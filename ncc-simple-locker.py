#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
import sys
from argparse import ArgumentParser
from functools import partial
from ncclient import manager
from lxml import etree
import logging
import time
import os


if __name__ == '__main__':

    parser = ArgumentParser(description='Select your simple poller parameters:')

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

    #
    # alternate operations
    #
    parser.add_argument('--unlock', action='store_true',
                        help="Instead of locking, unlock the target datastore")
    
    # other options
    parser.add_argument('--target', type=str, default='running',
                        help="Datastore to lock")
    parser.add_argument('--time', type=int, default=10,
                        help="Time to lock for")
    parser.add_argument('--context', action='store_true', default=False,
                        help="Use context-style locking")

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
    # for testing, just try and unlock the target
    #
    if args.unlock:
        m.unlock(target=args.target)
        print('Unlocked {}'.format(args.target))
        m.close_session()
        sys.exit(0)
    
    #
    # lock and unlock
    #
    if not args.context:
        m.lock(target=args.target)
        print('Locked {}'.format(args.target))
        print('Sleeping with lock for {} seconds...'.format(args.time))
        time.sleep(args.time)
        m.unlock(target=args.target)
        print('Unlocked {}'.format(args.target))
    else:
        with m.locked(args.target):
            print('Locked {}'.format(args.target))
            time.sleep(args.time)
        print('Unlocked {}'.format(args.target))
        
    #
    # graceful shutdown
    #
    m.close_session()
