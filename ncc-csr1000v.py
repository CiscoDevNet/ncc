import sys
from ncclient import manager
import logging

def demo(host, user, passwd):
    try:
        m = manager.connect(host=host, port=2022, username=user, password=passwd, device_params={'name':"csr"})
        print 'm.connected = {}'.format(m.connected)
        c = m.get_config(source='running').data_xml
        print c
    except:
        print 'Exception generated!'
        pass
    print 'm.connected = {}'.format(m.connected)

if __name__ == '__main__':

    rootLogger = logging.getLogger('ncclient.transport.session')
    rootLogger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    rootLogger.addHandler(handler)

    demo(sys.argv[1], sys.argv[2], sys.argv[3])
