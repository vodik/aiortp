class SDP:
    def __init__(self, local_addr, ptime):
        self.local_addr = local_addr
        self.ptime = ptime

        local_addr_desc = f'IN IP4 {self.local_addr[0]}'
        self.payload = '\r\n'.join([
            'v=0',
            f'o=user1 53655765 2353687637 {local_addr_desc}',
            's=-',
            't=0 0',
            'i=aiortp media stream',
            f'm=audio {self.local_addr[1]} RTP/AVP 0 101 13',
            f'c={local_addr_desc}',
            'a=rtpmap:0 PCMU/8000/1',
            'a=rtpmap:101 telephone-event/8000',
            'a=fmtp:101 0-15',
            f'a=ptime:{self.ptime}',
            'a=sendrecv',
            '',
        ])

    def __str__(self):
        return self.payload
