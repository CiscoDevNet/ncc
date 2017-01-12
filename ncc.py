#!/usr/bin/env python
import sys
import os
from argparse import ArgumentParser
from ncclient import manager
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import Template
from lxml import etree
import logging

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
# By default, don't support writeable-running or candidate configs
#
RUNNING = False
CANDIDATE = False


#
# Get where the script is; we will use this to find snippets for
# templates and filters unless overriden.
#
NCC_DIR, _ = os.path.split(os.path.realpath(__file__))
#named_filters = Environment(loader=FileSystemLoader('%s/snippets/filters' % NCC_DIR))
#named_templates = Environment(loader=FileSystemLoader('%s/snippets/editconfigs' % NCC_DIR))


def do_template(m, t, default_op='merge', **kwargs):
    '''Execute a template passed in, using the kwargs passed in to
    complete the rendering.

    '''
    data = t.render(kwargs)

    if CANDIDATE:
        m.edit_config(data,
                      format='xml',
                      target='candidate',
                      default_operation=default_op)
        m.commit()
    elif RUNNING:
        m.edit_config(data,
                      format='xml',
                      target='running',
                      default_operation=default_op)


def do_templates(m, t_list, named_templates, default_op='merge', **kwargs):
    """Execute a list of templates, using the kwargs passed in to
    complete the rendering.
    """
    for t in t_list:
        tmpl = named_templates.get_template('%s.tmpl' % t)
        data = tmpl.render(kwargs)
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
    print "filter", filter, "xpath", xpath
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
    # Various operation parameters. Put int a kwargs structure for use
    # in template rendering.
    #
    parser.add_argument('-i', '--intf-name', type=str,
                        help="Specify an interface for general use in templates (no format validation)")
    parser.add_argument('-s', '--subintf-index', type=int, 
                        help="Specify sub-interface index for general use in openconfig templates (no format validation)")
    parser.add_argument('-n', '--neighbor-addr', type=str, 
                        help="Specify a neighbor address (no format validation)")
    parser.add_argument('-r', '--remote-as', type=str, 
                        help="Specify the neighbor's remote AS (no format validation)")
    parser.add_argument('--description', type=str, 
                        help="BGP neighbor description string (quote it!)")
    parser.add_argument('--vlan', type=str,
                        help="VLAN Number")
    parser.add_argument('--rc-bridge-ip', type=str,
                        help="Bridge IP address for enabling RESTCONF static route")
    parser.add_argument('--rc-http-port', type=int, default=115,
                        help="HTTP port for RESTCONF (default 115)")
    parser.add_argument('--rc-https-port', type=int, default=116,
                        help="HTTPS port for RESTCONF (default 116)")

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
    # Basic, mutually exclusive, operations.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--list-templates', action='store_true',
                   help="List out named templates embedded in script")
    g.add_argument('--list-filters', action='store_true',
                   help="List out named filters embedded in script")
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--get-oper', action='store_true',
                   help="Get oper data")
    g.add_argument('--do-edit', type=str,
                   help="Execute a named template")
    g.add_argument('--do-edits', type=str, nargs='+',
                   help="Execute a sequence of named templates with an optional default operation and a single commit")

    #
    # Finally, parse the arguments!
    #
    args = parser.parse_args()

    #
    # setup the templates/filter directory
    #
    named_filters = Environment(loader=FileSystemLoader('%s/%s/filters' % (NCC_DIR, args.snippetdir)))
    named_templates = Environment(loader=FileSystemLoader('%s/%s/editconfigs' % (NCC_DIR, args.snippetdir)))


    #
    # temp insertion
    #
    if args.where:
        print(dir(named_filters))
        print(named_filters.get_template('intf-brief-all.tmpl').render())
        sys.exit(0)
        
    #
    # Do the named template/filter listing first, then exit.
    #
    if args.list_templates:
        print("Embedded named templates:")
        for k in sorted(iter(named_templates.list_templates())):
            print("  {}".format(k.replace('.tmpl', '')))
        sys.exit(0)
    elif args.list_filters:
        print("Embedded named filters:")
        for k in sorted(iter(named_filters.list_templates())):
            print("  {}".format(k.replace('.tmpl', '')))
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
    kwargs = {}
    if args.intf_name:
        kwargs['INTF_NAME'] = args.intf_name
    if args.subintf_index:
        kwargs['SUBINTF_INDEX'] = args.subintf_index
    if args.neighbor_addr:
        kwargs['NEIGHBOR_ADDR'] = args.neighbor_addr
    if args.remote_as:
        kwargs['REMOTE_AS'] = args.remote_as
    if args.description:
        kwargs['DESCRIPTION'] = args.description
    if args.vlan:
        kwargs['VLAN'] = args.vlan
    if args.rc_bridge_ip:
        kwargs['BRIDGE_IP'] = args.rc_bridge_ip
    if args.rc_http_port:
        kwargs['RC_HTTP_PORT'] = args.rc_http_port
    if args.rc_https_port:
        kwargs['RC_HTTPS_PORT'] = args.rc_https_port

    #
    # This populates the filter if it's a canned filter.
    #
    if args.named_filter:
        args.filter = named_filters.get_template('%s.tmpl' % args.named_filter).render(**kwargs)

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
    if 'urn:ietf:params:netconf:capability:writable-running:1.0' in m.server_capabilities:
        RUNNING = True
    if 'urn:ietf:params:netconf:capability:candidate:1.0' in m.server_capabilities:
        CANDIDATE = True
    
    if args.get_running:
        if args.xpath:
            get_running_config(m, xpath=args.xpath)
        else:
            get_running_config(m, filter=args.filter)
    elif args.get_oper:
        if args.xpath:
            get(m, xpath=args.xpath)
        else:
            get(m, filter=args.filter)
    elif args.do_edit:
        do_template(m, named_templates.get_template('%s.tmpl' % args.do_edit), **kwargs)
    elif args.do_edits:
        do_templates(m, args.do_edits, named_templates, default_op=args.default_op, **kwargs)
