import os
from setuptools import setup, find_packages
from setuptools.command.sdist import sdist as _sdist
from setuptools.extension import Extension
import sys


macros = [('CYTHON_TRACE', '1')]


try:
    from Cython.Distutils import build_ext
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False


class sdist(_sdist):
    def run(self):
        # Make sure the compiled Cython files in the distribution are up-to-date
        from Cython.Build import cythonize
        cythonize(["aiortp/packet.pyx"])
        _sdist.run(self)


cmdclass = {}
long_description=open('README.rst', encoding='utf-8').read()


if USE_CYTHON:
    ext_modules = [
        Extension("aiortp.packet", ["aiortp/packet.pyx"],
                  define_macros=macros),
    ]
    cmdclass['build_ext'] = build_ext
    cmdclass['sdist'] = sdist
else:
    ext_modules = [
        Extension("aiortp.packet", ["aiortp/packet.c"],
                  define_macros=macros),
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
    install_requires=[
        'aiotimer==0.1.0',
        'numpy',
        'pysndfile',
    ],
    cmdclass = cmdclass,
    ext_modules=ext_modules,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
