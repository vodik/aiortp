class SDP:
    def __init__(self, local_addr, ptime):
        self.local_addr = local_addr
        self.ptime = ptime

        local_addr_desc = 'IN IP4 {}'.format(self.local_addr[0])
        self.payload = '\r\n'.join([
            'v=0',
            'o=- 6666 2 IN IP4 {local_addr_desc}',
            's=SIP Call',
            'c=IN IP4 {local_addr_desc}',
            't=0 0',
            'm=audio 12100 {local_port} 0 101',
            'a=sendrecv',
            'a=rtpmap:0 PCMU/8000',
            'a=ptime:{ptime}',
            'a=rtpmap:101 telephone-event/8000',
            'a=fmtp:101 0-11,16',
            '',
        ]).format(local_addr_desc=local_addr_desc,
                  local_port=self.local_addr[1],
                  ptime=self.ptime)

    def __str__(self):
        return self.payload
