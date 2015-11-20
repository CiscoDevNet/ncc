import sys
from ncclient import manager

def demo(host, user, passwd):
    with manager.connect(host=host, port=830, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        for cap in sorted(m.server_capabilities):
            print cap

if __name__ == '__main__':
    demo(sys.argv[1], sys.argv[2], sys.argv[3])
