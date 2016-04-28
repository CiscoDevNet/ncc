import sys
import logging
from argparse import ArgumentParser
from ncclient import manager
from ncclient.operations.rpc import RPCError
import logging
from BeautifulSoup import BeautifulStoneSoup

def get_schema(host, port, user, passwd, schema, version):
    with manager.connect(timeout=120, host=host, port=port, username=user, password=passwd, device_params={'name':"iosxr"}) as m:
        try:
            c = m.get_schema(schema, version=version)
            print BeautifulStoneSoup(c.xml, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).find('data').getText()
        except RPCError as e:
            print >>sys.stderr, 'Failed to get schema {} || RPCError: severity={}, tag={}, message={}'.format(
                schema, e.severity, e.tag, e.message)


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
    parser.add_argument('--schema', type=str, required=True,
                        help="Get just this schema")
    parser.add_argument('--version', type=str, default=None,
                        help="Get just this schema")
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

    get_schema(
        args.host,
        args.port,
        args.username,
        args.password,
        args.schema,
        args.version)
