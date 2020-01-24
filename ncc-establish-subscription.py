#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
import datetime
import logging
import os
import signal
import sys
import time

from argparse import ArgumentParser
from lxml import etree
from ncclient import manager
from ncclient.transport.session import SessionListener


if __name__ == '__main__':

    parser = ArgumentParser(description='Select your telemetry parameters:')

    # Input parameters
    parser.add_argument('--host', type=str,
                        default=os.environ.get('NCC_HOST','127.0.0.1'),
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
                        default=os.environ.get('NCC_PORT',830),
                        help="Specify this if you want a non-default port "
                        "(default 830)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Exceedingly verbose logging to the console")
    parser.add_argument('--delete-after', type=int,
                        help="Delete the established subscription after N seconds")
    parser.add_argument('-x', '--xpaths', type=str, nargs='+', required=True,
                        help="List of xpaths to subscribe to, one or more")
    parser.add_argument('--streamns', type=str,
                        help="Namespace for a custom stream identity, "
                        "e.g. urn:cisco:params:xml:ns:yang:cisco-xe-ietf-yang-push-ext")
    parser.add_argument('--callback', type=str,
                        help="Module that a callback is defined in")
    
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--period', type=int,
                   help="Period in centiseconds for periodic subscription")
    g.add_argument('--dampening-period', type=int,
                   help="Dampening period in centiseconds for on-change subscription")
    g.add_argument('--streamident', type=str,
                   help="Custom stream identifier (e.g. yang-notif-native)")
    
    
    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        # for l in ['ncclient.transport.session', 'ncclient.operations.rpc']:
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
                         device_params={'name':'iosxe'},
                         unknown_host_cb=unknown_host_cb)

    #
    # set up a ctrl+c handler to tear down the netconf session
    #
    def sigint_handler(signal, frame):
        m.close_session()
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    #
    # A really simple callback, just spit out a header with some key
    # details plus the XML payload pretty-printed.
    #
    def callback(notif):
        print('-->>')
        print('(Default Callback)')
        print('Event time      : %s' % notif.event_time)
        print('Subscription Id : %d' % notif.subscription_id)
        print('Type            : %d' % notif.type)
        print('Data            :')
        print(etree.tostring(notif.datastore_ele, pretty_print=True).decode('utf-8'))
        print('<<--')

    def errback(notif):
        pass

    #
    # Select the callback to use
    #
    selected_init = None
    selected_callback = callback
    selected_errback = errback
    if args.callback:
        import importlib
        module = importlib.import_module(args.callback)
        selected_init = getattr(module, 'init')
        selected_callback = getattr(module, 'callback')
        selected_errback = getattr(module, 'errback')

    #
    # If we have a callback "module" specified, call its init function
    # with the list of xpaths we are dealing with.
    #
    if selected_init:
        selected_init(args.xpaths)

    #
    # iterate over the list of xpaths and create subscriptions
    #
    subs = []
    for xpath in args.xpaths:
        s = m.establish_subscription(
            selected_callback,
            selected_errback,
            xpath=xpath,
            period=args.period,
            dampening_period=args.dampening_period,
            streamident=args.streamident,
            streamns=args.streamns)
        print('Subscription Result : %s' % s.subscription_result)
        if s.subscription_result.endswith('ok'):
            print('Subscription Id     : %d' % s.subscription_id)
            subs.append(s.subscription_id)
    if not len(subs):
        print('No active subscriptions, exiting.')
        sys.exit(1)

    #
    # simple forever loop
    #
    if args.delete_after:
        time.sleep(args.delete_after)
        for s in subs:
            r = m.delete_subscription(s)
            print('delete subscription result = %s' % r.subscription_result)
    else:
        while True:
            time.sleep(5)
