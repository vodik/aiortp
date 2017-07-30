import os
from setuptools import setup, find_packages
from setuptools.extension import Extension
import sys


try:
    from Cython.Distutils import build_ext
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False


cmdclass = {}
long_description=open('README.md', encoding='utf-8').read()


if USE_CYTHON:
    ext_modules = [
        Extension("aiortp.clock.posix", ["aiortp/clock/posix.pyx"]),
        Extension("aiortp.packet", ["aiortp/packet.pyx"]),
        Extension("aiortp.scheduler", ["aiortp/scheduler.pyx"]),
    ]
    cmdclass['build_ext'] = build_ext
else:
    ext_modules = [
        Extension("aiortp.clock.posix", ["aiortp/clock/linux.c"]),
        Extension("aiortp.packet", ["aiortp/packet.c"]),
        Extension("aiortp.scheduler", ["aiortp/scheduler.c"]),
    ]


setup(
    name='aiortp',
    version='0.0.1',
    author='Simon Gomizelj',
    author_email='simon@vodik.xyz',
    packages=find_packages(),
    license="Apache 2",
    url='https://github.com/vodik/aiortp',
    description='RTP support for AsyncIO',
    long_description=long_description,
    cmdclass = cmdclass,
    ext_modules=ext_modules,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
