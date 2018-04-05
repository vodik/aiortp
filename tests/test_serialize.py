from hypothesis import given
from hypothesis.strategies import binary
from aiortp.packet import RTP, RTPEvent, rtphdr, rtpevent


@given(binary(min_size=rtphdr.size, max_size=rtphdr.size + 1000))
def test_rtp_decode_inverts_encode(pkt):
    rtp = RTP.parse(pkt)
    assert bytes(rtp) == pkt


@given(binary(min_size=rtpevent.size, max_size=rtpevent.size))
def test_rtpevent_decode_inverts_encode(pkt):
    rtpevent = RTPEvent.parse(pkt)
    assert bytes(rtpevent) == pkt


@given(binary(min_size=rtphdr.size + rtpevent.size,
              max_size=rtphdr.size + rtpevent.size))
def test_rtpevent_inside_rtp_decode_inverts_encode(pkt):
    rtp = RTP.parse(pkt)
    rtpevent = RTPEvent.parse(rtp.payload)

    assert pkt == bytes(RTP(
        version=rtp.version,
        padding=rtp.padding,
        ext=rtp.ext,
        csrc_items=rtp.csrc_items,
        marker=rtp.marker,
        p_type=rtp.p_type,
        seq=rtp.seq,
        timestamp=rtp.timestamp,
        ssrc=rtp.ssrc,
        payload=bytes(rtpevent)
    ))
