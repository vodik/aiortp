# cython: language_level=3, boundscheck=False
import asyncio
import audioop
import numpy as np
import os
import pysndfile
import re
import threading

from .clock import PosixClock
from .packet import pack_rtp, pack_rtpevent


DTMF_MAP = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    '*': 10,
    '#': 11,
    'A': 12,
    'B': 13,
    'C': 14,
    'D': 15,
    '⚡': 16
}


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


class DTMF:
    def __init__(self, sequence, *, tone_length=None, loop=None, future=None):
        self.sequence = [DTMF_MAP[x] for x in sequence]
        self.tone_length = tone_length or 200

        self.seq_iter = iter(self.sequence)
        self.current = next(self.seq_iter)
        self.cur_length = 0

        self.loop = loop
        self.future = future

        self.format = 101
        self.timeframe = 20
        self.stopped = False
        self.timestamp = 20
        self.seq = 49710
        self.ssrc = 167411978
        self.marked = True
        self.deal_with_technical_debt = True

    def __iter__(self):
        return self

    def __next__(self):
        if self.stopped:
            raise StopIteration()

        if self.marked and self.cur_length:
            self.marked = False

        # If we're off the end of the previous dtmf packet, get a new one
        if self.cur_length > self.tone_length:
            self.timestamp += 20  # self.tone_length - 60
            self.cur_length = 0
            try:
                self.current = next(self.seq_iter)
                self.marked = True
            except StopIteration:
                self.stopped = True
                if self.loop and self.future:
                    self.loop.call_soon_threadsafe(self.future.set_result, True)
                raise

        # Last three rtpevent messages should be marked as the end of event
        end = bool(self.cur_length + 60 >= self.tone_length)
        event = pack_rtpevent({'event_id': self.current,
                               'end_of_event': end,
                               'reserved': 0,
                               'volume': 10,
                               'duration': self.cur_length * 8})
        self.cur_length += 20
        return event

    def stop(self):
        if self.loop and self.future:
            self.loop.call_soon_threadsafe(self.future.cancel)
        self.stopped = True


class AudioFile:
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
        self.marked = False
        self.deal_with_technical_debt = False

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
                self.loop.call_soon_threadsafe(self.future.set_result, True)

        return chunk

    def stop(self):
        if self.loop and self.future:
            self.loop.call_soon_threadsafe(self.future.cancel)
        self.stopped = True


class Tone:
    def __init__(self, frequency, duration, timeframe, *,
                 loop=None, future=None, sample_rate=8000, amplitude=10_000):
        sample_times = np.arange(sample_rate * duration) / sample_rate
        wave = amplitude * np.sin(2 * np.pi * frequency * sample_times)
        samples = np.array(wave, dtype=np.int16)
        self.media = audioop.lin2ulaw(samples.tobytes(), 2)

        self.loop = loop
        self.future = future

        self.format = 0
        self.timeframe = timeframe
        self.stopped = False
        self.timestamp = 0
        self.seq = 39227
        self.ssrc = 3491926
        self.marked = False
        self.deal_with_technical_debt = False

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
                self.loop.call_soon_threadsafe(self.future.set_result, True)

        return chunk

    def stop(self):
        if self.loop and self.future:
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

    async def play_tone(self, frequency=650, duration=1.0, amplitude=5000):
        assert self.remote_addr
        self.transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )

        await protocol.ready
        self.future = self.loop.create_future()
        source = Tone(frequency, duration, 8000 // 1000 * self.ptime,
                      amplitude=amplitude, loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    async def start(self, filename):
        assert self.remote_addr
        self.transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )

        await protocol.ready
        self.future = self.loop.create_future()
        source = AudioFile(filename, 8000 // 1000 * self.ptime,
                           loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    async def dial(self, sequence):
        assert self.remote_addr
        self.transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: RTP(self),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )

        await protocol.ready
        self.future = self.loop.create_future()
        source = DTMF(sequence, loop=self.loop, future=self.future)
        self.scheduler.add(self.transport, source)
        return source

    def stop(self):
        self.scheduler.unregister(self.transport)

    def wait(self):
        assert self.future
        return self.future
