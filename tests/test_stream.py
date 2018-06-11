import aiortp
import pytest


@pytest.fixture
def rtp_server(loop):
    return aiortp.RTPScheduler()


async def test_dtmf_describe(rtp_server, loop):
    dtmf = '12345'
    source = aiortp.DTMF(dtmf)

    rtp_stream_1 = rtp_server.create_new_stream(('127.0.0.1', 16384))
    rtp_stream_2 = rtp_server.create_new_stream(('127.0.0.1', 16386))

    description1 = rtp_stream_1.describe()
    description2 = rtp_stream_2.describe()
    await rtp_stream_1.negotiate(description2)
    await rtp_stream_2.negotiate(description1)

    await rtp_stream_1.schedule(source)
    await aiortp.dtmf.dtmf_received(rtp_stream_2, dtmf)

    rtp_server._timer.close()
    rtp_stream_1.transport.close()
    rtp_stream_2.transport.close()

    assert str(description1) == '''v=0\r
o=user1 53655765 2353687637 IN IP4 127.0.0.1\r
s=-\r
t=0 0\r
i=aiortp media stream\r
m=audio 16384 RTP/AVP 0 101 13\r
c=IN IP4 127.0.0.1\r
a=rtpmap:0 PCMU/8000/1\r
a=rtpmap:101 telephone-event/8000\r
a=fmtp:101 0-15\r
a=ptime:20\r
a=sendrecv\r
'''
    assert str(description2) == '''v=0\r
o=user1 53655765 2353687637 IN IP4 127.0.0.1\r
s=-\r
t=0 0\r
i=aiortp media stream\r
m=audio 16386 RTP/AVP 0 101 13\r
c=IN IP4 127.0.0.1\r
a=rtpmap:0 PCMU/8000/1\r
a=rtpmap:101 telephone-event/8000\r
a=fmtp:101 0-15\r
a=ptime:20\r
a=sendrecv\r
'''
