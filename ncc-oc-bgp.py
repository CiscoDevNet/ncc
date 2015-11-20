#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Template
from lxml import etree
import logging

basic_bgp = Template("""<config>
 <bgp xmlns="http://openconfig.net/yang/bgp">
  <global>
   <config>
    <as>123</as>
   </config>
  </global>
 </bgp>
</config>""")


add_neighbor = Template("""<config>
 <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor nc:operation='create'>
     <neighbor-address>{{NEIGHBOR_ADDR}}</neighbor-address>
     <config>
      <neighbor-address>{{NEIGHBOR_ADDR}}</neighbor-address>
      <peer-as>{{REMOTE_AS}}</peer-as>
      <description>{{DESCRIPTION}}</description>
     </config>
    </neighbor>
   </neighbors>
  </bgp>
</config>""")


del_neighbor = Template("""<config>
 <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor nc:operation='delete'>
     <neighbor-address>{{NEIGHBOR_ADDR}}</neighbor-address>
    </neighbor>
   </neighbors>
  </bgp>
</config>""")


add_static_route_default = Template("""<config>
  <router-static xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-static-cfg">
   <default-vrf>
    <address-family>
     <vrfipv4>
      <vrf-unicast>
       <vrf-prefixes>
        <vrf-prefix>
         <prefix>10.1.1.0</prefix>
         <prefix-length>24</prefix-length>
         <vrf-route>
          <vrf-next-hop-table>
           <vrf-next-hop-interface-name-next-hop-address>
            <interface-name>Loopback0</interface-name>
            <next-hop-address>10.10.10.1</next-hop-address>
           </vrf-next-hop-interface-name-next-hop-address>
          </vrf-next-hop-table>
         </vrf-route>
        </vrf-prefix>
        <vrf-prefix>
         <prefix>10.1.2.0</prefix>
         <prefix-length>24</prefix-length>
         <vrf-route>
          <vrf-next-hop-table>
           <vrf-next-hop-interface-name>
            <interface-name>Loopback0</interface-name>
           </vrf-next-hop-interface-name>
          </vrf-next-hop-table>
         </vrf-route>
        </vrf-prefix>
       </vrf-prefixes>
      </vrf-unicast>
     </vrfipv4>
    </address-family>
   </default-vrf>
  </router-static>
</config>""")

foo1_add_static_route_default = Template("""<config>
  <router-static xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-static-cfg">
   <default-vrf>
    <address-family>
     <vrfipv4>
      <vrf-unicast>
       <vrf-prefixes>
        <vrf-prefix>
         <prefix>10.1.3.0</prefix>
         <prefix-length>24</prefix-length>
         <vrf-route>
          <vrf-next-hop-table>
           <vrf-next-hop>
            <interface-name>Loopback0</interface-name>
            <next-hop-address>192.168.1.1</next-hop/address>
            <explict-path-name>foo</explicit-path-name>
           </vrf-next-hop>
          </vrf-next-hop-table>
         </vrf-route>
        </vrf-prefix>
       </vrf-prefixes>
      </vrf-unicast>
     </vrfipv4>
    </address-family>
   </default-vrf>
  </router-static>
</config>""")

foo2_add_static_route_default = Template("""<config>
  <router-static xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-static-cfg">
   <default-vrf>
    <address-family>
     <vrfipv4>
      <vrf-unicast>
       <vrf-prefixes>
        <vrf-prefix>
         <prefix>10.1.4.0</prefix>
         <prefix-length>24</prefix-length>
         <vrf-route>
          <vrf-next-hop-table>
           <vrf-next-hop>
            <interface-name>Loopback0</interface-name>
           </vrf-next-hop>
          </vrf-next-hop-table>
         </vrf-route>
        </vrf-prefix>
       </vrf-prefixes>
      </vrf-unicast>
     </vrfipv4>
    </address-family>
   </default-vrf>
  </router-static>
</config>""")



def add_static_route_default_vrf(m, prefix, prefix_length, next_hop_intf, next_hop_addr, next_hop_path_name):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a neighbor!"
    data = add_static_route_default.render()
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()
    

def oc_basic(m):
    """Simple example to establish basic BGP config with a fixed AS.

    """
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a neighbor!"
    data = basic_bgp.render()
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()


def oc_add_neighbor(m, neighbor_addr, neighbor_remote_as, neighbor_description):
    """Simple example to add a BGP neighbor using the OC model.

    """
    if m is None or neighbor_addr is None or neighbor_remote_as is None or neighbor_description is None:
        print >>sys.stderr, "Not enough parameters to add a neighbor!"
    data = add_neighbor.render(NEIGHBOR_ADDR=neighbor_addr,
                               REMOTE_AS=neighbor_remote_as,
                               DESCRIPTION=neighbor_description)
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()


def oc_del_neighbor(m, neighbor_addr):
    """Simple example to delete a BGP neighbor using the OC model.

    """
    data = del_neighbor.render(NEIGHBOR_ADDR=neighbor_addr)
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()


def get_running_config(m, filter=None):
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter)).data_xml
    else:
        c = m.get_config(source='running').data_xml
    print etree.tostring(etree.fromstring(c), pretty_print=True)
        
        
if __name__ == '__main__':

    parser = ArgumentParser(description='Select your simple OC-BGP operation:')

    # Input parameters
    parser.add_argument('--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")
    parser.add_argument('-n', '--neighbor-addr', type=str, 
                        help="Specify a neighbor address, no validation")
    parser.add_argument('-r', '--remote-as', type=str, 
                        help="Specify the neighbor's remote AS, no validation")
    parser.add_argument('--description', type=str, 
                        help="Specify the neighbor's description, just a string (quote it!)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do I really need to explain?")

    # Only one type of filter
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="XML-formatted netconf subtree filter")
    g.add_argument('-o', '--oc-bgp-filter', action='store_true',
                   help="XML-formatted netconf subtree filter")

    # Basic operations
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('-b', '--basic', action='store_true',
                   help="Establish basic BGP config")
    g.add_argument('-a', '--add-neighbor', action='store_true',
                   help="Add a BGP neighbor")
    g.add_argument('-d', '--del-neighbor', action='store_true',
                   help="Delete a BGP neighbor by address")
    g.add_argument('--add-del-neighbor', action='store_true',
                   help="And *and* delete a BGP neighbor by address")
    g.add_argument('--add-static-route', action='store_true',
                   help="Get routes oper data")
    
    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        for l in ['ncclient.transport.ssh', 'ncclient.transport.session', 'ncclient.operations.rpc']:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        # rootLogger = logging.getLogger('ncclient.transport.ssh')
        # rootLogger.setLevel(logging.DEBUG)
        # handler = logging.StreamHandler()
        # rootLogger.addHandler(handler)

    if args.oc_bgp_filter:
        args.filter = '<bgp xmlns="http://openconfig.net/yang/bgp"/>'
    
    # m =  manager.connect(host=args.host,
    #                      port=args.port,
    #                      username=args.username,
    #                      password=args.password,
    #                      device_params={'name': 'csr'})
    
    def iosxr_unknown_host_cb(host, fingerprint):
        return True
    m =  manager.connect(host=args.host,
                         port=args.port,
                         username=args.username,
                         password=args.password,
                         allow_agent=False,
                         look_for_keys=False,
                         hostkey_verify=False,
                         unknown_host_cb=iosxr_unknown_host_cb)

    if args.get_running:
        get_running_config(m, filter=args.filter)
    elif args.basic:
        oc_basic(m)
    elif args.add_neighbor:
        oc_add_neighbor(m, args.neighbor_addr, args.remote_as, args.description)
    elif args.del_neighbor:
        oc_del_neighbor(m, args.neighbor_addr)
    elif args.add_del_neighbor:
        oc_add_neighbor(m, args.neighbor_addr, args.remote_as, args.description)
        oc_del_neighbor(m, args.neighbor_addr)
    elif args.add_static_route:
        add_static_route_default_vrf(m, '', '', '', '', '')
