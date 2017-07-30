# cython: language_level=3, boundscheck=False
import asyncio
import audioop
import numpy as np
import os
import pysndfile
import re
import threading

from .clock import PosixClock
from .packet import pack_rtp


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


class RTPSource:
    def __init__(self, filename, timeframe, *, loop=None, future=None):
        audio = pysndfile.PySndfile(filename)
        frames = audio.read_frames(dtype=np.int16)
        self.media = audioop.lin2ulaw(frames.tobytes(), frames.itemsize)

        self.loop = loop
        self.future = future

        self.format = 0
        self.timeframe = timeframe
        self.stopped = False
        self.timestamp = 20
        self.seq = 49709
        self.ssrc = 167411976

    def __iter__(self):
        return self

    def __next__(self):
        if self.stopped:
            raise StopIteration()

        chunk = self.media[:self.timeframe]
        self.media = self.media[self.timeframe:]

        if not self.media:
            self.stopped = True
            if self.loop and self.future:
                print('SET THIS FUTURE')
                self.loop.call_soon_threadsafe(self.future.set_result, True)

        return chunk

    def stop(self):
        print("STOPPING")
        if self.loop and self.future:
            print('CANCLE THIS FUTURE')
            self.loop.call_soon_threadsafe(self.future.cancel)
        self.stopped = True


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

    def create_new_stream(self, source_facotry, local_addr, *, ptime=20,
                          loop=None):
        return RTPStream(self, local_addr, ptime=ptime, loop=loop)

    def add(self, transport, source):
        with self._lock:
            print("ADDING SOURCE!")
            self.streams[transport] = source

        if not self._thread:
            print("ATTEMPTING TO LAUNCH THREAD")
            self._thread = threading.Thread(target=self._run)
            self._thread.daemon = True
            self._stop = threading.Event()
            self._stopping = threading.Event()
            self._ready = threading.Event()
            self._thread.start()
            self._ready.wait()

    def _stop_thread(self):
        print("STOPPING THREAD...")
        self._stop.set()
        self._stopping.wait()
        print("STOPPED...")

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
        print("LOOP STARTED")
        while not self._stop.is_set():
            clock.forward(self.interval * 1_000_000)

            with self._lock:
                for transport, source in self.streams.items():
                    payload = next(source)
                    transport.sendto(pack_rtp({
                        'version': 2,
                        'padding': 0,
                        'ext': 0,
                        'csrc.items': 0,
                        'marker': 0,
                        'p_type': source.format,
                        'seq': source.seq,
                        'timestamp': source.timestamp,
                        'ssrc': source.ssrc,
                        'payload': payload
                    }))

                    source.seq += 1
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

    async def start(self, filename):
        assert self.remote_addr
        self.transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )

        await protocol.ready
        self.future = self.loop.create_future()
        source = RTPSource(filename, 8000 // 1000 * self.ptime,
                           loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    def stop(self):
        self.scheduler.unregister(self.transport)

    def wait(self):
        assert self.future
        return self.future
