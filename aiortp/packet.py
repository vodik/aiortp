# cython: linetrace=True
import struct
import typing


rtphdr = struct.Struct('!HHII')
rtpevent = struct.Struct('!BBH')


class RTP(typing.NamedTuple):
    version: int = 2
    padding: bool = 0
    ext: int = 0
    csrc_items: int = 0
    marker: bool = 0
    p_type: int = 0
    seq: int = 0
    timestamp: int = 0
    ssrc: int = 0
    payload: bytes = b''

    @classmethod
    def parse(cls, data):
        rtp = rtphdr.unpack(data[:rtphdr.size])
        return cls(
            version=(rtp[0] >> 14) & 0x3,
            padding=(rtp[0] >> 13) & 0x1,
            ext=(rtp[0] >> 12) & 0x1,
            csrc_items=(rtp[0] >> 8) & 0xF,
            marker=(rtp[0] >> 7) & 0x1,
            p_type=rtp[0] & 0x7f,
            seq=rtp[1],
            timestamp=rtp[2],
            ssrc=rtp[3],
            payload=data[rtphdr.size:]
        )

    def __bytes__(self):
        header = rtphdr.pack(
            (self.version & 0x3) << 14
            | (self.padding & 0x1) << 13
            | (self.ext & 0x1) << 12
            | (self.csrc_items & 0xF) << 8
            | (self.marker & 0x1) << 7
            | (self.p_type & 0x7f),
            self.seq,
            self.timestamp,
            self.ssrc
        )
        return b''.join([header, bytes(self.payload)])


class RTPEvent(typing.NamedTuple):
    event_id: int
    end_of_event: bool
    reserved: bool
    volume: int
    duration: int

    @classmethod
    def parse(cls, data):
        event = rtpevent.unpack(data[:rtpevent.size])
        return cls(
            event_id=event[0],
            end_of_event=(event[1] >> 7) & 0x01,
            reserved=(event[1] >> 6) & 0x01,
            volume=event[1] & 0x3f,
            duration=event[2]
        )

    def __bytes__(self):
        return rtpevent.pack(
            self.event_id,
            (self.end_of_event & 0x01) << 7
            | (self.reserved & 0x01) << 6
            | (self.volume & 0x3f),
            self.duration
        )
