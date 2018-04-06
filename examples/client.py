import argparse
import asyncio
import contextlib
import logging
import random

import aiortp
import aiosip

sip_config = {
    'srv_host': '127.0.0.1',
    'srv_port': 6000,
    'realm': 'XXXXXX',
    'user': 'aiosip',
    'pwd': 'hunter2',
    'local_host': '127.0.0.1',
    'local_port': random.randint(6001, 6100)
}


async def run_call(peer, audio):
    scheduler = aiortp.RTPScheduler()
    stream = scheduler.create_new_stream((sip_config['srv_host'], 49709))

    call = await peer.invite(
        from_details=aiosip.Contact.from_header('sip:{}@{}:{}'.format(
            sip_config['user'], sip_config['local_host'],
            sip_config['local_port'])),
        to_details=aiosip.Contact.from_header('sip:666@{}:{}'.format(
            sip_config['srv_host'], sip_config['srv_port'])),
        password=sip_config['pwd'],
        headers={'Content-Type': 'application/sdp'},
        payload=str(stream.describe()))

    async with call:
        async for msg in call.wait_for_terminate():
            print("CALL STATUS:", msg.status_code)

        await stream.negotiate(msg.payload)
        await stream.schedule(audio)

    print("CALL TERMINATED")


async def start(app, protocol, audiofile):
    if protocol is aiosip.WS:
        peer = await app.connect(
            'ws://{}:{}'.format(sip_config['srv_host'], sip_config['srv_port']),
            protocol=protocol,
            local_addr=(sip_config['local_host'], sip_config['local_port']))
    else:
        peer = await app.connect(
            (sip_config['srv_host'], sip_config['srv_port']),
            protocol=protocol,
            local_addr=(sip_config['local_host'], sip_config['local_port']))

    audio = aiortp.AudioFile(audiofile, 8000 // 1000 * 20)
    await run_call(peer, audio)
    await app.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--protocol', default='udp')
    parser.add_argument('filename', default='udp')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    app = aiosip.Application(loop=loop)

    if args.protocol == 'udp':
        loop.run_until_complete(start(app, aiosip.UDP, args.filename))
    elif args.protocol == 'tcp':
        loop.run_until_complete(start(app, aiosip.TCP, args.filename))
    elif args.protocol == 'ws':
        loop.run_until_complete(start(app, aiosip.WS, args.filename))
    else:
        raise RuntimeError("Unsupported protocol: {}".format(args.protocol))

    loop.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
