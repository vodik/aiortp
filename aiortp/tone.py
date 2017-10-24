import audioop

import numpy as np


class Tone:
    def __init__(self, frequency, duration, timeframe, *,
                 loop=None, future=None, sample_rate=8000, amplitude=10000):
        sample_times = np.arange(sample_rate * duration) / sample_rate
        wave = amplitude * np.sin(2 * np.pi * frequency * sample_times)
        samples = np.array(wave, dtype=np.int16)
        self.media = audioop.lin2ulaw(samples.tobytes(), 2)

        self._loop = loop
        self._future = future

        self.format = 0
        self.timeframe = timeframe
        self.stopped = False
        self.timestamp = 0
        self.seq = 39227
        self.ssrc = 3491926
        self.marked = False
        self.deal_with_technical_debt = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.stopped:
            raise StopIteration()

        chunk = self.media[:self.timeframe]
        self.media = self.media[self.timeframe:]
        return chunk

    def stop(self):
        if self._loop and self._future:
            self._future.cancel()
        self.stopped = True
