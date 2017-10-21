import aiortp
import aiortp.dtmf
import pytest


@pytest.fixture
def rtp_server(loop):
    return aiortp.RTPScheduler()


async def test_dtmf_describe(rtp_server, loop):
    rtp_stream_1 = rtp_server.create_new_stream(('127.0.0.1', 16384))
    rtp_stream_2 = rtp_server.create_new_stream(('127.0.0.1', 16386))

    source = aiortp.dtmf.DTMF('12345')
    await rtp_stream_1.schedule(source, remote_addr=('127.0.0.1', 16386))

    description = rtp_stream_1.describe()
    await rtp_stream_2.negotiate(description)
    rtp_stream_1.wait()

    import asyncio
    await asyncio.sleep(3)

    rtp_server._stop_thread()
    rtp_stream_1.transport.close()
    rtp_stream_2.transport.close()

    assert str(description) == '''v=0\r
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

    assert rtp_stream_2.protocol.data
