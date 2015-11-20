#!/usr/bin/env python
import sys
import time
import logging
from argparse import ArgumentParser
from ncclient import manager
from ncclient.operations.rpc import RPCError
import re
from BeautifulSoup import BeautifulStoneSoup

def get_all_schema(host, port, user, passwd, output_dir, start_after=None):
    getting_yet = True
    if start_after:
        getting_yet = False
    m = manager.connect(host=host, port=port, timeout=300, username=user, password=passwd, device_params={'name':"iosxr"})
    for cap in sorted(m.server_capabilities):
        r = re.search('module=([^&]*)&', cap)
        if r is not None:
            schema = r.group(1)
            if getting_yet==False:
                print 'Skipping {}'.format(schema)
                if schema==start_after:
                    getting_yet = True
                continue
            print 'Getting schema for ' + schema + '...'
            try:
                c = m.get_schema(schema)
                with open(output_dir+'/'+r.group(1)+'.yang', 'w') as yang:
                    print >>yang, BeautifulStoneSoup(c.xml, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).find('data').getText()
                    yang.close()
            except RPCError as e:
                print >>sys.stderr, 'Failed to get schema {} || RPCError: severity={}, tag={}, message={}'.format(
                    schema, e.severity, e.tag, e.message)
            # except e:
            #     print >>sys.stderr, 'Failed to get schema {}, unexpected exception!'.format(schema)
    print 'Completed iterating over schema!'
        

if __name__ == '__main__':

    parser = ArgumentParser(description='Select your simple OC-BGP operation:')
    parser.add_argument('-a', '--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")
    parser.add_argument('-o', '--output-dir', type=str, required=False,
                        help="Where to write schema files")
    parser.add_argument('--start-after', type=str, required=False,
                        help="Don't get schemas until after this one")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do some verbose logging")
    args = parser.parse_args()

    #
    # if you enable verbose logging, it is INCREDIBLY verbose...you
    # have been warned!!
    #
    if args.verbose:
        handler = logging.StreamHandler()
        for l in ['ncclient.transport.ssh', 'ncclient.transport.ssession', 'ncclient.operations.rpc']:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    if not args.output_dir:
        # default the output to got to cwd
        args.output_dir = '.'
        
    get_all_schema(
        args.host,
        args.port,
        args.username,
        args.password,
        args.output_dir,
        args.start_after)
