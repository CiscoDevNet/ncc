import sys
from ncclient import manager

complex_filter = """<interface-properties>
 <data-nodes>
  <data-node>
   <data-node-name>0/0/CPU0</data-node-name>
   <system-view>
    <interfaces>
     <interface>
      <interface-name>Loopback0</interface-name>
     </interface>
    </interfaces>
   </system-view>
  </data-node>
 </data-nodes>
</interface-properties>"""


def demo(host, user, passwd):
    with manager.connect(host=host, port=830, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        c = m.get(filter=('subtree',complex_filter)).data_xml
        print c

if __name__ == '__main__':
    demo(sys.argv[1], sys.argv[2], sys.argv[3])
