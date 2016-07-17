#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager
import ncclient.operations.rpc
from jinja2 import Template
from lxml import etree
import logging

big_class_maps = Template("""<config>
  <native xmlns="urn:ios">
    <class-map>
      <name>BRONZE</name>
      <prematch>match-all</prematch>
      <match>
        <dscp>af11</dscp>
      </match>
    </class-map>
    <class-map>
      <name>GOLD</name>
      <prematch>match-all</prematch>
      <match>
        <dscp>af31</dscp>
      </match>
    </class-map>
    <class-map>
      <name>MULTICAST</name>
      <prematch>match-any</prematch>
      <match>
        <vlan>100</vlan>
        <vlan>200</vlan>
      </match>
    </class-map>
    <class-map>
      <name>PLATINUM</name>
      <prematch>match-all</prematch>
      <match>
        <dscp>af41</dscp>
      </match>
    </class-map>
    <class-map>
      <name>REAL-TIME</name>
      <prematch>match-all</prematch>
      <match>
        <dscp>ef</dscp>
      </match>
    </class-map>
    <class-map>
      <name>SILVER</name>
      <prematch>match-all</prematch>
      <match>
        <dscp>af21</dscp>
      </match>
    </class-map>
    <class-map>
      <name>SITE1</name>
      <prematch>match-all</prematch>
      <match>
        <vlan>100</vlan>
      </match>
    </class-map>
    <class-map>
      <name>SITE2</name>
      <prematch>match-all</prematch>
      <match>
        <vlan>200</vlan>
      </match>
    </class-map>
  </native>
</config>""")


"""
CLI equivalent policy:

policy-map SITE1-GRANDCHILD
  class REAL-TIME
    priority 256
  class PLATINUM
    bandwidth 256
    set dscp af41
    police 256000 conform-action transmit exceed-action set-dscp-transmit af43
  class GOLD 
    bandwidth 128
    set dscp af31
    police 128000 conform-action transmit exceed-action set-dscp-transmit af33
  class class-default 
    bandwidth 128

"""
big_qos_site1_grandchild = Template("""<config>
  <native xmlns="urn:ios">
    <policy-map>
      <name>SITE1-GRANDCHILD</name>
      <class>
        <name>GOLD</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>128</bits>
          </bandwidth>
        </action-list>
        <action-list>
          <action-type>set</action-type>
          <set>
            <dscp>af31</dscp>
          </set>
        </action-list>
        <action-list>
          <action-type>police</action-type>
          <police-target-bitrate>
            <police>
              <bit-rate>128000</bit-rate>
              <actions>
                <conform-transmit>
                  <conform-action>
                    <transmit/>
                  </conform-action>
                </conform-transmit>
                <exceed-set-dscp-transmit>
                  <exceed-action>
                    <set-dscp-transmit>af33</set-dscp-transmit>
                  </exceed-action>
                </exceed-set-dscp-transmit>
              </actions>
            </police>
          </police-target-bitrate>
        </action-list>
      </class>
      <class>
        <name>PLATINUM</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>256</bits>
          </bandwidth>
        </action-list>
        <action-list>
          <action-type>set</action-type>
          <set>
            <dscp>af41</dscp>
          </set>
        </action-list>
        <action-list>
          <action-type>police</action-type>
          <police-target-bitrate>
            <police>
              <bit-rate>256000</bit-rate>
              <actions>
                <conform-transmit>
                  <conform-action>
                    <transmit/>
                  </conform-action>
                </conform-transmit>
                <exceed-set-dscp-transmit>
                  <exceed-action>
                    <set-dscp-transmit>af43</set-dscp-transmit>
                  </exceed-action>
                </exceed-set-dscp-transmit>
              </actions>
            </police>
          </police-target-bitrate>
        </action-list>
      </class>
      <class>
        <name>REAL-TIME</name>
        <action-list>
          <action-type>priority</action-type>
          <priority>
            <kilo-bits>256</kilo-bits>
          </priority>
        </action-list>
      </class>
      <class>
        <name>class-default</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>128</bits>
          </bandwidth>
        </action-list>
      </class>
    </policy-map>
  </native>
</config>""")

"""
CLI equivalent policy:

policy-map SITE2-GRANDCHILD
  class REAL-TIME
    priority 256
  class PLATINUM
    bandwidth 256
    set dscp af41
    police 256000 conform-action transmit exceed-action set-dscp-transmit af43
  class GOLD 
    bandwidth 128
    set dscp af31
    police 128000 conform-action transmit exceed-action set-dscp-transmit af33
  class class-default 
    bandwidth 128

"""
big_qos_site2_grandchild = Template("""<config>
  <native xmlns="urn:ios">
    <policy-map>
      <name>SITE2-GRANDCHILD</name>
      <class>
        <name>GOLD</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>128</bits>
          </bandwidth>
        </action-list>
        <action-list>
          <action-type>set</action-type>
          <set>
            <dscp>af31</dscp>
          </set>
        </action-list>
        <action-list>
          <action-type>police</action-type>
          <police-target-bitrate>
            <police>
              <bit-rate>128000</bit-rate>
              <actions>
                <conform-transmit>
                  <conform-action>
                    <transmit/>
                  </conform-action>
                </conform-transmit>
                <exceed-set-dscp-transmit>
                  <exceed-action>
                    <set-dscp-transmit>af33</set-dscp-transmit>
                  </exceed-action>
                </exceed-set-dscp-transmit>
              </actions>
            </police>
          </police-target-bitrate>
        </action-list>
      </class>
      <class>
        <name>PLATINUM</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>256</bits>
          </bandwidth>
        </action-list>
        <action-list>
          <action-type>set</action-type>
          <set>
            <dscp>af41</dscp>
          </set>
        </action-list>
        <action-list>
          <action-type>police</action-type>
          <police-target-bitrate>
            <police>
              <bit-rate>256000</bit-rate>
              <actions>
                <conform-transmit>
                  <conform-action>
                    <transmit/>
                  </conform-action>
                </conform-transmit>
                <exceed-set-dscp-transmit>
                  <exceed-action>
                    <set-dscp-transmit>af43</set-dscp-transmit>
                  </exceed-action>
                </exceed-set-dscp-transmit>
              </actions>
            </police>
          </police-target-bitrate>
        </action-list>
      </class>
      <class>
        <name>REAL-TIME</name>
        <action-list>
          <action-type>priority</action-type>
          <priority>
            <kilo-bits>256</kilo-bits>
          </priority>
        </action-list>
      </class>
      <class>
        <name>class-default</name>
        <action-list>
          <action-type>bandwidth</action-type>
          <bandwidth>
            <bits>128</bits>
          </bandwidth>
        </action-list>
      </class>
    </policy-map>
  </native>
</config>""")


big_qos_site_child = Template("""<config>
  <native xmlns="urn:ios">
    <policy-map>
      <name>SITE-CHILD</name>
      <class>
        <name>SITE1</name>
        <action-list>
          <action-type>service-policy</action-type>
          <service-policy>SITE1-GRANDCHILD</service-policy>
        </action-list>
      </class>
      <class>
        <name>SITE2</name>
        <action-list>
          <action-type>service-policy</action-type>
          <service-policy>SITE2-GRANDCHILD</service-policy>
        </action-list>
      </class>
    </policy-map>
  </native>
</config>""")

big_qos_interface_parent = Template("""<config>
  <native xmlns="urn:ios">
    <policy-map>
      <name>INTERFACE-PARENT</name>
      <class>
        <name>MULTICAST</name>
        <action-list>
          <action-type>shape</action-type>
          <shape>
            <average>
              <bit-rate>2512000</bit-rate>
            </average>
          </shape>
        </action-list>
        <action-list>
          <action-type>service-policy</action-type>
          <service-policy>SITE-CHILD</service-policy>
        </action-list>
      </class>
    </policy-map>
  </native>
</config>""")

route_map_add = Template("""<config>
  <native xmlns="urn:ios">
    <route-map>
      <name>{{NAME}}</name>
      <sequence>{{SEQ}}</sequence>
      <operation>permit</operation>
      <set>
        <local-preference>1001</local-preference>
      </set>
      <match>
        <community>
          <name>1</name>
          <name>2</name>
        </community>
      </match>
    </route-map>
  </native>
</config>""")


route_map_del = Template("""<config>
  <native xmlns="urn:ios">
    <route-map nc:operation="delete">
      <name>{{NAME}}</name>
      <sequence>{{SEQ}}</sequence>
    </route-map>
  </native>
</config>""")


bind_input_routemap_to_neighbor = Template("""<config>
  <native xmlns="urn:ios">
    <router>
      <bgp>
        <as-no>101</as-no>
        <neighbor>
          <id>{{NEIGHBOR}}</id>
          <route-map>
            <inout>in</inout>
            <route-map-name>{{NAME}}</route-map-name>
          </route-map>
        </neighbor>
      </bgp>
    </router>
  </native>
</config>""")



unbind_input_routemap_to_neighbor = Template("""<config>
  <native xmlns="urn:ios">
    <router>
      <bgp>
        <as-no>101</as-no>
        <neighbor>
          <id>{{NEIGHBOR}}</id>
          <route-map nc:operation="delete">
            <inout>in</inout>
            <route-map-name>{{NAME}}</route-map-name>
          </route-map>
        </neighbor>
      </bgp>
    </router>
  </native>
</config>""")


classifier_entry_add = Template("""<config>
  <classifiers xmlns="urn:ietf:params:xml:ns:yang:ietf-diffserv-classifier">
    <classifier-entry>
      <classifier-entry-name>BAR</classifier-entry-name>
      <classifier-entry-filter-operation>match-all-filter</classifier-entry-filter-operation>
      <filter-entry>
        <filter-type xmlns:policy-types="urn:ietf:params:xml:ns:yang:c3pl-types">policy-types:ipv4-acl-name</filter-type>
        <filter-logical-not>false</filter-logical-not>
        <ipv4-acl-name-cfgs xmlns="urn:ietf:params:xml:ns:yang:cisco-policy-filters">
          <ipv4-acl-name-cfg>
            <ip-acl-name>WIBBLE</ip-acl-name>
          </ipv4-acl-name-cfg>
        </ipv4-acl-name-cfgs>
      </filter-entry>
      <filter-entry>
        <filter-type xmlns:policy-types="urn:ietf:params:xml:ns:yang:c3pl-types">policy-types:input-interface</filter-type>
        <filter-logical-not>false</filter-logical-not>
        <input-interface-cfgs xmlns="urn:ietf:params:xml:ns:yang:cisco-policy-filters">
          <input-interface-cfg>
            <if-name>GigabitEthernet1</if-name>
          </input-interface-cfg>
        </input-interface-cfgs>
      </filter-entry>
      <filter-entry>
        <filter-type xmlns:policy-types="urn:ietf:params:xml:ns:yang:c3pl-types">policy-types:ip-rtp</filter-type>
        <filter-logical-not>false</filter-logical-not>
      </filter-entry>
      <filter-entry>
        <filter-type xmlns:policy-types="urn:ietf:params:xml:ns:yang:c3pl-types">policy-types:ip-rtp</filter-type>
        <filter-logical-not>true</filter-logical-not>
      </filter-entry>
    </classifier-entry>
  </classifiers>
</config>""")


classifier_entry_del = Template("""<config>
  <classifiers xmlns="urn:ietf:params:xml:ns:yang:ietf-diffserv-classifier">
    <classifier-entry nc:operation="delete">
      <classifier-entry-name>BAR</classifier-entry-name>
    </classifier-entry>
  </classifiers>
</config>""")


policy_add = Template("""<config>
<policies xmlns="urn:ietf:params:xml:ns:yang:ietf-diffserv-policy" xmlns:action="urn:ietf:params:xml:ns:yang:ietf-diffserv-action">         
    <policy-entry>
      <policy-name>POLICY4</policy-name> 
      <classifier-entry>
        <classifier-entry-name>BAR</classifier-entry-name>
        <classifier-action-entry-cfg>
          <action-type>action:max-rate</action-type>
            <action:max-rate-cfg>
              <action:absolute-rate>100000</action:absolute-rate>
              <action:absolute-rate-metric>none</action:absolute-rate-metric>
              <action:absolute-rate-units>bps</action:absolute-rate-units>
            </action:max-rate-cfg>
          </classifier-action-entry-cfg>
        </classifier-entry>
      </policy-entry>
  </policies>
</config>""")


def add_route_map(m, name, seq):
    """Simple example to add a route map entry.

    """
    if m is None or name is None or seq is None:
        print >>sys.stderr, "Not enough parameters to add a route map!"
    data = route_map_add.render(NAME=name, SEQ=seq)
    m.edit_config(data, format='xml', target='running')


def del_route_map(m, name, seq):
    """Simple example to delete a route map entry.

    """
    if m is None or name is None or seq is None:
        print >>sys.stderr, "Not enough parameters to add a route map!"
    data = route_map_del.render(NAME=name, SEQ=seq)
    m.edit_config(data, format='xml', target='running')


def bind_input_route_map(m, neighbor, name):
    """Simple example to delete a route map entry.

    """
    if m is None or name is None or neighbor is None:
        print >>sys.stderr, "Not enough parameters to add a route map!"
    data = bind_input_routemap_to_neighbor.render(NEIGHBOR=neighbor, NAME=name)
    m.edit_config(data, format='xml', target='running')


def unbind_input_route_map(m, neighbor, name):
    """Simple example to delete a route map entry.

    """
    if m is None or name is None or neighbor is None:
        print >>sys.stderr, "Not enough parameters to add a route map!"
    data = unbind_input_routemap_to_neighbor.render(NEIGHBOR=neighbor, NAME=name)
    m.edit_config(data, format='xml', target='running')


def add_class_map(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a class map!"
    data = classifier_entry_add.render()
    m.edit_config(data, format='xml', target='running')


def del_class_map(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to delete a class map!"
    data = classifier_entry_del.render()
    m.edit_config(data, format='xml', target='running')


def add_policy_map(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a policy map!"
    data = policy_add.render()
    m.edit_config(data, format='xml', target='running')


def add_big_class_config(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a policy map!"
    data = big_class_maps.render()
    m.edit_config(data, format='xml', target='running')


def add_big_policy_config(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a policy map!"
    try:
        for p in [big_qos_site1_grandchild, big_qos_site2_grandchild, big_qos_site_child, big_qos_interface_parent]:
            data = p.render()
            print data
            res = m.edit_config(data, format='xml', target='running')
            print res
    except ncclient.operations.rpc.RPCError as e:
        print >>sys.stderr, e


def problem_for_peter(m):
    if m is None:
        print >>sys.stderr, "Not enough parameters to add a policy map!"
    try:
        for p in [big_class_maps, big_qos_site1_grandchild, big_qos_site2_grandchild, big_qos_interface_parent]:
            data = p.render()
            print data
            res = m.edit_config(data, format='xml', target='running')
            print res
    except ncclient.operations.rpc.RPCError as e:
        print >>sys.stderr, e


def copy_running_config(m):
    c = m.copy_config(source='running', target='startup')
        
        
def get_running_config(m, filter=None):
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter)).data_xml
    else:
        c = m.get_config(source='running').data_xml
    print etree.tostring(etree.fromstring(c), pretty_print=True)
        
        
if __name__ == '__main__':

    parser = ArgumentParser(description='Select report options.')

    # Input parameters
    parser.add_argument('--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")
    parser.add_argument('-r', '--route-map', type=str, 
                        help="Name of a route map")
    parser.add_argument('-s', '--seq', type=str, 
                        help="Sequence number in a route map")
    parser.add_argument('--description', type=str, 
                        help="Specify the neighbor's description, just a string (quote it!)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do some verbose logging")

    # Only one type of filter
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="XML-formatted netconf subtree filter")

    # Basic operations
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('-a', '--add-route-map', action='store_true',
                   help="Add a BGP neighbor")
    g.add_argument('-d', '--del-route-map', action='store_true',
                   help="Delete a route map entry")
    g.add_argument('-b', '--bind-route-map', action='store_true',
                   help="Bind an input route map")
    g.add_argument('--unbind-route-map', action='store_true',
                   help="Unbind an input route map")
    g.add_argument('--add-class-map', action='store_true',
                   help="Add a canned class map definition")
    g.add_argument('--del-class-map', action='store_true',
                   help="Delete a canned class map definition")
    g.add_argument('--add-policy-map', action='store_true',
                   help="Add a canned class map definition")
    g.add_argument('--copy-config', action='store_true',
                   help="It's all in the name!")
    g.add_argument('--big-class', action='store_true',
                   help="It's all in the name!")
    g.add_argument('--big-policy', action='store_true',
                   help="It's all in the name!")
    g.add_argument('--problem-for-peter', action='store_true',
                   help="It's all in the name!")
    
    args = parser.parse_args()

    if args.verbose:
        rootLogger = logging.getLogger('ncclient.transport.session')
        rootLogger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        rootLogger.addHandler(handler)

    m =  manager.connect(host=args.host,
                         port=args.port,
                         username=args.username,
                         password=args.password,
                         device_params={'name':"csr"})

    if args.get_running:
        get_running_config(m, filter=args.filter)
    elif args.add_route_map:
        add_route_map(m, args.route_map, args.seq)
    elif args.del_route_map:
        del_route_map(m, args.route_map, args.seq)
    elif args.bind_route_map:
        bind_input_route_map(m, '1.2.3.4', args.route_map)
    elif args.unbind_route_map:
        unbind_input_route_map(m, '1.2.3.4', args.route_map)
    elif args.add_class_map:
        add_class_map(m)
    elif args.del_class_map:
        del_class_map(m)
    elif args.add_policy_map:
        add_policy_map(m)
    elif args.copy_config:
        copy_running_config(m)
    elif args.big_class:
        add_big_class_config(m)
    elif args.big_policy:
        add_big_policy_config(m)
    elif args.problem_for_peter:
        problem_for_peter(m)
        
