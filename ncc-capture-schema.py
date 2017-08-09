#!/usr/bin/env python
from __future__ import print_function
from BeautifulSoup import BeautifulSoup
from argparse import ArgumentParser
from lxml import etree
from ncclient import manager
from ncclient.operations.rpc import RPCError
from netmiko import ConnectHandler
from os import listdir, makedirs
from os.path import isfile, join, basename, exists, getsize
import logging
import pyang
import re
import repoutil
import string
import sys
import time
import json
from git.exc import GitCommandError

#
# Check models script
#
check_models = '''
#!/bin/sh
#
# Simple run of pyang with the "--lint" flag over all yang files in
# this directory, ignoring some warnings. Prior to pushing to git, the
# validation was run with pyang 1.5. This script should be run with
# the working doirectory set to a directory containing the yang files
# to run "pyang --lint" over.
#
# The modules as uploaded exhibit a number of RFC 6087 amd RFC 6020
# errors and warnings that are judged to be cosmetic at this time and
# which do not impact the ability of a client to interact with a
# device supporting the module. The exact content ignored may be
# identified by reviewing the "grep -v" commands below.
#
EGREP=`command -v egrep`
GREP=`command -v grep`
PYANG=`command -v pyang`
CHECK_BC=""
PYANG_FLAGS=""

#
# simple function to check for existence of a binary on the current
# path
#
checkExists() {
    bin=`command -v $1`
    if [ -z "$bin" ]
    then
	echo this script requires $1 to be on your path
	exit 1
    fi
}

#
# check we have the utilties we need
#
checkExists pyang
checkExists egrep
checkExists grep

#
# brief help for the options we support
#
show_help () {
    echo Options for check-models.sh:
    printf "\n"
    printf "  -h       Show this help\n"
    printf "  -b <ver> Check backwards compatibility\n"
    printf "\n"
}

OPTIND=1
while getopts "hb:" opt; do
    case "$opt" in
    h|\?)
        show_help
	exit 0
	;;
    b)  CHECK_BC="$OPTARG"
	    ;;
    esac
done

#
# Run pyang over all the yang modules, ignoring certain errors and
# warnings.
#
echo Checking all models with "--lint" flag
for m in *.yang
do
    pyang $PYANG_FLAGS --lint $m 2>&1 | \\
	grep -v "warning: RFC 6087" | \\
	grep -v "error: RFC 6087: 4.2" | \\
	grep -v "error: RFC 6087: 4.7" | \\
	grep -v "error: RFC 6087: 4.11,4.12" | \\
	grep -v "error: RFC 6087: 4.12" | \\
	grep -v "not in canonical order" | \\
	grep -v "warning: locally scoped grouping" | \\
	egrep -v "warning: imported module\s[a-zA-Z0-9\-]+\snot used"
done

#
# Check if we're doing a BC check, if not, exit status 0
#
if [ -z "$CHECK_BC" ]; then
    exit 0
fi

#
# Run pyang over all the models in the 533 directory that also exist
# in the 532 peer directory, using the --check-update-from option.
# This requires pyang 1.5 or better, so we check this first.
#
version=`pyang --version | awk '{print $NF}'`
if ! awk -v ver="$version" 'BEGIN { if (ver < 1.5) exit 1; }'; then
    printf 'ERROR: pyang version 1.5 or higher required\n'
    exit 1
fi
UPDATE_FROM_PATH=../../../../standard/ietf/RFC
echo Comparing all models that also exist in ../$CHECK_BC AND that have
echo changed since version 600 with "--check-update-from" flag:
echo
for m in *.yang
do
    VER_FROM="../$CHECK_BC/$m"
    if [ -e "$VER_FROM" ]
    then
	DIFF=`diff $VER_FROM $m`
	if [ ! -z "$DIFF" ]
	then
	    pyang \
		--check-update-from $VER_FROM \
		--check-update-from-path $UPDATE_FROM_PATH \
		$m
	fi
    fi
done
'''

#
# The get filter we need to retrieve the schemas a device claims to have
#
schemas_filter = '''<netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
 <schemas/>
</netconf-state>'''

#
# print to stderr
#
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

#
# return an etree of the data retrieved
#
def get(m, filter=None):
    if filter and len(filter) > 0:
        c = m.get(filter=('subtree', filter))
    else:
        c = m.get()
    return c

#
# get a list of schema and save to the provided directory
#
def get_schema(m, schema_nodes, output_dir):
    failed_download = []
    for s, v in schema_nodes:
        try:
            c = m.get_schema(s, version=v)
            with open(output_dir+'/'+s+'@'+v+'.yang', 'w') as yang:
                print(BeautifulSoup(c.xml,
                                    convertEntities=BeautifulSoup.HTML_ENTITIES).find('data').getText(),
                      file=yang)
                yang.close()
        except RPCError as e:
            failed_download.append((s,v))
    return failed_download


if __name__ == '__main__':

    parser = ArgumentParser(description='Provide device and output parameters:')

    parser.add_argument('-a', '--host', type=str, required=True,
                        help="The device IP or DN")

    parser.add_argument('--port', type=int, required=False, default=830,
                        help="Optional port to contact for netconf")

    parser.add_argument('--ssh-port', type=int, required=False, default=22,
                        help="Optional port to contact for plain ssh")

    parser.add_argument('--device-type', type=str, default='cisco_xr',
                        help="Device type connecting to for netmiko")

    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")

    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")

    parser.add_argument('-t', '--timeout', type=int, required=False, default=30,
                        help="Netconf timeout; needed for slow devices")

    parser.add_argument('--process-MIBs', action="store_true", default=False,
                        dest="process_MIBs_sw",
                        help="Specify this to process advertised MIBs")

    parser.add_argument('--display-MIBs', action="store_true", default=False,
                        dest="display_MIBs_sw",
                        help="Specify this to process and display advertised MIBs")

    parser.add_argument('--git-repo', required=True, type=str,
                        help='Git reository to capture data to; should include any credentials required')

    parser.add_argument('--git-path', required=True, type=str,
                        help='Relative path in git repository to place schema and capabilities')

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

    #
    # Initialize OS & version strings for targetdir
    #
    ver = 'unknown'
    os = 'unknown'
    platform_metadata = {
          'vendor': 'cisco',
          'product-ids': [],
          'name': '',
          'os-type': '',
          'software-flavor': '',
          'software-version': '',
          'module-list-file': {}
    }

    #
    # Connect over netmiko
    #
    d = ConnectHandler(device_type=args.device_type,
                       ip=args.host,
                       port=args.ssh_port,
                       username=args.username,
                       password=args.password)
    version_output = d.send_command('show version')

    if args.device_type=='cisco_xr':
        os = 'xr'
        platform_metadata['os-type'] = 'IOS-XR'
        # TODO What do we want to track for software flavor?
        platform_metadata['software-flavor'] = 'ALL'
        inventory_output = d.send_command('show inventory all | begin Chassis')
        v = re.search(
            r'Version +: +([0-9\.A-Z]+)\n',
            version_output)
        if v is not None:
            ver = v.group(1)
            platform_metadata['software-version'] = v.group(1)

        pn = re.search(
             r'^cisco ([^\(]+)\(',
             version_output, re.M)
        if pn is not None:
            platform_metadata['name'] = pn.group(1).replace('Series', '').strip().replace(' ', '-')

        pid = re.search(
              r'PID: ([^,]+),', inventory_output)
        if pid is not None:
            platform_metadata['product-ids'].append(pid.group(1).strip())
        else:
            inventory_output = d.send_command('show inventory rack')
            pid = re.search(
                  r'^\s+ 0\s+([^\s]+)',
                  inventory_output, re.M)
            if pid is not None:
                platform_metadata['product-ids'].append(pid.group(1))
    elif args.device_type=='cisco_ios':
        os = 'xe'
        platform_metadata['os-type'] = 'IOS-XE'
        # TODO: Do we want to track licenses for XE here?
        platform_metadata['software-flavor'] = 'ALL'
        inventory_output = d.send_command('show inventory')
        v = re.search(
            r'Cisco IOS XE Software, Version ([a-zA-Z0-9_\.]+)',
            version_output)
        if v is not None:
            ver = v.group(1)
            platform_metadata['software-version'] = v.group(1)

        # This pattern seems complex, but it allows us to get the "C3850" part out
        # of "WS-C3850-48P" as an example.
        pn = re.search(
             r'^cisco (WS-)?([a-zA-Z0-9\-/]+)(-[0-9][0-9A-Z]+)? \([^)]+) processor',
             version_output, re.M)
        if pn is not None:
            platform_metadata['name'] = pn.group(2)

        pid = re.search(
              r'PID: ([^,]+),', inventory_output)
        if pid is not None:
            platform_metadata['product-ids'].append(pid.group(1).strip())
    elif args.device_type=='cisco_nxos':
        os = 'nx'
        platform_metadata['os-type'] = 'NX-OS'
        # TODO: What do we want to track for NX-OS?
        platform_metadata['software-flavor'] = 'ALL'
        inventory_output = d.send_command('show inventory')
        v = re.search(r'^\s+NXOS: version ([0-9A-Za-z\.\(\)_]+)',
            version_output, re.M)
        if v is not None:
            ver = v.group(1).replace('(', '-').replace(')', '-').strip('-')
            platform_metadata['software-version'] = v.group(1)

        pn = re.search(r'^\s+cisco ([^\s]+)\s.*Chassis',
             version_output, re.M)
        if pn is not None:
            platform_metadata['name'] = pn.group(1)

        pid = re.search(
              r'PID: ([^,]+),', inventory_output)
        if pid is not None:
            platform_metadata['product-ids'].append(pid.group(1).strip())

    args.git_path = '%s/%s/%s' % (args.git_path, os, ver)

    #
    # Pull down the repo and create the file output directory
    #
    repo = repoutil.RepoUtil(args.git_repo)
    repo.clone()
    targetdir = repo.localdir + '/' + args.git_path
    caps_name = platform_metdata['name'].lower() + '-capabilities.xml'
    caps_file = targetdir + '/' + caps_name
    platform_metadata['module-list-file']['type'] = 'capabilities'

    platform_metadata['module-list-file']['path'] = args.git_path + '/' + caps_name
    platform_metadata['module-list-file']['owner'] = repo.get_owner()
    platform_metadata['module-list-file']['repository'] = repo.get_repo_dir()
    if not exists(targetdir):
        makedirs(targetdir)

    # testing
    # targetdir = '.' + '/' + args.git_path
    # if not exists(targetdir):
    #     makedirs(targetdir)

    #
    # Connect to the router
    #
    def unknown_host_cb(host, fingerprint):
        return True
    mgr =  manager.connect(host=args.host,
                           port=args.port,
                           username=args.username,
                           password=args.password,
                           timeout=args.timeout,
                           allow_agent=False,
                           look_for_keys=False,
                           hostkey_verify=False,
                           unknown_host_cb=unknown_host_cb)

    #
    # Attempt to get the ietf-yang-library if available.
    # If not, fall back to capabilities.
    #
    do_caps = False
    try:
        response = mgr.get(('xpath', '/modules-state')).xml
        lib_data = etree.fromstring(response)
        lib_tags = lib_data.findall('.//{urn:ietf:params:xml:ns:yang:ietf-yang-library}modules-state')
        if len(lib_tags) == 0:
            raise Exception('No support for ietf-yang-library')

        with open(caps_file, 'w') as capsfile:
            for lib_tag in lib_tags:
                capsfile.write(etree.tostring(lib_tag, pretty_print=True))
            capsfile.close()
        platform_metadata['module-list-file']['type'] = 'yang-library'
    except (RPCError, Exception) as rpce:
        do_caps = True

    if do_caps:
        #
        # Save out capabilities
        #
        with open(caps_file, 'w') as capsfile:
            capsfile.write('''<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">\n <capabilities>\n''')
            for c in mgr.server_capabilities:
                capsfile.write('  <capability>{}</capability>\n'.format(c))
            capsfile.write(''' </capabilities>\n</hello>\n''')
            capsfile.close()
    #
    # Save out metadata (append if it exists)
    #
    md_file = targetdir + '/' + 'platform-metadata.json'
    md = { 'platforms': [] }
    if isfile(md_file) and getsize(md_file) > 0:
        mdfile = open(md_file, 'r')
        md = json.load(mdfile)
        mdfile.close()

        found_platform = False
        for platform in md['platforms']:
            if platform['vendor']=='cisco' and platform['name']==platform_metadata['name']:
                found_platform = True
                if platform_metadata['product-ids'][0] not in platform['product-ids']:
                    platform['product-ids'].append(platform_metadata['product-ids'][0])
                break

        if not found_platform:
            md['platforms'].append(platform_metadata)
    else:
        md['platforms'].append(platform_metadata)

    mdfile = open(md_file, 'w')
    json.dump(md, mdfile, indent=4)
    mdfile.close()

    #
    # Open up a report file
    #
    reportfile = open(targetdir+'/'+'REPORT.md', 'w')
    reportfile.write('# Schema & Capabilities Capture Report\n\n')
    reportfile.write('- Operating System: %s\n' % os)
    reportfile.write('- Version: %s\n\n' % ver)

    #
    # retrieve the schemas datatree and extract all the schema
    # identifiers
    #
    schema_tree = get(mgr, schemas_filter)
    soup = BeautifulSoup(schema_tree.data_xml)
    schema_nodes = [(s.findChild('identifier').getText(),
                     s.findChild('version').getText())
                    for s in soup.findAll('schema')]

    #
    # check the schema list against server capabilities
    #
    not_in_schemas = set()
    for c in mgr.server_capabilities:
        model = re.search('module=([^&]*)&revision=([0-9]+-[0-9]+-[0-9]+)', c)
        if model is not None:
            m = model.group(1)
            v = model.group(2)
            if (m, v) not in schema_nodes:
                not_in_schemas.add((m,v))
    if len(not_in_schemas) > 0:
        reportfile.write('The following models are advertised in capabilities but are not in schemas tree:\n\n')
        for m, v in sorted(not_in_schemas):
            write('- {}, revision={}\n'.format(m, v))

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
    failed = get_schema(mgr, schema_nodes, targetdir)
    for f in failed:
        failed_download.add(f)

    #
    # Now let's check all the schema that we downloaded (from this run
    # and any other) and parse them with pyang to extract any imports
    # or includes and verify that they were on the advertised schema
    # list and didn't fail download.
    #
    # TODO: cater for explicitly revisioned imports & includes
    #
    imports_and_includes = set()
    repos = pyang.FileRepository(targetdir)
    yangfiles = [f for f in listdir(targetdir) if isfile(join(targetdir, f))]
    for fname in yangfiles:
        ctx = pyang.Context(repos)
        if args.process_MIBs_sw or args.display_MIBs_sw:
            if "MIB" in fname:
                mib_name = str(fname).rstrip('.yang')
                mib_filter = '<'+mib_name+':'+mib_name+' xmlns:'+mib_name+'="urn:ietf:params:xml:ns:yang:smiv2:'+mib_name+'"/>'
                try:
                    mib = get(mgr, mib_filter)
                    if args.display_MIBs_sw:
                        print(mib_name)
                        soup = BeautifulSoup(mib)
                        print(soup.prettify())
                except RPCError as e:
                    print(mib_name)
                    print(e)
        fd = open(targetdir+'/'+fname, 'r')
        text = fd.read()
        ctx.add_module(fname, text)
        this_module = basename(fname).split(".")[0]
        for ((m,r), module) in ctx.modules.iteritems():
            if m==this_module:
                for s in module.substmts:
                    if (s.keyword=='import') or (s.keyword=='include'):
                        imports_and_includes.add(s.arg)

    #
    # Verify that all imports and includes appeared in the advertised
    # schema
    #
    schema_list = [m for m, r in schema_nodes]
    not_advertised = [i for i in imports_and_includes if i not in schema_list]
    if len(not_advertised)>0:

        #
        # list the not-advertised schemas
        #
        reportfile.write('\nThe following schema are imported or included, but not listed in schemas tree:\n\n')
        for m in sorted(not_advertised, key=str.lower):
            reportfile.write('- {}\n'.format(m))

        #
        # try to download the not-advertised schemas
        #
        for m in not_advertised:
            try:
                c = mgr.get_schema(m)
                with open(targetdir+'/'+m+'.yang', 'w') as yang:
                    print(c.data, file=yang)
                    yang.close()
            except RPCError as e:
                failed_download.add(str(m))

    #
    # List out the schema that are imported or included and NOT
    # downloaded successfully.
    #
    if len(failed_download)>0:
        reportfile.write('\nThe following schema are imported, included or advertised, but not downloadable:\n\n')
        for m, v in sorted(failed_download):
            reportfile.write('- {}\n'.format(m))
    reportfile.write('\n')

    #
    # Craete check-models.sh
    #
    with open(targetdir+'/check-models.sh', 'w') as f:
        f.write(check_models)
        f.close()

    #
    # cleanup
    #
    reportfile.close()

    #
    # Commit everything to local repo and push to origin
    #
    try:
        repo.add_all_untracked()
        repo.commit_all(message='Push version %s models.' % ver)
        repo.push()
    except GitCommandError as e:
        eprint("Add, Commit Or Push Failed:")
        eprint(e.stdout)
        eprint(e.stderr)
    repo.remove()
