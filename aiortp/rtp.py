from collections import namedtuple


RTPPacket = namedtuple('RTPPacket', 'marked,format,seq,timestamp,ssrc,payload')


class RTPSource:
    pass


class RTPSink:
    pass
