from hypothesis import given
from hypothesis.strategies import binary
from aiortp.packet import rtphdr, pack_rtp, parse_rtp


@given(binary(min_size=rtphdr.size, max_size=rtphdr.size + 1_000))
def test_rtp_decode_inverts_encode(pkt):
    assert pack_rtp(parse_rtp(pkt)) == pkt
