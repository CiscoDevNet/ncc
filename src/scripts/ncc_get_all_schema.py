#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
from __future__ import print_function
import logging
import re
from os import listdir
from os.path import isfile, join, basename
from argparse import ArgumentParser
from ncclient import manager
from ncclient.operations.rpc import RPCError
import pyang
import pyang.repository
import pyang.context


#
# local logger
#
logger = logging.getLogger(__name__)


#
# The get filter we need to retrieve the schemas a device claims to have
#
schemas_filter = '''<netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
 <schemas>
  <schema>
   <identifier/>
  </schema>
 </schemas>
</netconf-state>'''


def get(m, filter=None):
    logger.debug('Getting %s', str(filter))
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter)).data
    else:
        c = m.get().data
    return c


def get_schema(m, schema_list, output_dir, start_after=None):
    failed_download = []
    getting_yet = True
    if start_after:
        getting_yet = False
    for s in schema_list:
        if getting_yet is False:
            if s == start_after:
                getting_yet = True
            else:
                continue
        try:
            logger.debug('Retrieving %s', s)
            c = m.get_schema(s)
            with open(output_dir + '/' + s + '.yang', 'wb') as yang:
                yang.write(c.data.encode('UTF-8'))
        except RPCError as e:
            logger.debug('Failed to get %s', s)
            failed_download.append(s)
    return failed_download


def main():

    parser = ArgumentParser(description='Provide device and output parameters:')
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
    parser.add_argument('-t', '--timeout', type=int, required=False, default=30,
                        help="Where to write schema files")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Do some verbose logging")

    g = parser.add_mutually_exclusive_group()
    g.add_argument('--start-after', type=str, required=False,
                   help="Don't get schemas until after this one")
    g.add_argument('--skip-download', action='store_true', default=False,
                   help="Skip downloading schema and just consider those downloaded already")

    args = parser.parse_args()

    #
    # if you enable verbose logging, it is INCREDIBLY verbose...you
    # have been warned!!
    #
    if args.verbose:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    if not args.output_dir:
        # default the output to got to cwd
        args.output_dir = '.'

    def unknown_host_cb(host, fingerprint):
        return True
    def get_manager():
        logger.debug('Connecting to netconf server')
        return manager.connect(host=args.host,
                               port=args.port,
                               username=args.username,
                               password=args.password,
                               timeout=args.timeout,
                               allow_agent=False,
                               look_for_keys=False,
                               hostkey_verify=False,
                               unknown_host_cb=unknown_host_cb)
    mgr = get_manager()

    #
    # retrieve the schemas datatree and extract all the schema
    # identifiers
    #
    schema_tree = get(mgr, schemas_filter)
    schema_list = [
        n.text
        for n in schema_tree.xpath('//*[local-name()="identifier"]')
    ]

    #
    # check the schema list against server capabilities
    #
    not_in_schemas = set()
    for c in mgr.server_capabilities:
        model = re.search('module=([^&]*)', c)
        if model is not None:
            m = model.group(1)
            if m not in schema_list:
                not_in_schemas.add(m)
            deviations = re.search('deviations=([^&<]*)', c)
            if deviations is not None:
                d = deviations.group(1)
                for dfn in d.split(','):
                    if dfn not in schema_list:
                        logger.debug('Deviation %s not in schema list', dfn)
                        not_in_schemas.add(dfn)
    if len(not_in_schemas) > 0:
        print('The following models are advertised in capabilities but are not in schemas tree:')
        for m in sorted(not_in_schemas):
            print('    {}'.format(m))

    #
    # this dict is for keeping track of the schemas that failed to
    # download
    #
    failed_download = set()

    #
    # Now download all the schema, which also returns a list of any
    # that failed to be downloaded. If we downloaded, list the failed
    # downloads (if any).
    #
    if not args.skip_download:
        failed = get_schema(mgr, schema_list, args.output_dir, args.start_after)
        for f in failed:
            failed_download.add(str(f))

    #
    # end of main download phase, so close the session for now
    #
    mgr.close_session()

    #
    # Now let's check all the schema that we downloaded (from this run
    # and any other) and parse them with pyang to extract any imports
    # or includes and verify that they were on the advertised schema
    # list and didn't fail download.
    #
    # TODO: cater for explicitly revisioned imports & includes
    #
    imports_and_includes = set()
    repos = pyang.repository.FileRepository(args.output_dir, use_env=False)
    ctx = pyang.context.Context(repos)
    yangfiles = [f for f in listdir(args.output_dir) if isfile(join(args.output_dir, f))]
    for fname in sorted(yangfiles):
        logger.debug('Parsing %s', fname)
        fd = open(args.output_dir + '/' + fname, 'rb')
        text = fd.read().decode('UTF-8')
        ctx.add_module(fname, text)
        this_module = basename(fname).split(".")[0]
        for ((m, r), module) in ctx.modules.items():
            if m == this_module:
                for s in module.substmts:
                    if (s.keyword == 'import') or (s.keyword == 'include'):
                        imports_and_includes.add(s.arg)

    #
    # Verify that all imports and includes appeared in the advertised
    # schema
    #
    not_advertised = [str(i) for i in imports_and_includes if i not in schema_list]
    if len(not_advertised) > 0:

        #
        # list the not-advertised schemas
        #
        print('The following schema are imported or included, but not listed in schemas tree:')
        for m in sorted(not_advertised, key=str.lower):
            print('    {}'.format(m))

        #
        # try to download the not-advertised schemas
        #
        mgr = get_manager()
        for m in not_advertised:
            logger.debug('Trying to get module %s, which is included or import, bit not advertised', m)
            try:
                c = mgr.get_schema(m)
                with open(args.output_dir + '/' + m + '.yang', 'wb') as yang:
                    yang.write(c.data.encode('UTF-8'))
            except RPCError as e:
                failed_download.add(str(m))
        mgr.close_session()

    #
    # List out the schema that are imported or included and NOT
    # downloaded successfully.
    #
    if len(failed_download) > 0:
        print('The following schema are imported, included or advertised, but not downloadable:')
        for m in sorted(failed_download, key=str.lower):
            print('    {}'.format(m))
