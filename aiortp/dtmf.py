from .packet import pack_rtp, pack_rtpevent


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


class DTMF:
    def __init__(self, sequence, *, tone_length=None, loop=None, future=None):
        self.sequence = [DTMF_MAP[x] for x in sequence]
        self.tone_length = tone_length or 200

        self.seq_iter = iter(self.sequence)
        self.current = next(self.seq_iter)
        self.cur_length = 0

        self.loop = loop
        self.future = future

        self.format = 101
        self.timeframe = 20
        self.stopped = False
        self.timestamp = 20
        self.seq = 49710
        self.ssrc = 167411978
        self.marked = True
        self.deal_with_technical_debt = True

    def __iter__(self):
        return self

    def __next__(self):
        if self.stopped:
            raise StopIteration()

        if self.marked and self.cur_length:
            self.marked = False

        # If we're off the end of the previous dtmf packet, get a new one
        if self.cur_length > self.tone_length:
            self.timestamp += 20  # self.tone_length - 60
            self.cur_length = 0
            try:
                self.current = next(self.seq_iter)
                self.marked = True
            except StopIteration:
                self.stopped = True
                if self.loop and self.future:
                    self.loop.call_soon_threadsafe(self.future.set_result, True)
                raise

        # Last three rtpevent messages should be marked as the end of event
        end = bool(self.cur_length + 60 >= self.tone_length)
        event = pack_rtpevent({'event_id': self.current,
                               'end_of_event': end,
                               'reserved': 0,
                               'volume': 10,
                               'duration': self.cur_length * 8})
        self.cur_length += 20
        return event

    def stop(self):
        if self.loop and self.future:
            self.loop.call_soon_threadsafe(self.future.cancel)
        self.stopped = True
