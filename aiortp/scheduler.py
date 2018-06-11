import asyncio
from collections import deque
import time
import logging
import typing
import re

import aiotimer

from .packet import RTP


LOG = logging.getLogger(__name__)


class PacketData(typing.NamedTuple):
    frametime: float
    packet: typing.Dict[str, typing.Any]


class RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, stream, *, loop):
        self.stream = stream
        self.packets = deque()
        self.ready = loop.create_future()
        self.transport = None
        self.packet_queue = asyncio.Queue()
        self._loop = loop

    def connection_made(self, transport):
        self.transport = transport
        self.ready.set_result(self.transport)

    def datagram_received(self, data, addr):
        packet = PacketData(frametime=time.time(),
                            packet=RTP.parse(data))
        self.packets.append(packet)
        try:
            self.packet_queue.put_nowait(packet)
        except Exception:
            LOG.exception('Failed to queue packet')

    def error_received(self, exc):
        print("Error received:", exc)


class RTPTimer(aiotimer.Protocol):
    def __init__(self, streams, *, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self.streams = streams

    def timer_ticked(self):
        for transport, source in self.streams.items():
            try:
                packet = next(source)
            except StopIteration:
                assert self._loop == asyncio.get_event_loop()
                source.future.set_result(None)
                continue

            transport.sendto(bytes(packet))

        self.streams = {k: v for k, v in self.streams.items()
                        if not v.stopped}

    def timer_overrun(self, overruns):
        raise RuntimeError("Timer overrun, everything is broken")


class RTPScheduler:
    def __init__(self, *, interval=20):
        self.interval = interval
        self.streams = {}
        self._timer = None
        self._protocol = None

    def create_new_stream(self, local_addr, *, ptime=20, loop=None):
        return RTPStream(self, local_addr, ptime=ptime, loop=loop)

    def add(self, transport, source):
        self.streams[transport] = source

        if not self._timer:
            self._timer, self._protocol = aiotimer.create_timer(
                lambda: RTPTimer(self.streams),
                interval=self.interval * 0.001
            )

    def unregister(self, transport):
        source = self.streams.pop(transport, None)
        if source:
            source.stop()

    def stop(self):
        old_streams = self.streams
        self.streams = {}

        for source in old_streams.values():
            source.stop()


class RTPStream:
    def __init__(self, scheduler, local_addr, *, ptime=20, loop=None):
        self.scheduler = scheduler
        self.local_addr = local_addr
        self.remote_addr = None
        self.stream = None
        self.ptime = ptime
        self._loop = loop or asyncio.get_event_loop()

    def describe(self):
        from .sdp import SDP
        return SDP(self.local_addr, self.ptime)

    async def negotiate(self, sdp):
        # TODO: add state-tracking
        _sdp = str(sdp)
        m_header = re.search(r'm=audio (\d+) RTP/AVP', _sdp)
        c_header = re.search(r'c=IN IP4 ([\d.]+)', _sdp)
        self.remote_addr = c_header.group(1), int(m_header.group(1))
        self.transport = await self._create_endpoint()

    async def _create_endpoint(self):
        assert self.remote_addr
        transport, self.protocol = await self._loop.create_datagram_endpoint(
            lambda: RTPProtocol(self, loop=self._loop),
            local_addr=self.local_addr,
            remote_addr=self.remote_addr
        )
        await self.protocol.ready
        return transport

    async def schedule(self, source):
        source.future = self._loop.create_future()

        self.transport = await self._create_endpoint()
        self.scheduler.add(self.transport, source)

        assert source.future
        await source.future

    def stop(self):
        self.scheduler.unregister(self.transport)

    async def packets(self):
        while True:
            yield await self.protocol.packet_queue.get()
