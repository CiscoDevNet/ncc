import sys
from ncclient import manager
import re

def demo(host, port, user, passwd):
    with manager.connect(host=host, port=port, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        for cap in sorted(m.server_capabilities):
            m = re.search('module=([^&]*)&', cap)
            if m is not None:
                print m.group(1)

if __name__ == '__main__':
    demo(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
