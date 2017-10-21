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
    def __init__(self, stream, *, loop=None):
        self.stream = stream
        self.data = bytearray()
        self.ready = loop.create_future()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.ready.set_result(self.transport)

    def datagram_received(self, data, addr):
        print("RECEIVING")
        self.data.extend(data)

    def error_received(self, exc):
        print("Error received:", exc)


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
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        clock = self.clock()
        self._ready.set()
        while not self._stop.is_set():
            clock.forward(self.interval * 1_000_000)

            with self._lock:
                for transport, source in self.streams.items():
                    try:
                        payload = next(source)
                    except StopIteration:
                        print("STOP", id(source.future))

                        def callback():
                            print("IN CALLBACK...")
                            source.future.set_result(None)

                        assert self._loop == asyncio.get_event_loop()
                        self._loop.call_soon_threadsafe(callback)
                        print("DONE?", source.future.done())
                        continue

                    print("SENDING...")
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

        print("AAAND STOPPING")
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
        from .sdp import SDP
        return SDP(self.local_addr, self.ptime)

    async def negotiate(self, sdp):
        _sdp = str(sdp)
        m_header = re.search(r'm=audio (\d+) RTP/AVP', _sdp)
        c_header = re.search(r'c=IN IP4 ([\d.]+)', _sdp)
        self.remote_addr = c_header.group(1), int(m_header.group(1))
        self.transport = await self._create_endpoint()

    async def _create_endpoint(self):
        assert self.remote_addr
        transport, self.protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self, loop=self.loop),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )
        await self.protocol.ready
        return transport

    async def schedule(self, source, remote_addr):
        self.remote_addr = remote_addr
        self.future = source.future = self.loop.create_future()

        self.transport = await self._create_endpoint()
        self.scheduler.add(self.transport, source)
        return source

    def stop(self):
        self.scheduler.unregister(self.transport)

    def wait(self):
        assert self.future
        return self.future


# async def play(self, remote_addr, filename):
#     rtp_scheduler = aiortp.RTPScheduler()
#     rtp_stream = rtp_scheduler.create_new_stream(remote_addr)

#     source = AudioSource(filename)
#     await rtp_stream.schedule(source)
#     await rtp_stream.wait()


# async def dial(self, remote_addr, sequence):
#     rtp_scheduler = aiortp.RTPScheduler()
#     rtp_stream = rtp_scheduler.create_new_stream(remote_addr)

#     source = DTFMSource(filename)
#     await rtp_stream.schedule(source)
#     await rtp_stream.wait()


# async def play_tone(self, frequency, amplitude, duration):
#     rtp_scheduler = aiortp.RTPScheduler()
#     rtp_stream = rtp_scheduler.create_new_stream(remote_addr)

#     source = DTFMSource(frequency, amplitude, duration)
#     await rtp_stream.schedule(source)
#     await rtp_stream.wait()
