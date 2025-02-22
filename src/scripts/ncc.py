#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
from __future__ import print_function
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time

from argparse import ArgumentParser
from git import Repo
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import StrictUndefined
from jinja2 import meta
from jinja2.exceptions import UndefinedError
from lxml import etree
from ncclient import manager
from ncclient.operations.rpc import RPCError

#
# Namespaces starting point for xpath queries
#
ns_dict = {
    'nc': 'urn:ietf:params:xml:ns:netconf:base:1.0'
}

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
# default bytes to display when UnicodeDecodeError exceptions are caught
#
UNICODE_ERRB = 30

#
# Repository to clone snippets from
#
REPO_URL = 'https://github.com/CiscoDevNet/ncc.git'

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


def strip_leading_trailing_ws(to_strip):
    s1 = re.sub(r"^\s*", "", to_strip)
    s2 = re.sub(r"\s*$", "", s1)
    return s2


def display_capabilities(m):
    """Display the capabilities in a useful, categorized way.
    """
    ietf_netconf_caps = []
    ietf_models = []
    openconfig_models = []
    cisco_models = []
    cisco_calvados_models = []
    mib_models = []
    other_models = []

    # local function to pull out NS & module
    def append_ns_and_module(c, module_list):
        re_model = '^([^\?]+)\?module=([^&]+)&?'
        match = re.search(re_model, c)
        if match:
            module_list.append('%s (%s)' % (match.group(2), match.group(1)))

    # pre-process capabilities, split into various categories
    ns_to_list = [
        ('urn:ietf:params:xml:ns:yang:smiv2', mib_models),
        ('urn:ietf:params:xml:ns', ietf_models),
        ('http://openconfig.net/yang', openconfig_models),
        ('http://cisco.com/ns/yang', cisco_models,),
        ('http://cisco.com/calvados', cisco_calvados_models),
        ('http://cisco.com/panini/calvados', cisco_calvados_models),
        ('http://tail-f.com/ns/mibs', mib_models),
        ('http://tail-f.com/ns', cisco_calvados_models),
        ('http://tail-f.com/test', cisco_calvados_models),
        ('http://tail-f.com/yang', cisco_calvados_models),
        ('http://www.cisco.com/calvados', cisco_calvados_models),
        ('http://www.cisco.com/ns/calvados', cisco_calvados_models),
        ('http://www.cisco.com/panini/calvados', cisco_calvados_models),
        ('http://', other_models),
    ]
    for c in m.server_capabilities:
        matched = False
        if c.startswith('urn:ietf:params:netconf'):
            ietf_netconf_caps.append(c)
            matched = True
        else:
            for ns, ns_list in ns_to_list:
                if ns in c:
                    append_ns_and_module(c, ns_list)
                    matched = True
                    break
        if matched is False:
            other_models.append(c)

    # now print them
    list_to_heading = [
        (ietf_netconf_caps, 'IETF NETCONF Capabilities:'),
        (ietf_models, 'IETF Models:'),
        (openconfig_models, 'OpenConfig Models:'),
        (cisco_models, 'Cisco Models:'),
        (cisco_calvados_models, 'Cisco XR Admin Plane Models:'),
        (mib_models, 'MIB Models:'),
        (other_models, 'Other Models:'),
    ]
    for (l, h) in list_to_heading:
        if len(l) > 0:
            print(h)
            for s in sorted(l):
                print('\t%s' % s)


def query_model_support(m, re_module):
    """Search the capabilities for one or more models that match the provided
    regex.
    """
    matches = []
    re_model = '^([^\?]+)\?module=([^&]+)&?'
    for c in m.server_capabilities:
        m = re.search(re_model, c)
        if m:
            model = m.group(2)
            match = re.search(re_module, model)
            if match:
                matches.append(model)
    return matches


def list_templates(header, source_env):
    """List out all the templates in the provided environment, parse them
    and extract variables that should be provided.
    UPDATED To present the VARS as JSON dict with enpty values
    """
    print(header)
    env = Environment()
    for tname in sorted(source_env.list_templates()):
        tfile = source_env.get_template(tname).filename
        with open(tfile, 'r') as f:
            vars = meta.find_undeclared_variables(env.parse(f.read()))
            f.close()
            print("  {}".format(tname.replace('.tmpl', '')), end=" ")
            if vars:
                print(":{", end=" ")
                print(','.join(['"%s" : ""' % v for v in sorted(vars)])),
                print("}")
            else:
                print()


def cook_xpath(xpath):
    # The basic XPath filter, in XML, looks like:
    #
    # <nc:filter type="xpath"
    #            xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0"
    #            xmlns:if="urn:ietf:params:xml:ns:yang:ietf-interfaces"
    #            select="/some/x/path/query"/>)
    #
    # We need to:
    # - identify all "ns:" occurrences
    # - create a namespace mapping that we will put in the XML outside select
    # - construct the XML
    #
    filter_template = '<nc:filter type="xpath" %s select="%s"/>'
    ns_set = {'nc'}
    re_ns = re.compile('([\w\-]+):([\w\-]+)')
    for prefix, local_name in re_ns.findall(xpath):
        if prefix not in ns_dict:
            print('Required prefix "%s" not defined' % prefix)
            sys.exit(1)
        else:
            ns_set.add(prefix)
    namespaces = ' '.join(['xmlns:%s="%s"' % (p, ns_dict[p]) for p in ns_set])
    return filter_template % (namespaces, xpath)


def do_templates(m, t_list, default_op='merge', **kwargs):
    """Execute a list of templates, using the kwargs passed in to
    complete the rendering.
    """

    for tmpl in t_list:
        try:
            data = tmpl.render(kwargs)
        except UndefinedError as e:
            print("Undefined variable %s.  Use --params to specify json dict"
                  % e.message)
            # assuming we should fail if a single template fails?
            exit(1)

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


def get_running_config(m, filter=None, xpath=None, with_defaults=None):
    """
    Get running config with a passed in filter. If both types of filter
    are passed in for some reason, the subtree filter "wins". When an
    xpath filter is passed in, it is assumed to be the fully created
    XML, and so is not passed to ncclient using the tuple syntax.
    """
    c = None
    if filter and len(filter) > 0:
        c = m.get_config(source='running', filter=('subtree', filter), with_defaults=with_defaults)
    elif xpath and len(xpath) > 0:
        c = m.get_config(source='running', filter=xpath, with_defaults=with_defaults)
    else:
        c = m.get_config(source='running', with_defaults=with_defaults)
    return c


def install_snippets(target_dir='.'):
    localdir = tempfile.mkdtemp()
    Repo.clone_from(REPO_URL, localdir)
    for entry in os.listdir(localdir):
        if entry.startswith('snippets'):
            shutil.move(localdir + '/' + entry, target_dir)
    shutil.rmtree(localdir)


def display_env_vars():
    print('export NCC_HOST=127.0.0.1')
    print('export NCC_PORT=2223')
    print('export NCC_USERNAME=vagrant')
    print('export NCC_PASSWORD=vagrant')


def get(m, filter=None, xpath=None, with_defaults=None):
    """
    Get state with a passed in filter. If both types of filter are
    passed in for some reason, the subtree filter "wins". When an
    xpath filter is passed in, it is assumed to be the fully created
    XML, and so is not passed to ncclient using the tuple syntax.
    """
    c = None
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter), with_defaults=with_defaults)
    elif xpath and len(xpath) > 0:
        c = m.get(filter=xpath, with_defaults=with_defaults)
    else:
        c = m.get(with_defaults=with_defaults)
        return
    return c


def report_unicode_decode_error(u):
    assert isinstance(u, UnicodeDecodeError)
    start = u.start - UNICODE_ERRB
    if start < 0: start = 0
    end = u.start + UNICODE_ERRB
    if end > len(u.object): end = len(u.object)
    print('UnicodeDecodeError exception:')
    print('    {}'.format(u))
    print('Surrounding data (+/- up to {} bytes):'.format(UNICODE_ERRB))
    print('    {}'.format(u.object[start:end]))

#
# new entry point for poetry
#
def main():

    #
    # quick hack to allow for global constants to be referenced in this
    # function correctly
    #
    global UNICODE_ERRB
    global RUNNING
    global CANDIDATE
    global NCC_DIR
    global LOGGING_TO_ENABLE
    global REPO_URL
    global NC_WRITABLE_RUNNING
    global NC_CANDIDATE
    global ns_dict

    parser = ArgumentParser(
        description='Select your NETCONF operation and parameters:')

    #
    # NETCONF session parameters and other values
    #
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
    parser.add_argument('--timeout', type=int, default=60,
                        help="NETCONF operation timeout in seconds "
                        "(default 60)")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Exceedingly verbose logging to the console")
    parser.add_argument('-t', '--time', action='store_true',
                        help="Display the time an operation took, excluding connection setup and display")
    parser.add_argument('--default-op', type=str, default='merge',
                        help="The NETCONF default operation to use "
                        "(default 'merge')")
    parser.add_argument('--with-defaults', type=str,
                        help="RFC 6243 with-defaults value to use")
    parser.add_argument('--device-type', type=str, default=None,
                         help="The device type to pass to ncclient "
                         "(default: None)")
    parser.add_argument('--unicode-error-bytes', type=int,
                        default=UNICODE_ERRB,
                        help="Specify number of +/- bytes to display for  "
                        "UnicodeDecodeError exceptions "
                        "(default {})".format(UNICODE_ERRB))

    #
    # Where we want to source snippets from
    #
    parser.add_argument('--snippets', type=str,
                        default=os.environ.get(
                            'NCC_SNIPPETS', "%s/snippets" % NCC_DIR),
                        help="Directory where 'snippets' can be found; "
                        "default is location of script")

    #
    # specify a list of namespaces
    #
    parser.add_argument('--ns', type=str, nargs='+',
                        help="Specify list of prefix=NS bindings or JSON "
                        "files with bindings. @filename will read a JSON file "
                        "and update the set of namespace bindings, silently "
                        "overwriting with any redefinitions.")

    #
    # Various operation parameters. These will be put into a kwargs
    # dictionary for use in template rendering.
    #
    parser.add_argument('--params', type=str,
                        help="JSON-encoded string of parameters dictionary "
                        "for templates")
    parser.add_argument('--params-file', type=str,
                        help="JSON-encoded file of parameters dictionary "
                        "for templates")
    #
    # Only one type of filter allowed.
    #
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-f', '--filter', type=str,
                   help="NETCONF subtree filter")
    g.add_argument('--named-filter', nargs='+',
                   help="List of named NETCONF subtree filters")
    g.add_argument('-x', '--xpath', type=str,
                   help="NETCONF XPath filter")

    #
    # Mutually exclusive operations.
    #
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--env', action='store_true',
                   help="Display environment variables a user can set.")
    g.add_argument('--install-snippets', action='store_true',
                   help="Use git to obtain the snippets from GitHub and copy "
                   "to the current directory")
    g.add_argument('-c', '--capabilities', action='store_true',
                   help="Display capabilities of the device.")
    g.add_argument('--is-supported', type=str,
                   help="Query the server capabilities to determine whether "
                   "the device claims to support YANG modules matching the "
                   "provided regular expression. The regex provided is not "
                   "automatically anchored to start or end. Note that the "
                   "regex supplied must be in a format valid for Python and "
                   "that it may be necessary to quote the argument.")
    g.add_argument('--list-templates', action='store_true',
                   help="List out named edit-config templates")
    g.add_argument('--list-filters', action='store_true',
                   help="List out named filters")
    g.add_argument('-g', '--get-running', action='store_true',
                   help="Get the running config")
    g.add_argument('--get-oper', action='store_true',
                   help="Get oper data")
    g.add_argument('--do-edits', type=str, nargs='+',
                   help="Execute a sequence of named templates with an "
                   "optional default operation and a single commit when "
                   "candidate config supported. If only writable-running "
                   "support, ALL operations will be attempted.")
    g.add_argument('-w', '--where', action='store_true',
                   help="Print where script is and exit")

    #
    # Finally, parse the arguments!
    #
    args = parser.parse_args()

    #
    # Display the environment variable
    #
    if args.env:
        display_env_vars()
        sys.exit(0)

    #
    # install the snippets to the current directory
    #
    if args.install_snippets:
        install_snippets()
        sys.exit(0)

    #
    # setup unicode decode error exception +/- bytes
    #
    UNICODE_ERRB = args.unicode_error_bytes

    #
    # Setup the templates for use.
    #
    named_filters = Environment(loader=FileSystemLoader(
        '%s/filters' % args.snippets),
        undefined=StrictUndefined)
    named_templates = Environment(loader=FileSystemLoader(
        '%s/editconfigs' % args.snippets),
        undefined=StrictUndefined)

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
    # Parse any ns bindings if provided. If a binding starts with "@",
    # we assume it is a filename with a JSON representation of a
    # dict. The contents of the dict will be merged over the current
    # ns_dict, and **silently** overwrite existing bindings.
    #
    if args.ns:
        for ns in args.ns:
            if ns.startswith('@'):
                update_dict = json.loads(open(ns[1:], 'r').read())
                ns_dict.update(update_dict)
            else:
                prefix, namespace = ns.split('=')
                if not prefix or not namespace:
                    next
                else:
                    if (prefix in ns_dict) and (ns_dict[prefix] != namespace):
                        print('Clashing namespace defined:')
                        print('  xmlns:%s="%s" (existing)'
                              % (prefix, ns_dict[prefix]))
                        print('  xmlns:%s="%s" (redfinition)'
                              % (prefix, namespace))
                        sys.exit(1)
                    else:
                        ns_dict[prefix] = namespace
    if args.xpath:
        args.xpath = cook_xpath(args.xpath)

    #
    # This populates the filter if it's a canned filter.
    #
    if args.named_filter is not None:
        try:
            args.filter = []
            for f in args.named_filter:
                args.filter.append(named_filters.get_template(
                    '%s.tmpl' % f).render(**kwargs))
        except UndefinedError as e:
            print("Undefined variable %s.  Use --params to specify json dict" % e.message)
            exit(1)

    #
    # Could use this extra param instead of the last four arguments
    # specified below:
    #
    # device_params={'name': 'iosxr'}
    #
    def unknown_host_cb(host, fingerprint):
        return True

    device_params = {}
    if args.device_type is not None:
        device_params = {'name': args.device_type}

    m = manager.connect(host=args.host,
                        port=args.port,
                        timeout=args.timeout,
                        username=args.username,
                        password=args.password,
                        allow_agent=False,
                        look_for_keys=False,
                        hostkey_verify=False,
                        device_params=device_params,
                        unknown_host_cb=unknown_host_cb)

    #
    # Extract the key capabilities that determine how we interact with
    # the device. This script will prefer using candidate config.
    #
    if NC_WRITABLE_RUNNING in m.server_capabilities:
        RUNNING = True
    if NC_CANDIDATE in m.server_capabilities:
        CANDIDATE = True

    #
    # Main operations
    #
    # TODO: get_running/get_oper are a bit samey, could be done better
    #
    results = []
    start_time = 0.0
    end_time = 0.0
    if args.get_running:
        try:
            start_time = time.time()
            if isinstance(args.filter, list):
                for f in args.filter:
                    results.append(get_running_config(
                        m,
                        filter=f,
                        xpath=None,
                        with_defaults=args.with_defaults))
            else:
                results.append(get_running_config(
                    m,
                    xpath=args.xpath,
                    filter=args.filter,
                    with_defaults=args.with_defaults))
            end_time = time.time()
        except UnicodeDecodeError as u:
            report_unicode_decode_error(u)
            sys.exit(1)
    elif args.get_oper:
        try:
            start_time = time.time()
            if isinstance(args.filter, list):
                for f in args.filter:
                    results.append(get(
                        m,
                        filter=f,
                        xpath=None,
                        with_defaults=args.with_defaults))
            else:
                results.append(get(
                    m,
                    filter=args.filter,
                    xpath=args.xpath,
                    with_defaults=args.with_defaults))
            end_time = time.time()
        except UnicodeDecodeError as u:
            report_unicode_decode_error(u)
            sys.exit(1)
    elif args.do_edits:
        try:
            start_time = time.time()
            do_templates(
                m,
                [named_templates.get_template('%s.tmpl' % t)
                  for t in args.do_edits],
                default_op=args.default_op,
                **kwargs)
            end_time = time.time()
        except RPCError as e:
            end_time = time.time()
            print("RPC Error")
            print("---------")
            print("severity: %s" % e.severity)
            print("     tag: %s" % e.tag)
            if e.path and len(e.path) > 0:
                print("    path: %s" % strip_leading_trailing_ws(e.path))
            print(" message: %s" % e.message)
            print("    type: %s" % e.type)
    elif args.capabilities:
        display_capabilities(m)
    elif args.is_supported:
        models = query_model_support(m, args.is_supported)
        for model in models:
            print(model)

    #
    # display any get results
    #
    if len(results) > 0:
        for c in results:
            if c:
                print(etree.tostring(c.data, pretty_print=True).decode('UTF-8'))

    #
    # dsplay operation time if requested
    #
    if args.time:
        print("\nTotal Operation Time = {}".format(end_time-start_time))

    #
    # Orderly teardown of the netconf session.
    # Ignore Value error sometimes returned in cleanup
    try:
        m.close_session()
    except ValueError:
        pass
