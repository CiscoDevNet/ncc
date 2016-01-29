#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Template
from lxml import etree
import logging


def get(m, filter=None):
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter)).data_xml
    else:
        c = m.get().data_xml
    print etree.tostring(etree.fromstring(c), pretty_print=True)
        
        
if __name__ == '__main__':

    parser = ArgumentParser(description='Provide your get parameters:')

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

    # Only one type of filter
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="XML-formatted netconf subtree filter")
    
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
    get(m, args.filter)
