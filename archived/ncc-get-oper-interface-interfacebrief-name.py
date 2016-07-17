import sys
from ncclient import manager
from jinja2 import Template


complex_filter = Template("""<interfaces>
  <interface-briefs>
    <interface-brief>
      <interface-name>{{IFNAME}}</interface-name>
    </interface-brief>
</interfaces>""")


def demo(host, user, passwd, ifname):
    with manager.connect(host=host, port=830, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        c = m.get(filter=('subtree',complex_filter.render(IFNAME=ifname))).data_xml
        print c

if __name__ == '__main__':
    demo(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
