#!/usr/bin/env python
import sys
import os
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Environment
from jinja2.exceptions import UndefinedError
from jinja2 import meta
from jinja2 import FileSystemLoader
from jinja2 import StrictUndefined
from jinja2 import Template
from lxml import etree
import logging
import json


#
# Add things people want logged here. Just various netconf things for
# now. SSH disabled as it is just too much right now.
#
LOGGING_TO_ENABLE = [
    'ncclient.transport.ssh',
    'ncclient.transport.session',
    'ncclient.operations.rpc'
]


#
# Capability constants
#
NC_WRITABLE_RUNNING = 'urn:ietf:params:netconf:capability:writable-running:1.0'
NC_CANDIDATE = 'urn:ietf:params:netconf:capability:candidate:1.0'


#
# By default, don't support writeable-running or candidate configs
#
RUNNING = False
CANDIDATE = False


#
# Get where the script is; we will use this to find snippets for
# templates and filters unless overriden.
#
NCC_DIR, _ = os.path.split(os.path.realpath(__file__))



def list_templates(header, source_env):
    """List out all the templates in the provided environment, parse them
    and extract variables that should be provided.
    """
    print(header)
    env = Environment()
    for tname in sorted(source_env.list_templates()):
        tfile = source_env.get_template(tname).filename
        with open(tfile, 'r') as f:
            vars = meta.find_undeclared_variables(env.parse(f.read()))
            f.close()
            print("  {}".format(tname.replace('.tmpl', '')))
            for v in sorted(vars):
                print('    %s' % v)


def do_templates(m, t_list, default_op='merge', **kwargs):
    """Execute a list of templates, using the kwargs passed in to
    complete the rendering.
    """
    for tmpl in t_list:

        data = tmpl.render(kwargs)
        print "data", data
        if CANDIDATE:
            m.edit_config(data,
                          format='xml',
                          target='candidate',
                          default_operation=default_op)
        elif RUNNING:
            m.edit_config(data,
                          format='xml',
                          target='running',
                          default_operation=default_op)
    if CANDIDATE:
        m.commit()


def get_running_config(m, filter=None, xpath=None):
    """Get running config with a passed in filter. If both types of
    filter are passed in for some reason, the subtree filter "wins".
    """
    import time
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter))
    elif xpath and len(xpath)>0:
        c = m.get_config(source='running', filter=('xpath', xpath))
    else:
        c = m.get_config(source='running')
    print(etree.tostring(c.data, pretty_print=True))
        
        
def get(m, filter=None, xpath=None):
    """Get state with a passed in filter. If both types of filter are
    passed in for some reason, the subtree filter "wins".
    """
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter))
    elif xpath and len(xpath)>0:
        c = m.get(filter=('xpath', xpath))
    else:
        print("Need a filter for oper get!")
        return
    print(etree.tostring(c.data, pretty_print=True))
        
        
if __name__ == '__main__':

    parser = ArgumentParser(description='Select your NETCONF operation and parameters:')

    #
    # NETCONF session parameters
    #
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help="The IP address for the device to connect to (default localhost)")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Username to use for SSH authentication (default 'cisco')")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Password to use for SSH authentication (default 'cisco')")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port (default 830)")
    parser.add_argument('--timeout', type=int, default=60,
                        help="NETCONF operation timeout in seconds (default 60)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Exceedingly verbose logging to the console")
    parser.add_argument('--default-op', type=str, default='merge',
                        help="The NETCONF default operation to use (default 'merge')")

    parser.add_argument('-w', '--where', action='store_true',
                        help="Print where script is and exit")
    parser.add_argument('--snippetdir', type=str, default='snippets-xe',
                        help="parent snippet directory")


    #
    # Where we want to source snippets from
    #
    parser.add_argument('--snippets', type=str, default="snippets-xe",
                        help="Directory where 'snippets' can be found; default is location of script")

    #
    # Various operation parameters. These will be put into a kwargs
    # dictionary for use in template rendering.
    #
    parser.add_argument('--params', type=str,
                        help="JSON-encoded string of parameters dictionaryfor templates")
    parser.add_argument('--params-file', type=str,
                        help="JSON-encoded file of parameters dictionary for templates")
    #
    # Only one type of filter allowed.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="NETCONF subtree filter")
    g.add_argument('--named-filter', type=str,
                   help="Named NETCONF subtree filter")
    g.add_argument('-x', '--xpath', type=str,
                   help="NETCONF XPath filter")

    #
    # Mutually exclusive operations.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--list-templates', action='store_true',
                   help="List out named edit-config templates")
    g.add_argument('--list-filters', action='store_true',
                   help="List out named filters")
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--get-oper', action='store_true',
                   help="Get oper data")
    g.add_argument('--do-edits', type=str, nargs='+',
                   help="Execute a sequence of named templates with an optional default operation and a single commit")

    #
    # Finally, parse the arguments!
    #
    args = parser.parse_args()
        

    #

    #
    named_filters = Environment(loader=FileSystemLoader(
        '%s/%s/filters' % (NCC_DIR,args.snippets)),
        undefined=StrictUndefined)
    named_templates = Environment(loader=FileSystemLoader(
        '%s/%s/editconfigs' % (NCC_DIR, args.snippets)))

    #
    # Do the named template/filter listing first, then exit.
    #
    if args.list_templates:
        list_templates("Edit-config templates:", named_templates)
        sys.exit(0)
    elif args.list_filters:
        list_templates("Named filters:", named_filters)
        sys.exit(0)

    #
    # If the user specified verbose logging, set it up.
    #
    if args.verbose:
        handler = logging.StreamHandler()
        for l in LOGGING_TO_ENABLE:
            logger = logging.getLogger(l)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

    #
    # set up various keyword arguments that have specific arguments
    #

    kwargs = None
    if args.params:
        kwargs = json.loads(args.params)
    elif args.params_file:
        with open(args.params_file) as f:
            kwargs = json.loads(f.read())
            f.close()
    else:
        kwargs = {}

    #
    # This populates the filter if it's a canned filter.
    #
    if args.named_filter:
        try:
            args.filter = named_filters.get_template(
                '%s.tmpl' % args.named_filter).render(**kwargs)
        except UndefinedError as e:
            print "Undefined variable %s" % e.message
            exit(1)

    #
    # Could use this extra param instead of the last four arguments
    # specified below:
    #
    # device_params={'name': 'iosxr'}
    #
    def unknown_host_cb(host, fingerprint):
        return True
    m =  manager.connect(host=args.host,
                         port=args.port,
                         timeout=args.timeout,
                         username=args.username,
                         password=args.password,
                         allow_agent=False,
                         look_for_keys=False,
                         hostkey_verify=False,
                         unknown_host_cb=unknown_host_cb)

    #
    # Extract the key capabilities that determine how we interact with
    # the device. This script will prefer using candidate config.
    #
    if NC_WRITABLE_RUNNING in m.server_capabilities:
        RUNNING = True
    if NC_CANDIDATE in m.server_capabilities:
        CANDIDATE = True


    if args.get_running:
        # if args.xpath:
        #     get_running_config(m, xpath=args.xpath)
        # else:
        #     get_running_config(m, filter=args.filter)
        get_running_config(m, xpath=args.xpath, filter=args.filter)

    elif args.get_oper:
        #if args.xpath:
        #    get(m, xpath=args.xpath)
        #else:
        #    get(m, filter=args.filter)
        get(m, filter=args.filter, xpath=args.xpath)
    elif args.do_edits:
        do_templates( m,
                      [named_templates.get_template('%s.tmpl' % t) for t in args.do_edits],
                      default_op=args.default_op,
                      **kwargs)


    #
    # Orderly teardown of the netconf session.
    #
    m.close_session()
