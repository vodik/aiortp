from hypothesis import given
from hypothesis.strategies import binary
from aiortp.packet import rtphdr, pack_rtp, parse_rtp
from aiortp.packet import rtpevent, pack_rtpevent, parse_rtpevent


@given(binary(min_size=rtphdr.size, max_size=rtphdr.size + 1000))
def test_rtp_decode_inverts_encode(pkt):
    rtp = parse_rtp(pkt)
    assert pack_rtp(rtp) == pkt


@given(binary(min_size=rtpevent.size, max_size=rtpevent.size))
def test_rtpevent_decode_inverts_encode(pkt):
    rtpevent = parse_rtpevent(pkt)
    assert pack_rtpevent(rtpevent) == pkt


@given(binary(min_size=rtphdr.size + rtpevent.size,
              max_size=rtphdr.size + rtpevent.size))
def test_rtpevent_inside_rtp_decode_inverts_encode(pkt):
    rtp = parse_rtp(pkt)
    rtpevent = parse_rtpevent(rtp.pop('payload'))

    rtp['payload'] = pack_rtpevent(rtpevent)
    assert pack_rtp(rtp) == pkt
