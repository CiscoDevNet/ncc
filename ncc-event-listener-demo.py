#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
# This sample works with NETCONF ebents of the format:
#
# <notification xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">
#   <eventTime>2018-10-27T18:33:54+00:00</eventTime>
#   <linkDown xmlns='urn:ietf:params:xml:ns:yang:smiv2:IF-MIB'>
#     <object-2>
#       <ifIndex>4</ifIndex>
#       <ifAdminStatus>down</ifAdminStatus>
#     </object-2>
#     <object-3>
#       <ifIndex>4</ifIndex>
#       <ifOperStatus>down</ifOperStatus>
#     </object-3>
#   </linkDown>
# </notification>
#
import sys
from argparse import ArgumentParser
from functools import partial
from ncclient import manager
from lxml import etree
import logging
import time
import datetime
import threading
import re


#
# Get the if-index for an interface from the IOS XE
# Cisco-IOS-XE-interfaces-oper model. The {} are for substitution
# using .format(...).
#
intf_query = '''
<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper">
  <interface>
    <name>{}</name>
    <if-index/>
  </interface>
</interfaces>
'''


#
# Use the IOS XE native model Cisco-IOS-XE-native to bring up an
# iterface (CLI equivalent of "no shutdown"). The {} are for
# substitution using .format(...).
#
intf_no_shut = '''
<nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    <interface>
      <{}>
        <name>{}</name>
        <shutdown nc:operation="remove"/>
      </{}>
    </interface>
  </native>
</nc:config>
'''


#
# Simple example listener to run on a standalone thread.
#
def listener(mgr=None, stream_name=None, if_name=None, if_index=None):
    assert mgr is not None
    assert stream_name is not None
    assert if_name is not None
    assert if_index is not None

    #
    # assume if_name is a simple IOS XE-style interface name like
    # 'GigabitEthernet4'; this woukd clearly be inappropriate for
    # production code!!
    #
    p = re.compile(r'([a-zA-Z]+)([0-9]+)')
    m = p.match(if_name)
    if not m:
        print('cannot find if type and index')
        return
    if_type = m.group(1)
    if_ind = m.group(2)
    intf_no_shut_resolved = intf_no_shut.format(if_type, if_ind, if_type)
    print('Monitoring interface {} with SNMP if-index {}'.format(
        if_name, if_index))

    #
    # Create a subscription and loop waiting for notifications form
    # the device mgr is connected to. Note that other threads can
    # still use the connection.
    #
    mgr.create_subscription(stream_name=stream_name)
    while True:
        # blocking call, but will see ALL notifications
        notif = mgr.take_notification()
        if notif:
            root = notif.notification_ele
            linkDown = root.xpath(
                '//ns1:linkDown/*[ns1:ifIndex={}]/ns1:ifAdminStatus'.format(if_index),
                namespaces={
                    'ns1': 'urn:ietf:params:xml:ns:yang:smiv2:IF-MIB',
                })
            if len(linkDown) > 0:
                print('linkDown event -> ifAdminStatus = {}'.format(linkDown[0].text))
                print('Bringing interface back up...')
                mgr.edit_config(
                    intf_no_shut_resolved,
                    target='running',
                    format='xml')
                print('Done')
            else:
                pass


if __name__ == '__main__':

    parser = ArgumentParser(description='Select your simple poller parameters:')

    # Input parameters
    parser.add_argument('--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do I really need to explain?")

    # other options
    parser.add_argument('--stream', type=str, required=True,
                        help="Event stream to register on")
    parser.add_argument('--if-name', type=str, required=True,
                        help="Interface name to watch for link state events on")

    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        for l in ['ncclient.transport.ssh', 'ncclient.transport.session', 'ncclient.operations.rpc']:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    #
    # Connect
    #
    def unknown_host_cb(host, fingerprint):
        return True
    m =  manager.connect(host=args.host,
                         port=args.port,
                         username=args.username,
                         password=args.password,
                         allow_agent=False,
                         look_for_keys=False,
                         hostkey_verify=False,
                         unknown_host_cb=unknown_host_cb)

    #
    # find the interface if-index for the provided name
    #
    r = m.get(filter=('subtree', intf_query.format(args.if_name)))
    if_index = r.data_ele.xpath(
        '//ns1:if-index',
        namespaces={
            'ns1': 'http://cisco.com/ns/yang/Cisco-IOS-XE-interfaces-oper',
        })
    if len(if_index) == 0:
        print('No ifIndex found got {}'.format(args.if_name))
        sys.exit(1)

    #
    # run the listener
    #
    thr = threading.Thread(
        target=partial(
            listener,
            mgr=m,
            stream_name=args.stream,
            if_name=args.if_name,
            if_index=int(if_index[0].text)))
    thr.start()
    thr.join()
