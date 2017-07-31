======
aiortp
======

Very, very pre-alpha software. Buyer beware!

RTP and basic SDP support for AsyncIO written in pure Python/Cython.

Seems to have good performance charactistics when playing static audio samples.

Lots of work needing to be done, has a horrible API, and need to explore if a
pure playback loop in pure C without the GIL will improve performance.

Built with a focus of SIP testing, but I do hope to build something
more general purpose out of the base.

-------
Example
-------

.. code-block:: python

    # Create the scheduler and attach a stream
    rtp_scheduler = aiortp.RTPScheduler()
    rtp = rtp_scheduler.create_new_stream((local_ip, 49709))

    # Get the SDP and send an invite off
    payload = rtp.describe()
    headers['Content-Type'] = 'application/sdp'
    response = send_invite(headers=headers, payload=payload)

    # Then feed in the SDP from the 200 OK
    rtp.negotiate(response.payload)

    # Start playback
    await rtp.start('some_audio_sample.flac')

    # Wait for the audio sample to finish playback
    await rtp.wait()

----
TODO
----

- Expose the received RTP stream
- DTMF
- Comfort noise
- More codecs
- Better SDP support
- Jitter buffer and RTP statistics (jitter, etc.)
- Support for other operating systems
