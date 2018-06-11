from .packet import RTPEvent

DTMF_MAP = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    '*': 10,
    '#': 11,
    'A': 12,
    'B': 13,
    'C': 14,
    'D': 15,
    '⚡': 16
}


async def dtmf_received(stream, dtmf):
    """Wait for a given dtmf event sequence on stream."""
    events = []
    async for packet in stream.packets():
        if packet.packet.marker == 0:
            continue
        events.append(RTPEvent.parse(packet.packet.payload))
        if len(events) == len(dtmf):
            break

    expect_ids = (DTMF_MAP[char] for char in dtmf)
    for event, expect_id in zip(events, expect_ids):
        if event.event_id != expect_id:
            raise RuntimeError('unexepected event: {}'.format(event))
