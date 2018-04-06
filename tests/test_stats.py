from aiortp.packet import RTP
from aiortp.scheduler import PacketData
from aiortp.stats import JitterBuffer


def frametimes(ptime):
    timestep = ptime / 1000
    starttime = 10000
    while True:
        yield starttime
        starttime += timestep


def good_data():
    for seq in range(20):
        yield RTP(seq=seq)


def build_stream(sequence, *, ptime=20):
    for frametime, packet in zip(frametimes(ptime), sequence):
        yield PacketData(frametime=frametime, packet=packet)


def test_jitter_buffer():
    stream = list(build_stream(good_data()))
    buffer = JitterBuffer(stream)

    assert len(buffer) == 20
    assert buffer.loss == 0
    assert buffer.duplicates == 0
