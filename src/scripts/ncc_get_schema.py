#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
from __future__ import print_function

import logging
import os
import os.path
import pyang
import pyang.repository
import pyang.context
import sys

from argparse import ArgumentParser
from ncclient import manager
from ncclient.operations.rpc import RPCError


#
# local logger
#
logger = logging.getLogger(__name__)


#
# default bytes to display when UnicodeDecodeError exceptions are caught
#
UNICODE_ERRB = 30


def report_unicode_decode_error(u):
    assert isinstance(u, UnicodeDecodeError)
    start = u.start - UNICODE_ERRB
    if start < 0: start = 0
    end = u.start + UNICODE_ERRB
    if end > len(u.object): end = len(u.object)
    print('Unicode Encode/Decode Error exception:', file=sys.stderr)
    print('    {}'.format(u), file=sys.stderr)
    print('Surrounding data (+/- up to {} bytes):'.format(UNICODE_ERRB), file=sys.stderr)
    print('    {}'.format(u.object[start:end]), file=sys.stderr)


def report_unicode_encode_error(u):
    assert isinstance(u, UnicodeEncodeError)
    start = u.start - UNICODE_ERRB
    if start < 0: start = 0
    end = u.start + UNICODE_ERRB
    if end > len(u.object): end = len(u.object)
    print('Unicode Encode/Decode Error exception:', file=sys.stderr)
    print('    {}'.format(u), file=sys.stderr)
    print('Surrounding data (+/- up to {} bytes):'.format(UNICODE_ERRB), file=sys.stderr)
    print('    {}'.format(u.object[start:end].encode('UTF-8')), file=sys.stderr)


def get_schema(m, schema, version):
    '''
    Simple schema download to stdout.
    '''
    try:
        logger.debug('Retrieving %s', schema)
        c = m.get_schema(schema, version=version)
        print(c.data)
    except RPCError as e:
        print(
            'Failed to get schema {} || RPCError: severity={}, tag={}, message={}'.format(
                schema, e.severity, e.tag, e.message),
            file=sys.stderr)


def get_schema_with_depends(mgr, schema, version, dest_dir="."):
    '''
    Get a names schema, with optional version, and download it. If the
    downloaded revision doesn't exist in the destination directory,
    recursively resolve all dependencies the module has. If any of
    those dependencies already exist, they will not be downloaded.

    Any downloaded schema are saved to files with version-extended file
    names.

    If the module give to this routine is a sub-module, the
    'belongs-to' statement is not resolved.
    '''
    to_resolve = set([(schema, version)])
    try:
        repo = pyang.repository.FileRepository(dest_dir)
        while to_resolve:
            s, v = to_resolve.pop()
            c = mgr.get_schema(s, version=v)
            ctx = pyang.context.Context(repo)
            ctx.add_module(s, c.data)
            for ((m, r), module) in ctx.modules.items():
                if m == s:
                    dest_file = '%s/%s@%s.yang' % (dest_dir, m, r)
                    if not os.path.isfile(dest_file):
                        for sub in module.substmts:
                            if (sub.keyword == 'import') or (sub.keyword == 'include'):
                                to_resolve.add((sub.arg, None))
                            with open(dest_file, 'wb') as f:
                                f.write(c.data.encode('UTF-8'))
    except RPCError as e:
        print(
            'Failed to get schema {} || RPCError: severity={}, tag={}, message={}'.format(
                schema, e.severity, e.tag, e.message),
            file=sys.stderr)


def main():

    parser = ArgumentParser(description='Select schema download options:')
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
    parser.add_argument('--get-depends', action='store_true',
                        help="Also get dependencies for named schema; "
                        "use of this option will trigger writing "
                        "downloaded schema to files")
    parser.add_argument('-o', '--output-dir', type=str, default=os.getcwd(),
                        help="Where to write schema files, and if models or "
                        " their dependencies already exist in this location, "
                        "their download will be skipped")
    parser.add_argument('--version', type=str, default=None,
                        help="Schema to retrieve")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do some verbose logging")
    args = parser.parse_args()

    #
    # if you enable verbose logging, it is INCREDIBLY verbose...you
    # have been warned!! so verbose with .ssh that I have currently
    # commented that out ;-)
    #
    if args.verbose:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        for l in ['ncclient.transport.session',
                  # 'ncclient.transport.ssh',
                  'ncclient.operations.rpc']:
            ll = logging.getLogger(l)
            ll.addHandler(handler)
            ll.setLevel(logging.DEBUG)

    #
    # connect to the device and either get schema with dependencies,
    # or do a simple get schema.
    #
    with manager.connect(
            timeout=600,
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            allow_agent=False,
            look_for_keys=False,
            hostkey_verify=False) as m:
        try:
            if args.get_depends:
                get_schema_with_depends(m, args.schema, args.version, dest_dir=args.output_dir)
            else:
                get_schema(m, args.schema, args.version)
        except UnicodeDecodeError as u:
            report_unicode_decode_error(u)
        except UnicodeEncodeError as u:
            report_unicode_encode_error(u)
