import itertools

from aiortp.packet import RTP
from aiortp.scheduler import PacketData
from aiortp.stats import JitterBuffer


def frametimes(ptime):
    timestep = ptime / 1000
    starttime = 10000
    while True:
        yield starttime
        starttime += timestep


def build_buffer(sequence, *, ptime=20):
    def inner():
        for frametime, packet in zip(frametimes(ptime), sequence):
            yield PacketData(frametime=frametime, packet=packet)

    return JitterBuffer(list(inner()))


def test_jitter_buffer():
    data = [RTP(seq=seq) for seq in range(1, 21)]
    buffer = build_buffer(data)

    assert len(buffer) == 20
    assert buffer.loss == 0
    assert buffer.duplicates == 0


def test_jitter_buffer_detect_duplicates():
    data = [RTP(seq=42)] * 20
    buffer = build_buffer(data)

    assert len(buffer) == 1
    assert buffer.loss == 0
    assert buffer.duplicates == 19 / 20


def test_jitter_buffer_detect_loss():
    data = [RTP(seq=seq) for seq in range(1, 21, 2)]
    buffer = build_buffer(data)

    assert len(buffer) == 10
    assert buffer.loss == 9 / 10
    assert buffer.duplicates == 0


def test_jitter_buffer_detect_loss_and_duplicates():
    data = itertools.chain.from_iterable(
        [RTP(seq=seq)] * 2 for seq in range(1, 21, 2)
    )
    buffer = build_buffer(data)

    assert len(buffer) == 10
    assert buffer.loss == 9 / 20
    assert buffer.duplicates == 10 / 20
