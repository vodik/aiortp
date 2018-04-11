from setuptools import setup, find_packages


long_description=open('README.rst', encoding='utf-8').read()


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
        'sndfile',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
