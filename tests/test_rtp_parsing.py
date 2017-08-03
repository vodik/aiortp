from hypothesis import given
from hypothesis.strategies import binary
from aiortp.packet import rtphdr, pack_rtp, parse_rtp
from aiortp.packet import rtpevent, pack_rtpevent, parse_rtpevent


@given(binary(min_size=rtphdr.size, max_size=rtphdr.size + 1_000))
def test_rtp_decode_inverts_encode(pkt):
    assert pack_rtp(parse_rtp(pkt)) == pkt


@given(binary(min_size=rtpevent.size, max_size=rtpevent.size))
def test_rtpevent_decode_inverts_encode(pkt):
    assert pack_rtpevent(parse_rtpevent(pkt)) == pkt
