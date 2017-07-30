from hypothesis import given
from hypothesis.strategies import binary
from aiortp import *


@given(binary(min_size=rtphdr.size, max_size=rtphdr.size))
def test_decode_inverts_encode(pkt):
    assert pack_rtp(parse_rtp(pkt)) == pkt
