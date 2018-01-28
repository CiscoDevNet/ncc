#!/usr/bin/env python
import sys
import signal
from argparse import ArgumentParser
from ncclient import manager
from lxml import etree
import logging
import time
import datetime
from ncclient.transport.session import SessionListener

#
# some useful constants
#
CISCO_CDP_OPER_NS = 'http://cisco.com/ns/yang/Cisco-IOS-XE-cdp-oper'
CISCO_PROCESS_CPU_OPER = 'http://cisco.com/ns/yang/Cisco-IOS-XE-process-cpu-oper'

#
# globals
#
events_received = 0


def get(m, filter=None, xpath=None):
    if filter and len(filter) > 0:
        return m.get(filter=('subtree', filter))
    elif xpath and len(xpath)>0:
        return m.get(filter=('xpath', xpath))
    else:
        print ("Need a filter for oper get!")
        return None


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
    parser.add_argument('--delete-after', type=int,
                        help="Delete the established subscription after N seconds")
    parser.add_argument('--xpaths', type=str, nargs='+',
                        help="List of xpaths to subscribe to, one or more")

    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--period', type=int,
                   help="Period in centiseconds for periodic subscription")
    g.add_argument('--dampening-period', type=int,
                   help="Dampening period in centiseconds for on-change subscription")

    args = parser.parse_args()

    if args.verbose:
        handler = logging.StreamHandler()
        # for l in ['ncclient.transport.ssh', 'ncclient.transport.session', 'ncclient.operations.rpc']:
        for l in ['ncclient.transport.session', 'ncclient.operations.rpc']:
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
    # set up a ctrl+c handler to tear down the netconf session
    #
    def sigint_handler(signal, frame):
        m.close_session()
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    #
    # a pair of really simple callbacks...
    #
    def callback(notif):
        print('-->>')
        # print('Num Events Rxd  : %d' % events_received)
        print('Event time      : %s' % notif.event_time)
        print('Subscription Id : %d' % notif.subscription_id)
        print('Type            : %d' % notif.type)
        print('Data            :')
        print(etree.tostring(notif.datastore_ele, pretty_print=True))
        print('<<--')

    def errback(notif):
        pass
    
    #
    # iterate over the list of xpaths and create subscriptions
    #
    subs = []
    for xpath in args.xpaths:
        s = m.establish_subscription(
            callback,
            errback,
            xpath=xpath,
            period=args.period,
            dampening_period=args.dampening_period)
        print('Subscription Result : %s' % s.subscription_result)
        if s.subscription_result.endswith('ok'):
            print('Subscription Id     : %d' % s.subscription_id)
            subs.append(s.subscription_id)

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
