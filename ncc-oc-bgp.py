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


shut = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/2</interface-name>
    <shutdown/>
   </interface-configuration>
  </interface-configurations>
</config>""")


no_shut = Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/2</interface-name>
    <shutdown nc:operation="delete"/>
   </interface-configuration>
  </interface-configurations>
</config>""")


named_templates = {
    'set_autoneg_true': Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation>true</auto-negotiation>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>"""),
    'set_autoneg_override': Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation>override</auto-negotiation>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>"""),
    'delete_autoneg': Template("""<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation nc:operation="delete"/>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>"""),
    'delete_ebgp_multihop_enabled': Template("""<config>
  <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor>
     <neighbor-address>192.168.1.222</neighbor-address>
     <ebgp-multihop>
      <config>
       <enabled nc:operation="delete"/>
      </config>
     </ebgp-multihop>
    </neighbor>
   </neighbors>
  </bgp>
</config>"""),
    'set_ebgp_multihop_enabled_true': Template("""<config>
  <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor>
     <neighbor-address>192.168.1.222</neighbor-address>
     <ebgp-multihop>
      <config>
       <enabled>true</enabled>
      </config>
     </ebgp-multihop>
    </neighbor>
   </neighbors>
  </bgp>
</config>"""),
    'set_ebgp_multihop_enabled_false': Template("""<config>
  <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor>
     <neighbor-address>192.168.1.222</neighbor-address>
     <ebgp-multihop>
      <config>
       <enabled>false</enabled>
      </config>
     </ebgp-multihop>
    </neighbor>
   </neighbors>
  </bgp>
</config>"""),
    'classmap_einarnn_3': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-asr9k-policymgr-cfg">
   <class-maps>
    <class-map>
     <type>qos</type>
     <name>EINARNN_3</name>
     <class-map-mode-match-any/>
     <match>
      <ipv4-dscp>42-45</ipv4-dscp>
     </match>
    </class-map>
   </class-maps>
  </policy-manager>
</config>"""),
    'classmap_einarnn_4': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-asr9k-policymgr-cfg">
   <class-maps>
    <class-map>
     <type>qos</type>
     <name>EINARNN_4</name>
     <class-map-mode-match-any/>
     <match>
      <ipv4-dscp>42</ipv4-dscp>
      <ipv4-dscp>43</ipv4-dscp>
      <ipv4-dscp>44</ipv4-dscp>
      <ipv4-dscp>45</ipv4-dscp>
     </match>
    </class-map>
   </class-maps>
  </policy-manager>
</config>"""),
    'classmap_einarnn_5': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-asr9k-policymgr-cfg">
   <class-maps>
    <class-map>
     <type>qos</type>
     <name>EINARNN_5</name>
     <class-map-mode-match-any/>
     <match>
      <ipv4-dscp>af21</ipv4-dscp>
      <ipv4-dscp>af22</ipv4-dscp>
      <ipv4-dscp>cs2</ipv4-dscp>
      <ipv4-dscp>cs6</ipv4-dscp>
     </match>
    </class-map>
   </class-maps>
  </policy-manager>
</config>"""),
    'classmap_einarnn_6': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-asr9k-policymgr-cfg">
   <class-maps>
    <class-map>
     <type>qos</type>
     <name>EINARNN_6</name>
     <class-map-mode-match-any/>
     <match>
      <ipv4-dscp>42</ipv4-dscp>
      <ipv4-dscp>44</ipv4-dscp>
      <ipv4-dscp>45</ipv4-dscp>
      <ipv4-dscp>46</ipv4-dscp>
      <ipv6-dscp>42</ipv6-dscp>
      <ipv6-dscp>44</ipv6-dscp>
      <ipv6-dscp>45</ipv6-dscp>
      <ipv6-dscp>46</ipv6-dscp>
     </match>
    </class-map>
   </class-maps>
  </policy-manager>
</config>"""),
    'classmap_delete_einarnn_all': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-asr9k-policymgr-cfg">
   <class-maps>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>EINARNN_3</name>
    </class-map>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>EINARNN_4</name>
    </class-map>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>EINARNN_5</name>
    </class-map>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>EINARNN_6</name>
    </class-map>
   </class-maps>
  </policy-manager>
</config>"""),
    'xxx': Template("""<config>
      <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
        <class-maps>
          <class-map>
            <type>qos</type>
            <name>XXX</name>
            <match>
              <mpls-experimental-topmost>5</mpls-experimental-topmost>
              <ipv4-dscp>42</ipv4-dscp>
              <ipv4-dscp>44</ipv4-dscp>
              <ipv4-dscp>46</ipv4-dscp>
              <ipv4-dscp>45</ipv4-dscp>
              <qos-group>1</qos-group>
            </match>
            <class-map-mode-match-any/>
          </class-map>
        </class-maps>
      </policy-manager>
</config>"""),
    'xxx_del': Template("""<config>
      <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
        <class-maps>
          <class-map nc:operation="delete">
            <type>qos</type>
            <name>XXX</name>
          </class-map>
        </class-maps>
      </policy-manager>
</config>"""),

    #
    # create a simple policy
    #
    'policy_test_cr': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <policy-maps>
    <policy-map>
     <type>qos</type>
     <name>testtest</name>
     <policy-map-rule>
      <class-name>dscp-31</class-name>
      <class-type>qos</class-type>
      <police>
       <rate>
        <value>100</value>
        <units>kbps</units>
       </rate>
       <burst>
        <value>200</value>
        <units>bytes</units>
       </burst>
      </police>
     </policy-map-rule>
    </policy-map>
   </policy-maps>
  </policy-manager>
</config"""),
    
    'class_dscp31_cr': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <class-maps>
    <class-map>
     <type>qos</type>
     <name>dscp-31</name>
     <class-map-mode-match-any/>
     <match>
      <dscp>31</dscp>
     </match>
    </class-map>
   </class-maps>
  </policy-manager>
</config"""),

    'class_dscp31_del': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <class-maps>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>dscp-31</name>
    </class-map>
   </class-maps>
  </policy-manager>
</config"""),

    #
    # create a simple policy
    #
    'policy_test_del': Template("""<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <policy-maps>
    <policy-map nc:operation="delete">
     <type>qos</type>
     <name>test</name>
    </policy-map>
   </policy-maps>
</config"""),
    
    #
    #  create an empty VRF
    #
    'empty_vrf': Template("""<config>
  <vrfs xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-rsi-cfg"/>
</config>"""),

    #
    # create empty l2vpn elements
    #
    'empty_l2vpn': Template("""<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg" nc:operation="merge">
    <database>
      <bridge-domain-groups/>
    </database>
  </l2vpn>
</config>"""),

    #
    # delete all l2vpn elements
    #
    'delete_l2vpn': Template("""<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg" nc:operation="delete">
  </l2vpn>
</config>"""),

    #
    # create other l2vpn config
    #
    'more_l2vpn': Template("""<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg" nc:operation="merge">
    <database>
      <bridge-domain-groups>
	<bridge-domain-group xmlns:a="urn:ietf:params:xml:ns:netconf:base:1.0">
	  <name>SERVICE</name>
	  <bridge-domains>
	    <bridge-domain>
	      <name>ESP-vPE1</name>
	      <bd-attachment-circuits>
		<bd-attachment-circuit>
		  <name>Bundle-Ether46001.1</name>
		</bd-attachment-circuit>
	      </bd-attachment-circuits>
	    </bridge-domain>
	  </bridge-domains>
	</bridge-domain-group>
      </bridge-domain-groups>
    </database>
  </l2vpn>
</config>"""),

    #
    # delete bridge-domain-groups
    #
    'l2vpn_bdgroups_del': Template("""<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg">
    <database>
      <bridge-domain-groups nc:operation="delete">
	<bridge-domain-group>
	  <name>SERVICE</name>
	  <bridge-domains>
	    <bridge-domain>
	      <name>ESP-vPE1</name>
	      <bd-attachment-circuits>
		<bd-attachment-circuit>
		  <name>Bundle-Ether46001.1</name>
		</bd-attachment-circuit>
	      </bd-attachment-circuits>
	    </bridge-domain>
	  </bridge-domains>
	</bridge-domain-group>
      </bridge-domain-groups>
    </database>
  </l2vpn>
</config>"""),

    #
    # OSPF test
    #
    'simple_ospf': Template("""<config>
<ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-ospf-cfg">
 <processes>
  <process>
   <process-name>apphost</process-name>
   <default-vrf>
    <area-addresses>
     <area-area-id>
      <area-id>0</area-id>
      <name-scopes>
       <name-scope>
        <interface-name>GigabitEthernet0/0/0/0</interface-name>
        <cost>30</cost>
       </name-scope>
      </name-scopes>
      </area-area-id>
     </area-addresses>
    </default-vrf>
  </process>
 </processes>
</ospf>
</config>"""),

}


def add_static_route_default_vrf(m, prefix, prefix_length, next_hop_intf, next_hop_addr, next_hop_path_name):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a neighbor!"
    data = add_static_route_default.render()
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='none')
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


def do_template(m, t, **kwargs):
    data = t.render(kwargs)
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()


def do_templates(m, t_list, default_op='merge', **kwargs):
    for t in t_list:
        tmpl = named_templates[t]
        data = tmpl.render(kwargs)
        m.edit_config(data,
                      format='xml',
                      target='candidate',
                      default_operation=default_op)
    m.commit()


def get_running_config(m, filter=None, xpath=None):
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter)).data_xml
    elif xpath and len(xpath)>0:
        c = m.get_config(source='running', filter=('xpath', xpath)).data_xml
    else:
        c = m.get_config(source='running').data_xml
    print etree.tostring(etree.fromstring(c), pretty_print=True)
        
        
def get(m, filter=None, xpath=None):
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter)).data_xml
    elif xpath and len(xpath)>0:
        c = m.get(filter=('xpath', xpath)).data_xml
    else:
        print ("Need a filter for oper get!")
        return
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
    parser.add_argument('--default-op', type=str, default='merge',
                        help="The NETCONF default operatiopn to use (merge by default")

    # Only one type of filter
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="XML-formatted netconf subtree filter")
    g.add_argument('-x', '--xpath', type=str,
                   help="XPath-formatted filter")
    g.add_argument('-o', '--oc-bgp-filter', action='store_true',
                   help="XML-formatted netconf subtree filter")

    # Basic operations
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--get-oper', action='store_true',
                   help="Get oper data")
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
    g.add_argument('--shut', action='store_true',
                   help="Shutdown interface GiE 0/0/0/2")
    g.add_argument('--no-shut', action='store_true',
                   help="No shutdown interface GiE 0/0/0/2")
    g.add_argument('--do-edit', type=str,
                   help="Execute a named template")
    g.add_argument('--do-edits', type=str, nargs='+',
                   help="Execute a sequence of named templates with an optional default operation and a single commit")
    
    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        for l in ['ncclient.transport.ssh', 'ncclient.transport.session', 'ncclient.operations.rpc']:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    if args.oc_bgp_filter:
        args.filter = '<bgp xmlns="http://openconfig.net/yang/bgp"/>'

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
        if args.xpath:
            get_running_config(m, xpath=args.xpath)
        else:
            get_running_config(m, filter=args.filter)
    elif args.get_oper:
        if args.xpath:
            get(m, xpath=args.xpath)
        else:
            get(m, filter=args.filter)
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
    elif args.shut:
        do_template(m, shut)
    elif args.no_shut:
        do_template(m, no_shut)
    elif args.do_edit:
        do_template(m, named_templates[args.do_edit])
    elif args.do_edits:
        do_templates(m, args.do_edits, default_op=args.default_op)
