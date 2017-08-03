import struct


rtphdr = struct.Struct('!HHII')
rtpevent = struct.Struct('!BBH')


def parse_rtp(data):
    rtp = rtphdr.unpack(data[:rtphdr.size])
    return {'version': (rtp[0] >> 14) & 0x3,
            'padding': (rtp[0] >> 13) & 0x1,
            'ext': (rtp[0] >> 12) & 0x1,
            'csrc.items': (rtp[0] >> 8) & 0xF,
            'marker': (rtp[0] >> 7) & 0x1,
            'p_type': rtp[0] & 0x7f,
            'seq': rtp[1],
            'timestamp': rtp[2],
            'ssrc': rtp[3],
            'payload': data[rtphdr.size:]}


def parse_rtpevent(data):
    event = rtpevent.unpack(data[:rtpevent.size])
    return {'event_id': (event[0] >> 1),
            'end_of_event': event[0] & 0x1,
            'reserved': (event[1] >> 7),
            'volume': event[1] & 0x7f,
            'duration': event[2]}


def pack_rtp(data):
    header = rtphdr.pack((data['version'] & 0x3) << 14
                          | (data['padding'] & 0x1) << 13
                          | (data['ext'] & 0x1) << 12
                          | (data['csrc.items'] & 0xF) << 8
                          | (data['marker'] & 0x1) << 7
                          | (data['p_type'] & 0x7f),
                          data['seq'],
                          data['timestamp'],
                          data['ssrc'])
    return b''.join([header, data['payload']])


def pack_rtpevent(data):
    return rtpevent.pack(data['event_id'] << 1
                         | data['end_of_event'] & 0x1,
                         (data['reserved'] & 0x1) << 7
                         | data['volume'],
                         data['duration'])
