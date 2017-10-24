class SDP:
    def __init__(self, local_addr, ptime):
        self.local_addr = local_addr
        self.ptime = ptime

        local_addr_desc = 'IN IP4 {}'.format(self.local_addr[0])
        self.payload = '\r\n'.join([
            'v=0',
            'o=user1 53655765 2353687637 {local_addr_desc}',
            's=-',
            't=0 0',
            'i=aiortp media stream',
            'm=audio {local_port} RTP/AVP 0 101 13',
            'c={local_addr_desc}',
            'a=rtpmap:0 PCMU/8000/1',
            'a=rtpmap:101 telephone-event/8000',
            'a=fmtp:101 0-15',
            'a=ptime:{ptime}',
            'a=sendrecv',
            '',
        ]).format(local_addr_desc=local_addr_desc,
                  local_port=self.local_addr[1],
                  ptime=self.ptime)

    def __str__(self):
        return self.payload
