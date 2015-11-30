#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Template
from lxml import etree
import logging


add_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
    <interface-virtual/>
   </interface-configuration>
  </interface-configurations>
</config>""")

add_loopback_with_ip = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>Loopback11</interface-name>
    <interface-virtual/>
    <ipv4-network xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-io-cfg">
     <addresses>
      <primary>
       <address>{{IP}}</address>
       <netmask>{{NETMASK}}</netmask>
      </primary>
     </addresses>
    </ipv4-network>
   </interface-configuration>
  </interface-configurations>
</config>""")

del_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration nc:operation="delete">
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
   </interface-configuration>
  </interface-configurations>
</config>""")

add_vrf_to_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
    <vrf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-rsi-cfg">{{VRF}}</vrf>
   </interface-configuration>
  </interface-configurations>
</config>""")

del_vrf_from_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
    <vrf nc:operation="delete" xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-rsi-cfg"/>
   </interface-configuration>
  </interface-configurations>
</config>""")

add_ip_to_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
    <ipv4-network xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-io-cfg">
     <addresses>
      <primary>
       <address>{{IP}}</address>
       <netmask>{{NETMASK}}</netmask>
      </primary>
     </addresses>
    </ipv4-network>
   </interface-configuration>
  </interface-configurations>
</config>""")

del_ip_from_loopback = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>{{INTF}}</interface-name>
    <ipv4-network nc:operation="delete" xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-io-cfg"/>
   </interface-configuration>
  </interface-configurations>
</config>""")


def apply_template(m, t, commit=True, **kwargs):
    if m is None:
        print >>sys.stderr, "Not enough parameters to apply the template!"
    data = t.render(kwargs)
    m.edit_config(data,
                  format='xml',
                  target='candidate')
    if commit:
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
    parser.add_argument('--intf', type=str, required=False, default="Loopback11",
                        help="A name for an interface")
    parser.add_argument('--ip', type=str, required=False, default="192.168.1.1",
                        help="Specific IP adress to add")
    parser.add_argument('--netmask', type=str, required=False, default="255.255.255.0",
                        help="Specific IP adress to add")
    parser.add_argument('--vrf', type=str, required=False, default="FOO",
                        help="Specific VRF to add")

    # Only one type of filter
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="XML-formatted netconf subtree filter")

    # Basic operations
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--del-interface', action='store_true',
                   help="Delete the canned interface")
    g.add_argument('--del-ip', action='store_true',
                   help="Delete the IP address from the canned interface")
    g.add_argument('--del-vrf', action='store_true',
                   help="Delete the VRF from the canned interface")
    g.add_argument('--add-interface', action='store_true',
                   help="Add the canned interface")
    g.add_argument('--add-vrf', action='store_true',
                   help="Add a VRF to the canned interface")
    g.add_argument('--add-ip', action='store_true',
                   help="Add an IP address to the canned interface")
    g.add_argument('--add-all-vrf-first', action='store_true',
                   help="Add interface, VRF and IP address in one transaction")
    g.add_argument('--add-all-ip-first', action='store_true',
                   help="Add interface, VRF and IP address in one transaction, IP first")
    g.add_argument('--move-vrf-naive', action='store_true',
                   help="Naively change the VRF from FOO to BAR")
    g.add_argument('--move-vrf-complex', action='store_true',
                   help="Change the VRF from FOO to BAR, but deleting and re-applying IP as well")
    
    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        for l in ['ncclient.transport.ssh', 'ncclient.transport.session', 'ncclient.operations.rpc']:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    #
    # Could use this extra param instead of the last four arguments
    # specified below:
    #
    # device_params={'name': 'iosxr'}
    #
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

    #
    # Primitives to add/remove interface, IP and VRF
    #
    elif args.add_interface:
        apply_template(m, add_loopback, INTF=args.intf, commit=True)
    elif args.del_interface:
        apply_template(m, del_loopback, INTF=args.intf, commit=True)

    elif args.add_vrf:
        apply_template(m, add_vrf_to_loopback, INTF=args.intf, VRF=args.vrf, commit=True)
    elif args.del_vrf:
        apply_template(m, del_vrf_from_loopback, INTF=args.intf, commit=True)

    elif args.add_ip:
        apply_template(m, add_ip_to_loopback,
                       INTF=args.intf, IP=args.ip, NETMASK=args.netmask,
                       commit=True)
    elif args.del_ip:
        apply_template(m, del_ip_from_loopback, INTF=args.intf, commit=True)


    elif args.add_all_vrf_first:
        #
        # With no interface cinfig in place, this works fine.
        #
        apply_template(m, add_loopback,
                       INTF=args.intf,
                       commit=False)
        apply_template(m, add_vrf_to_loopback,
                       INTF=args.intf, VRF=args.vrf,
                       commit=False)
        apply_template(m, add_ip_to_loopback,
                       INTF=args.intf, IP=args.ip, NETMASK=args.netmask,
                       commit=True)

    elif args.add_all_ip_first:
        #
        # With no interface config in place, this works fine.
        #
        apply_template(m, add_loopback,
                       INTF=args.intf,
                       commit=False)
        apply_template(m, add_ip_to_loopback,
                       INTF=args.intf, IP=args.ip, NETMASK=args.netmask,
                       commit=False)
        apply_template(m, add_vrf_to_loopback,
                       INTF=args.intf, VRF=args.vrf,
                       commit=True)

    #
    # Very naively just change the VRF. If the interface already has
    # an IP address, this will fail.
    #
    elif args.move_vrf_naive:
        apply_template(m, add_vrf_to_loopback,
                       INTF=args.intf, VRF=args.vrf,
                       commit=True)

    #
    # Move the VRF in a more complex way, namely by removing the IP,
    # changing the VRF and then adding back the IP adress. This is all
    # in a single transaction, but across multiple messages to
    # backend.
    #
    elif args.move_vrf_complex:
        apply_template(m, del_ip_from_loopback,
                       INTF=args.intf,
                       commit=False)
        apply_template(m, add_vrf_to_loopback,
                       INTF=args.intf, VRF=args.vrf,
                       commit=False)
        apply_template(m, add_ip_to_loopback,
                       INTF=args.intf, IP=args.ip, NETMASK=args.netmask,
                       commit=True)
