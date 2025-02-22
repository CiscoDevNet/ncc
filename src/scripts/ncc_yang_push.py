#!/usr/bin/env python
#
# Copyright (c) 2019 Cisco and/or its affiliates
#
import sys
from argparse import ArgumentParser
from functools import partial
from ncclient import manager
from lxml import etree
import logging
import time
import os


#
# Capability constants
#
NC_WRITABLE_RUNNING = 'urn:ietf:params:netconf:capability:writable-running:1.0'
NC_CANDIDATE = 'urn:ietf:params:netconf:capability:candidate:1.0'
NC_NOTIF_1_1 = 'urn:ietf:params:netconf:capability:notification:1.1'

#
# simple XML template to replace periodic suscriptions via netconf
#
replace_periodic_subscription = '''
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <mdt-config-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-cfg">
    <mdt-subscription nc:operation="replace">
      <subscription-id>{subs_id}</subscription-id>
      <base>
        <stream>yang-push</stream>
        <encoding>encode-kvgpb</encoding>
        <period>{period}</period>
        <xpath>{xpath}</xpath>
      </base>
      <mdt-receivers>
        <address>{receiver_ipv4}</address>
        <port>{receiver_port}</port>
        <protocol>grpc-tcp</protocol>
      </mdt-receivers>
    </mdt-subscription>
  </mdt-config-data>
</config>
'''

#
# simple XML template to replace on-change suscriptions via netconf
#
replace_onchange_subscription = '''
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <mdt-config-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-cfg">
    <mdt-subscription nc:operation="replace">
      <subscription-id>{subs_id}</subscription-id>
      <base>
        <stream>yang-push</stream>
        <encoding>encode-kvgpb</encoding>
        <dampening-period>{dampening_period}</dampening-period>
        <xpath>{xpath}</xpath>
      </base>
      <mdt-receivers>
        <address>{receiver_ipv4}</address>
        <port>{receiver_port}</port>
        <protocol>grpc-tcp</protocol>
      </mdt-receivers>
    </mdt-subscription>
  </mdt-config-data>
</config>
'''


#
# siple XML template to remove a subscription by id
#
del_subscription = '''
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <mdt-config-data xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-mdt-cfg">
    <mdt-subscription nc:operation="remove">
      <subscription-id>{subs_id}</subscription-id>
    </mdt-subscription>
  </mdt-config-data>
</config>
'''


#
# display template for a slightly more human readable view of the key
# attributes of a subscription
#
subscription_periodic = '''
Subscription Id {sub_id}
  Receiver {receiver_ipv4}:{receiver_port}
  Period   {period}
  XPath    {xpath}
'''


def replace_subscription(
        edit_config,
        subs_id=None,
        xpath=None,
        receiver_ipv4=None,
        receiver_port=None,
        period=None,
        dampening_period=None):
    '''
    Replace (with netconf semantics) the subscription identified by
    subs_id with the definition passed in, using the edit-config
    function passed in.
    '''
    assert edit_config is not None
    assert subs_id is not None
    assert xpath is not None
    assert receiver_ipv4 is not None
    assert receiver_port is not None
    if period is not None:
        edit_config(replace_periodic_subscription.format(
            subs_id=subs_id,
            xpath=xpath,
            receiver_ipv4=receiver_ipv4,
            receiver_port=receiver_port,
            period=period))
    elif dampening_period is not None:
        edit_config(replace_onchange_subscription.format(
            subs_id=subs_id,
            xpath=xpath,
            receiver_ipv4=receiver_ipv4,
            receiver_port=receiver_port,
            dampening_period=dampening_period))
    else:
        print('Must have period or dampening period!', file=sys.stderr)


def delete_subscription(
        edit_config,
        subs_id=None):
    '''
    Delete a subscription by subscription-id, using the edit-confog
    function passed in.
    '''
    assert edit_config is not None
    assert subs_id is not None
    edit_config(del_subscription.format(subs_id=subs_id))


def list_subscriptions(m):
    '''
    Get and list, in a human readable format, all the subscriptions on
    the device passed in.
    '''
    c = m.get_config(source='running', filter=('xpath', '/mdt-config-data'))
    subs = c.data.xpath('//*[local-name()="mdt-subscription"]')
    for sub in subs:
        #
        # TOTO: somewhat messy code here. Could be better. An XSLT for
        # example, would be much nicer!
        #
        period = None
        dampening_period = None
        sub_id = sub.xpath('*[local-name()="subscription-id"]')[0].text
        xpath = sub.xpath('*/*[local-name()="xpath"]')[0].text
        receiver_ipv4 = sub.xpath('*/*[local-name()="address"]')[0].text
        receiver_port = sub.xpath('*/*[local-name()="port"]')[0].text
        try:
            period = sub.xpath('*/*[local-name()="period"]')[0].text
        except:
            pass
        try:
            dampening_period = sub.xpath('*/*[local-name()="dampening-period"]')[0].text
        except:
            pass        
        if period:
            print(subscription_periodic.format(
                sub_id=sub_id,
                xpath=xpath,
                receiver_ipv4=receiver_ipv4,
                receiver_port=receiver_port,
                period=period))
    
    
def compose_edit_config(m):
    '''
    Look at the capabilities of the device we are connected to for the
    session, and create and return a very specific function to do
    single edit-config operations against that device, including
    proper locking and unlocking and use of commit if necessary.

    '''
    if NC_CANDIDATE in m.server_capabilities:
        def candidate_edit_config(data):
            m.lock(target='running')
            m.lock(target='candidate')
            m.edit_config(data,
                          format='xml',
                          target='candidate')
            m.commit()
            m.unlock(target='candidate')
            m.unlock(target='running')
        return candidate_edit_config
    else:
        def writable_running_edit_config(data):
            m.lock(target='running')
            m.edit_config(data,
                          format='xml',
                          target='running')
            m.unlock(target='running')
        return writable_running_edit_config

        
def main():

    parser = ArgumentParser(description='Select your YANG push parameters:')

    # Input parameters
    parser.add_argument('--host', type=str,
                        default=os.environ.get('NCC_HOST', '127.0.0.1'),
                        help="The IP address for the device to connect to "
                        "(default localhost)")
    parser.add_argument('-u', '--username', type=str,
                        default=os.environ.get('NCC_USERNAME', 'cisco'),
                        help="Username to use for SSH authentication "
                        "(default 'cisco')")
    parser.add_argument('-p', '--password', type=str,
                        default=os.environ.get('NCC_PASSWORD', 'cisco'),
                        help="Password to use for SSH authentication "
                        "(default 'cisco')")
    parser.add_argument('--port', type=int,
                        default=os.environ.get('NCC_PORT', 830),
                        help="Specify this if you want a non-default port "
                        "(default 830)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do I really need to explain?")

    # basic action options
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-l', '--list-subscriptions', action='store_true',
                   help="List all subscriptions and key parameters")
    g.add_argument('-a', '--add-subscription', action='store_true',
                   help="Add a subscription with provided id")
    g.add_argument('-d', '--delete-subscription', action='store_true',
                   help="Delete a subscription with provided id")

    #
    # parameters for adding a subscription
    #
    # fixed fields:
    # - stream   = yang-push
    # - encoding = encode-kvgpb
    # - protocol = grpc-tcp
    #
    # configurable fields
    # - subscription id
    # - xpath
    # - period or dampening-period (mutually exclusive)
    # - receiver ipv4 address
    # - receiver port
    #
    parser.add_argument('-s', '--subscription-id', type=int,
                        help="Subscription id")
    parser.add_argument('-x', '--xpath', type=str,
                        help="The XPath to subscribe to")
    parser.add_argument('--rx-ipv4', type=str,
                        help="Receiver IPv4 address")
    parser.add_argument('--rx-port', type=int,
                        help="Receiver port")
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--period', type=int, default=None,
                   help="Subscription period")
    g.add_argument('--dampening-period', type=int, default=None,
                   help="Subscription dampening period")

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
    # check we can do this; looks ugly because IOS XE advertises
    # NC_NOTIF_1_1 with extra whitespace characters :-(
    #
    has_yang_push = False
    for cap in m.server_capabilities:
        if NC_NOTIF_1_1 in cap:
            has_yang_push = True
            break
    if not has_yang_push:
        print('NETCONF server does not have capability {}'.format(NC_NOTIF_1_1),
              file=sys.stderr)
        m.close_session()
        sys.exit(1)

    #
    # create appropriate edit config function
    #

    #
    # do requested operation
    #
    if args.list_subscriptions:
        list_subscriptions(m)
    elif args.add_subscription:
        fn_edit_config_replace = compose_edit_config(m)
        replace_subscription(
            fn_edit_config_replace,
            subs_id=args.subscription_id,
            xpath=args.xpath,
            receiver_ipv4=args.rx_ipv4,
            receiver_port=args.rx_port,
            period=args.period,
            dampening_period=args.dampening_period)
    elif args.delete_subscription:
        fn_edit_config_delete = compose_edit_config(m)
        delete_subscription(
            fn_edit_config_delete,
            args.subscription_id)
        
    #
    # graceful shutdown
    #
    m.close_session()
