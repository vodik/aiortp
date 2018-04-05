# cython: linetrace=True
import struct
import typing


rtphdr = struct.Struct('!HHII')
rtpevent = struct.Struct('!BBH')


class RTP(typing.NamedTuple):
    version: int
    padding: bool
    ext: int
    csrc_items: int
    marker: bool
    p_type: int
    seq: int
    timestamp: int
    ssrc: int
    payload: bytes

    def __bytes__(self):
        return pack_rtp(self)


class RTPEvent(typing.NamedTuple):
    event_id: int
    end_of_event: bool
    reserved: bool
    volume: int
    duration: int

    def __bytes__(self):
        return pack_rtp(self)


def parse_rtp(data):
    rtp = rtphdr.unpack(data[:rtphdr.size])
    return RTP(
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


def pack_rtp(data):
    header = rtphdr.pack((data.version & 0x3) << 14
                         | (data.padding & 0x1) << 13
                         | (data.ext & 0x1) << 12
                         | (data.csrc_items & 0xF) << 8
                         | (data.marker & 0x1) << 7
                         | (data.p_type & 0x7f),
                         data.seq,
                         data.timestamp,
                         data.ssrc)
    return b''.join([header, data.payload])


def parse_rtpevent(data):
    event = rtpevent.unpack(data[:rtpevent.size])
    return RTPEvent(
        event_id=event[0],
        end_of_event=(event[1] >> 7) & 0x01,
        reserved=(event[1] >> 6) & 0x01,
        volume=event[1] & 0x3f,
        duration=event[2]
    )


def pack_rtpevent(data):
    return rtpevent.pack(data.event_id,
                         (data.end_of_event & 0x01) << 7
                         | (data.reserved & 0x01) << 6
                         | (data.volume & 0x3f),
                         data.duration)
