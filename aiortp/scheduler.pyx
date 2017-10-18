# cython: language_level=3, boundscheck=False, linetrace=True
import asyncio
import audioop
import numpy as np
import os
import pysndfile
import re
import threading

from .audio import AudioFile
from .clock import PosixClock
from .dtmf import DTMF
from .packet import pack_rtp, pack_rtpevent
from .tone import Tone


class RTP(asyncio.DatagramProtocol):
    def __init__(self, stream):
        self.stream = stream
        self.data = bytearray()
        self.ready = asyncio.Future()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.ready.set_result(self.transport)

    def datagram_received(self, data, addr):
        self.data.extend(data)


class RTPTask:
    def __init__(self, transport, source, ptime):
        self.transport = transport
        self.ptime = ptime
        self.source = source


class RTPScheduler:
    def __init__(self, *, interval=20):
        self.clock = PosixClock
        self.interval = interval
        self.streams = {}

        self._thread = None
        self._ready = None
        self._stop = None
        self._stopping = None
        self._lock = threading.Lock()

    def create_new_stream(self, local_addr, *, ptime=20, loop=None):
        return RTPStream(self, local_addr, ptime=ptime, loop=loop)

    def add(self, transport, source):
        with self._lock:
            self.streams[transport] = source

        if not self._thread:
            self._thread = threading.Thread(target=self._run)
            self._thread.daemon = True
            self._stop = threading.Event()
            self._stopping = threading.Event()
            self._ready = threading.Event()
            self._thread.start()
            self._ready.wait()

    def _stop_thread(self):
        self._stop.set()
        self._stopping.wait()

        # cleanup thread
        self._thread = None
        self._ready = None
        self._stop = None
        self._stopping = None

    def unregister(self, transport):
        with self._lock:
            source = self.streams.pop(transport, None)

        if source:
            source.stop()

        if not self.streams and self._thread:
            self._stop_thread()

    def stop(self):
        with self._lock:
            old_streams = self.streams
            self.streams = {}

        for source in old_streams.values():
            source.stop()

        if self._thread:
            self._stop_thread()

    def _run(self):
        clock = self.clock()
        self._ready.set()
        while not self._stop.is_set():
            clock.forward(self.interval * 1_000_000)

            with self._lock:
                for transport, source in self.streams.items():
                    try:
                        payload = next(source)
                    except StopIteration:
                        continue

                    transport.sendto(pack_rtp({
                        'version': 2,
                        'padding': 0,
                        'ext': 0,
                        'csrc.items': 0,
                        'marker': source.marked,
                        'p_type': source.format,
                        'seq': source.seq,
                        'timestamp': source.timestamp,
                        'ssrc': source.ssrc,
                        'payload': payload
                    }))

                    source.seq += 1
                    if not source.deal_with_technical_debt:
                        source.timestamp += source.timeframe

                self.streams = {k: v for k, v in self.streams.items()
                                if not v.stopped}
                if not self.streams:
                    break

            clock.sleep()

        self._stopping.set()


class RTPStream:
    def __init__(self, scheduler, local_addr, *, ptime=20, loop=None):
        self.scheduler = scheduler
        self.local_addr = local_addr
        self.remote_addr = None
        self.stream = None
        self.ptime = ptime
        self.future = None
        self.loop = loop or asyncio.get_event_loop()

    def describe(self):
        local_addr_desc = f'IN IP4 {self.local_addr[0]}'
        return '\r\n'.join([
            'v=0',
            f'o=user1 53655765 2353687637 {local_addr_desc}',
            's=-',
            't=0 0',
            'i=aiortp media stream',
            f'm=audio {self.local_addr[1]} RTP/AVP 0 101 13',
            f'c={local_addr_desc}',
            'a=rtpmap:0 PCMU/8000/1',
            'a=rtpmap:101 telephone-event/8000',
            'a=fmtp:101 0-15',
            f'a=ptime:{self.ptime}',
            'a=sendrecv',
            '',
        ])

    def negotiate(self, sdp):
        m_header = re.search(r'm=audio (\d+) RTP/AVP', sdp)
        c_header = re.search(r'c=IN IP4 ([\d.]+)', sdp)
        self.remote_addr = c_header.group(1), int(m_header.group(1))

    async def _create_endpoint(self):
        assert self.remote_addr
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )
        await protocol.ready
        return transport

    async def play_tone(self, frequency=650, duration=1.0, amplitude=5000):
        self.transport = await self._create_endpoint()
        self.future = self.loop.create_future()
        source = Tone(frequency, duration, 8000 // 1000 * self.ptime,
                      amplitude=amplitude, loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    async def start(self, filename):
        self.transport = await self._create_endpoint()
        self.future = self.loop.create_future()
        source = AudioFile(filename, 8000 // 1000 * self.ptime,
                           loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    async def dial(self, sequence):
        self.transport = await self._create_endpoint()
        self.future = self.loop.create_future()
        source = DTMF(sequence, loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    def stop(self):
        self.scheduler.unregister(self.transport)

    def wait(self):
        assert self.future
        return self.future
