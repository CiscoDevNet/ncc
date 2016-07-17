import sys
from ncclient import manager
import logging
from BeautifulSoup import BeautifulStoneSoup

def demo(host, user, passwd):
    with manager.connect(host=host, port=830, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        c = m.validate('candidate')
        print c

if __name__ == '__main__':
    # rootLogger = logging.getLogger('ncclient.transport.session')
    # rootLogger.setLevel(logging.DEBUG)
    # handler = logging.StreamHandler()
    # rootLogger.addHandler(handler)
    demo(sys.argv[1], sys.argv[2], sys.argv[3])
