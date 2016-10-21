#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Template
from lxml import etree
import logging

#
# Add things people want logged here. Just various netconf things for
# now. SSH disabled as it is just too much right now.
#
LOGGING_TO_ENABLE = [
    'ncclient.transport.ssh',
    'ncclient.transport.session',
    'ncclient.operations.rpc'
]


#
# Some named filters to help people out
#
named_filters = {

    'lldp-all': Template('''
<lldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ethernet-lldp-cfg"/>
'''),

    'vrrp-ipv4-all': Template('''
<vrrp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-vrrp-cfg"/>
'''),

    'qos-oper-intf': Template('''
<qos xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-qos-ma-oper">
  <interface-table>
    <interface>
      <interface-name>{{INTF_NAME}}</interface-name>
      <input/>
    </interface>
  </interface-table>
</qos>
'''),

    'qos-oper-all': Template('''
<qos xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-qos-ma-oper">
  <interface-table>
    <interface>
      <input/>
      <output/>
    </interface>
  </interface-table>
</qos>
'''),

    'ietf-intfs-state': Template('''<interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>'''),
    
    'acls-all': Template('''<ipv4-acl-and-prefix-list xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-acl-cfg"/>'''),
    
    'acl-666': Template('''<ipv4-acl-and-prefix-list xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-acl-cfg">
  <accesses>
    <access>
      <access-list-name>RUBBLE1</access-list-name>
      <access-list-entries>
        <access-list-entry>
          <sequence-number>666</sequence-number>
        </access-list-entry>
        <access-list-entry>
          <sequence-number>777</sequence-number>
        </access-list-entry>
      </access-list-entries>
    </access>
  </accesses>
</ipv4-acl-and-prefix-list>'''),

    'oc-bgp': Template('''<bgp xmlns="http://openconfig.net/yang/bgp"/>'''),

    'intf-brief-all': Template('''<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
  <interface-briefs/>
</interfaces>'''),
    
    'intf-brief': Template('''<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
  <interface-briefs>
    <interface-brief>
      <interface-name>{{INTF_NAME}}</interface-name>
    </interface-brief>
</interfaces>'''),

    'intf-stats': Template('''<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
  <interface-xr>
    <interface>
      <interface-name>{{INTF_NAME}}</interface-name>
      <interface-statistics/>
    </interface>
  </interface-xr>
</interfaces>'''),
    
    'intf-stats-limited': Template('''<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
  <interface-xr>
    <interface>
      <interface-name>{{INTF_NAME}}</interface-name>
      <interface-statistics>
        <full-interface-stats>
          <packets-received/>
          <bytes-received/>
          <packets-sent/>
          <bytes-sent/>
        </full-interface-stats>
      </interface-statistics>
    </interface>
  </interface-xr>
</interfaces>'''),

    'oc-intf': Template('''<interfaces xmlns="http://openconfig.net/yang/interfaces"/>'''),

    'oc-intf-named': Template('''<interfaces xmlns="http://openconfig.net/yang/interfaces">
  <interface>
    <name>{{INTF_NAME}}</name>
  </interface>
</interfaces>'''),
    
    'oc-subintf-named': Template('''<interfaces xmlns="http://openconfig.net/yang/interfaces">
  <interface>
    <name>{{INTF_NAME}}</name>
    <subinterfaces/>
  </interface>
</interfaces>'''),
    
    'oc-subintf-named-and-indexed': Template('''<interfaces xmlns="http://openconfig.net/yang/interfaces">
  <interface>
    <name>{{INTF_NAME}}</name>
    <subinterfaces>
      <subinterface>
        <index>{{SUBINTF_INDEX}}</index>
      </subinterface>
    </subinterfaces>
  </interface>
</interfaces>'''),
    
    'telem-all': Template('''<telemetry-model-driven xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-telemetry-model-driven-cfg"/>'''),
}


#
# Named templates to use with --do-edit and --do-edits
#
named_templates = {
    #
    # simple LLDP
    #
    'lldp-basic': Template('''<config>
  <lldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ethernet-lldp-cfg">
   <timer>10</timer>
  </lldp>
</config>'''),

    'lldp-del': Template('''<config>
  <lldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ethernet-lldp-cfg" nc:operation="remove"/>
</config>'''),

    'lldp-basic-and-del': Template('''<config>
  <lldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ethernet-lldp-cfg">
   <timer>10</timer>
  </lldp>
  <lldp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ethernet-lldp-cfg" nc:operation="remove"/>
</config>'''),

    #
    # XE-specific
    #
    'xe-enable-polling': Template('''<config>
  <netconf-yang xmlns="http://cisco.com/yang/cisco-self-mgmt">
    <cisco-odm xmlns="http://cisco.com/yang/cisco-odm">
      <polling-enable>true</polling-enable>
    </cisco-odm>
  </netconf-yang>
</config>'''),

    #
    # Basic OC BGP  template
    #
    'oc_basic': Template('''<config>
 <bgp xmlns="http://openconfig.net/yang/bgp">
  <global>
   <config>
    <as>123</as>
   </config>
  </global>
 </bgp>
    </config>'''),

    #
    # Add an OC BGP beighbor
    #
    'add_neighbor': Template('''<config>
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
</config>'''),

    #
    # Delete an OC BGP beighbor
    #
    'del_neighbor': Template('''<config>
 <bgp xmlns="http://openconfig.net/yang/bgp">
   <neighbors>
    <neighbor nc:operation='delete'>
     <neighbor-address>{{NEIGHBOR_ADDR}}</neighbor-address>
    </neighbor>
   </neighbors>
  </bgp>
</config>'''),


    #
    # Add static routes using the XR native model. Depends on Loopback0
    # existing.
    #
    'add_static_route_default': Template('''<config>
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
</config>'''),


    #
    # Add static routes using the XR native model. Depends on Loopback0
    # existing.
    #
    'del_static_route_default': Template('''<config>
  <router-static xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-static-cfg">
   <default-vrf>
    <address-family>
     <vrfipv4>
      <vrf-unicast>
       <vrf-prefixes>
        <vrf-prefix nc:operation="remove">
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
        <vrf-prefix nc:operation="remove">
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
</config>'''),


    #
    # Another static route variant
    #
    'foo1_add_static_route_default': Template('''<config>
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
</config>'''),


    #
    # Another static route variant
    #
    'foo2_add_static_route_default': Template('''<config>
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
</config>'''),


    #
    # Shut GigabitEthernet0/0/0/2
    #
    'shut': Template('''<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/2</interface-name>
    <shutdown/>
   </interface-configuration>
  </interface-configurations>
</config>'''),


    #
    # No shut GigabitEthernet0/0/0/2
    #
    'no_shut': Template('''<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/2</interface-name>
    <shutdown nc:operation="delete"/>
   </interface-configuration>
  </interface-configurations>
</config>'''),

    'set_autoneg_true': Template('''<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation>true</auto-negotiation>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>'''),
    
    'set_autoneg_override': Template('''<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation>override</auto-negotiation>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>'''),
    
    'delete_autoneg': Template('''<config>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <ethernet xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-drivers-media-eth-cfg">
      <auto-negotiation nc:operation="delete"/>
     </ethernet>
   </interface-configuration>
  </interface-configurations>
</config>'''),
    
    'delete_ebgp_multihop_enabled': Template('''<config>
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
</config>'''),
    
    'set_ebgp_multihop_enabled_true': Template('''<config>
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
</config>'''),
    
    'set_ebgp_multihop_enabled_false': Template('''<config>
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
</config>'''),
    
    'classmap_einarnn_3': Template('''<config>
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
</config>'''),
    
    'classmap_einarnn_4': Template('''<config>
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
</config>'''),
    
    'classmap_einarnn_5': Template('''<config>
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
</config>'''),
    
    'classmap_einarnn_6': Template('''<config>
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
</config>'''),
    
    'classmap_delete_einarnn_all': Template('''<config>
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
</config>'''),
    
    'xxx': Template('''<config>
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
</config>'''),
    
    'xxx_del': Template('''<config>
      <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
        <class-maps>
          <class-map nc:operation="delete">
            <type>qos</type>
            <name>XXX</name>
          </class-map>
        </class-maps>
      </policy-manager>
</config>'''),

    #
    # create a simple policy
    #
    'policy_test_cr': Template('''<config>
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
</config'''),

    #
    # delete a simple policy
    #
    'policy_test_cr': Template('''<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <policy-maps>
    <policy-map nc:operation="delete">
     <type>qos</type>
     <name>testtest</name>
    </policy-map>
   </policy-maps>
  </policy-manager>
</config'''),

    #
    # create a simple class with a single DSCP match
    #
    'class_dscp31_cr': Template('''<config>
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
</config'''),

    'class_dscp31_del': Template('''<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <class-maps>
    <class-map nc:operation="delete">
     <type>qos</type>
     <name>dscp-31</name>
    </class-map>
   </class-maps>
  </policy-manager>
</config'''),

    #
    # create a simple policy
    #
    'policy_test_del': Template('''<config>
  <policy-manager xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-infra-policymgr-cfg">
   <policy-maps>
    <policy-map nc:operation="delete">
     <type>qos</type>
     <name>test</name>
    </policy-map>
   </policy-maps>
</config'''),
    
    #
    # create empty l2vpn elements
    #
    'empty_l2vpn': Template('''<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg" nc:operation="merge">
    <database>
      <bridge-domain-groups/>
    </database>
  </l2vpn>
</config>'''),

    #
    # delete all l2vpn elements
    #
    'delete_l2vpn': Template('''<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg" nc:operation="delete">
  </l2vpn>
</config>'''),

    #
    # create other l2vpn config
    #
    'l2vpn_bdgroups_cr': Template('''<config>
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
</config>'''),

    #
    # delete bridge-domain-groups
    #
    'l2vpn_bdgroups_del': Template('''<config>
  <l2vpn xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-l2vpn-cfg">
    <database>
      <bridge-domain-groups nc:operation="delete"/>
    </database>
  </l2vpn>
</config>'''),

    #
    # OSPF test
    #
    'simple_ospf': Template('''<config>
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
</config>'''),

    #
    # Enable RESTCONF on a capable box. Needs to have the IP address
    # of the bridge attached to the MgmtEth.
    #
    'restconf-enable': Template('''<config>
  <ip xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-tcp-cfg">
   <cinetd>
    <services>
     <vrfs>
      <vrf>
       <vrf-name>default</vrf-name>
       <ipv4>
        <telnet>
         <tcp>
          <maximum-server>35</maximum-server>
         </tcp>
        </telnet>
       </ipv4>
      </vrf>
     </vrfs>
    </services>
   </cinetd>
  </ip>
  <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
   <interface-configuration>
    <active>act</active>
    <interface-name>Loopback2</interface-name>
    <interface-virtual/>
    <ipv4-network xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-io-cfg">
     <addresses>
      <primary>
       <address>128.0.0.1</address>
       <netmask>255.0.0.0</netmask>
      </primary>
     </addresses>
    </ipv4-network>
    <shutdown nc:operation="remove"/>
   </interface-configuration>
  </interface-configurations>
  <restconf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-man-restconf-cfg">
   <agent>
    <enable/>
   </agent>
  </restconf>
  <web xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-man-http-lighttpd-yang-cfg">
   <server>
    <service>
     <restconf>
      <enable/>
      <http-port>{{RC_HTTP_PORT}}</http-port>
      <https-port>{{RC_HTTPS_PORT}}</https-port>
      <http-enable/>
     </restconf>
    </service>
   </server>
  </web>
  <router-static xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ip-static-cfg">
   <default-vrf>
    <address-family>
     <vrfipv4>
      <vrf-unicast>
       <vrf-prefixes>
        <vrf-prefix>
         <prefix>0.0.0.0</prefix>
         <prefix-length>0</prefix-length>
         <vrf-route>
          <vrf-next-hop-table>
           <vrf-next-hop-interface-name-next-hop-address>
            <interface-name>MgmtEth0/RP0/CPU0/0</interface-name>
            <next-hop-address>{{BRIDGE_IP}}</next-hop-address>
           </vrf-next-hop-interface-name-next-hop-address>
          </vrf-next-hop-table>
         </vrf-route>
        </vrf-prefix>
       </vrf-prefixes>
      </vrf-unicast>
     </vrfipv4>
    </address-family>
   </default-vrf>
  </router-static>
</config>'''),

    #
    # Telemetry stuff
    #
    'telem-cr': Template('''
<config>
  <telemetry-model-driven xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-telemetry-model-driven-cfg">
   <destination-groups>
    <destination-group>
     <destination-id>DGroup1</destination-id>
     <destinations>
      <destination>
       <address-family>ipv6</address-family>
       <ipv6>
        <ipv6-address>2001:db8:0:100::15</ipv6-address>
        <destination-port>5432</destination-port>
        <encoding>self-describing-gpb</encoding>
        <protocol>
         <protocol>tcp</protocol>
         <tls-hostname></tls-hostname>
         <no-tls>0</no-tls>
        </protocol>
       </ipv6>
      </destination>
     </destinations>
    </destination-group>
   </destination-groups>
  </telemetry-model-driven>
</config>'''),

    'telem-del-ipv6-fails': Template('''
<config>
  <telemetry-model-driven xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-telemetry-model-driven-cfg">
   <destination-groups>
    <destination-group>
     <destination-id>DGroup1</destination-id>
     <destinations>
      <destination nc:operation="delete">
       <address-family>ipv6</address-family>
      </destination>
     </destinations>
    </destination-group>
   </destination-groups>
  </telemetry-model-driven>
</config>'''),

    'telem-del-ipv6-works': Template('''
<config>
  <telemetry-model-driven xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-telemetry-model-driven-cfg">
   <destination-groups>
    <destination-group>
     <destination-id>DGroup1</destination-id>
     <destinations>
      <destination>
       <address-family>ipv6</address-family>
       <ipv6 nc:operation="delete">
        <ipv6-address>2001:db8:0:100::15</ipv6-address>
        <destination-port>5432</destination-port>
       </ipv6>
      </destination>
     </destinations>
    </destination-group>
   </destination-groups>
  </telemetry-model-driven>
</config>'''),

}


def do_template(m, t, **kwargs):
    '''Execute a template passed in, using the kwargs passed in to
    complete the rendering.

    '''
    data = t.render(kwargs)

    #
    # For IOS-XR
    #
    m.edit_config(data,
                  format='xml',
                  target='candidate',
                  default_operation='merge')
    m.commit()

    #
    # For IOS-XE
    #
    # m.edit_config(data,
    #               format='xml',
    #               target='running',
    #               default_operation='merge')


def do_templates(m, t_list, default_op='merge', **kwargs):
    """Execute a list of templates, using the kwargs passed in to
    complete the rendering.
    """
    for t in t_list:
        tmpl = named_templates[t]
        data = tmpl.render(kwargs)
        m.edit_config(data,
                      format='xml',
                      target='candidate',
                      default_operation=default_op)
    m.commit()


def get_running_config(m, filter=None, xpath=None):
    """Get running config with a passed in filter. If both types of
    filter are passed in for some reason, the subtree filter "wins".
    """
    import time
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter))
    elif xpath and len(xpath)>0:
        c = m.get_config(source='running', filter=('xpath', xpath))
    else:
        c = m.get_config(source='running')
    print(etree.tostring(c.data, pretty_print=True))
        
        
def get(m, filter=None, xpath=None):
    """Get state with a passed in filter. If both types of filter are
    passed in for some reason, the subtree filter "wins".
    """
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter))
    elif xpath and len(xpath)>0:
        c = m.get(filter=('xpath', xpath))
    else:
        print("Need a filter for oper get!")
        return
    print(etree.tostring(c.data, pretty_print=True))
        
        
if __name__ == '__main__':

    parser = ArgumentParser(description='Select your NETCONF operation and parameters:')

    #
    # NETCONF session parameters
    #
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help="The IP address for the device to connect to (default localhost)")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Username to use for SSH authentication (default 'cisco')")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Password to use for SSH authentication (default 'cisco')")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port (default 830)")
    parser.add_argument('--timeout', type=int, default=60,
                        help="NETCONF operation timeout in seconds (default 60)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Exceedingly verbose logging to the console")
    parser.add_argument('--default-op', type=str, default='merge',
                        help="The NETCONF default operation to use (default 'merge')")

    #
    # Various operation parameters. Put int a kwargs structure for use
    # in template rendering.
    #
    parser.add_argument('-i', '--intf-name', type=str, 
                        help="Specify an interface for general use in templates (no format validation)")
    parser.add_argument('-s', '--subintf-index', type=int, 
                        help="Specify sub-interface index for general use in openconfig templates (no format validation)")
    parser.add_argument('-n', '--neighbor-addr', type=str, 
                        help="Specify a neighbor address (no format validation)")
    parser.add_argument('-r', '--remote-as', type=str, 
                        help="Specify the neighbor's remote AS (no format validation)")
    parser.add_argument('--description', type=str, 
                        help="BGP neighbor description string (quote it!)")
    parser.add_argument('--rc-bridge-ip', type=str,
                        help="Bridge IP address for enabling RESTCONF static route")
    parser.add_argument('--rc-http-port', type=int, default=115,
                        help="HTTP port for RESTCONF (default 115)")
    parser.add_argument('--rc-https-port', type=int, default=116,
                        help="HTTPS port for RESTCONF (default 116)")

    #
    # Only one type of filter allowed.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="NETCONF subtree filter")
    g.add_argument('--named-filter', type=str,
                   help="Named NETCONF subtree filter")
    g.add_argument('-x', '--xpath', type=str,
                   help="NETCONF XPath filter")

    #
    # Basic, mutually exclusive, operations.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--list-templates', action='store_true',
                   help="List out named templates embedded in script")
    g.add_argument('--list-filters', action='store_true',
                   help="List out named filters embedded in script")
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--get-oper', action='store_true',
                   help="Get oper data")
    g.add_argument('--do-edit', type=str,
                   help="Execute a named template")
    g.add_argument('--do-edits', type=str, nargs='+',
                   help="Execute a sequence of named templates with an optional default operation and a single commit")

    #
    # Finally, parse the arguments!
    #
    args = parser.parse_args()

    #
    # Do the named template/filter listing first, then exit.
    #
    if args.list_templates:
        print("Embedded named templates:")
        for k in sorted(iter(named_templates)):
            print("  {}".format(k))
        sys.exit(0)
    elif args.list_filters:
        print("Embedded named filters:")
        for k in sorted(iter(named_filters)):
            print("  {}".format(k))
        sys.exit(0)
    #
    # If the user specified verbose logging, set it up.
    #
    if args.verbose:
        handler = logging.StreamHandler()
        for l in LOGGING_TO_ENABLE:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    #
    # set up various keyword arguments that have specific arguments
    #
    kwargs = {}
    if args.intf_name:
        kwargs['INTF_NAME'] = args.intf_name
    if args.subintf_index:
        kwargs['SUBINTF_INDEX'] = args.subintf_index
    if args.neighbor_addr:
        kwargs['NEIGHBOR_ADDR'] = args.neighbor_addr
    if args.remote_as:
        kwargs['REMOTE_AS'] = args.remote_as
    if args.description:
        kwargs['DESCRIPTION'] = args.description
    if args.rc_bridge_ip:
        kwargs['BRIDGE_IP'] = args.rc_bridge_ip
    if args.rc_http_port:
        kwargs['RC_HTTP_PORT'] = args.rc_http_port
    if args.rc_https_port:
        kwargs['RC_HTTPS_PORT'] = args.rc_https_port

    #
    # This populates the filter if it's a canned filter.
    #
    if args.named_filter:
        args.filter = named_filters[args.named_filter].render(**kwargs)

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
                         timeout=args.timeout,
                         username=args.username,
                         password=args.password,
                         device_params={'name': 'iosxr'} )
                         #allow_agent=False,
                         #look_for_keys=False,
                         #hostkey_verify=False,
                         #unknown_host_cb=iosxr_unknown_host_cb)

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
    elif args.do_edit:
        do_template(m, named_templates[args.do_edit], **kwargs)
    elif args.do_edits:
        do_templates(m, args.do_edits, default_op=args.default_op, **kwargs)
