# cython: linetrace=True
from posix.time cimport TIMER_ABSTIME, CLOCK_MONOTONIC
from posix.time cimport clock_gettime, clock_nanosleep, timespec


cdef class PosixClock:
    cdef timespec deadline

    def __cinit__(self):
        self.deadline = timespec(tv_sec=0, tv_nsec=0)
        clock_gettime(CLOCK_MONOTONIC, &self.deadline)

    cpdef forward(self, offset):
        self.deadline.tv_nsec += offset
        if self.deadline.tv_nsec >= 1_000_000_000:
            self.deadline.tv_nsec -= 1_000_000_000
            self.deadline.tv_sec += 1

    cpdef sleep(self):
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &self.deadline, NULL)
