import audioop

import numpy as np
import pysndfile


class AudioFile:
    def __init__(self, filename, timeframe, *, loop=None, future=None):
        audio = pysndfile.PySndfile(filename)
        frames = audio.read_frames(dtype=np.int16)
        self.media = audioop.lin2ulaw(frames.tobytes(), frames.itemsize)

        self._loop = loop
        self._future = future

        self.format = 0
        self.timeframe = timeframe

        self.stopped = False
        self.timestamp = 20
        self.seq = 49709
        self.ssrc = 167411976
        self.marked = False
        self.deal_with_technical_debt = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.stopped:
            raise StopIteration()

        chunk = self.media[:self.timeframe]
        self.media = self.media[self.timeframe:]

        result = (self.marked, self.format, self.seq, self.timestamp,
                  self.ssrc, chunk)
        self.timestamp += self.timeframe
        return result

    def stop(self):
        if self._loop and self._future:
            self._future.cancel()
        self.stopped = True
