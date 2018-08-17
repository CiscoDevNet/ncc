# Various Scripts & Jupyter Notebooks

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [New & Updated](#new--updated)
- [Introduction](#introduction)
- [Python Dependencies](#python-dependencies)
- [Python Scripts](#python-scripts)
  - [Running The Scripts](#running-the-scripts)
  - [ncc-establish-subscription.py](#ncc-establish-subscriptionpy)
  - [ncc.py](#nccpy)
    - [Device Capabilities](#device-capabilities)
    - [Snippets](#snippets)
- [Running The Jupyter Notebooks](#running-the-jupyter-notebooks)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## New & Updated

|  Date  | Status |  Description  |
| :----: | :----: | :------------ |
| 08/17/18 | ![](images/updated.png) | Added option to specify # bytes displayed for UnicodeDecodeError exceptions | 
| 08/15/18 | ![](images/updated.png) | Added operation timing plus helpful display of UnicodeDecodeError exceptions to `ncc` | 
| 03/11/18 | ![](images/updated.png) | Code review comments addressed, convenience links to still have .py versions of scripts added, `ncc --env` now shows command line option environment variables apply to |
| 02/21/18 | ![](images/updated.png) | Tweaks to `ncc-capture-schema` plus its addition to packaged scripts |
| 02/14/18 | ![](images/new.png) | Addition of `--install-snippets` and `--env` options to `ncc`.
| 02/14/18 | ![](images/updated.png) | Preparation for pip installation and PyPi upload; removing `.py` extensions from scripts that will be pip-installed; addition of copyright statements and [`LICENSE.txt`](LICENSE.txt); removed legacy script links.
| 02/09/18 | ![](images/new.png) | Addition of `--ns` option for XPath filters, allowing either direct list of namespace mapping or via a file (sample file [here](sample-ns.json)) 


## Introduction

This repository presents:

* Python scripts using the ncclient library (`0.5.2` or greater as of writing) to talk to NETCONF-enabled devices.
* Jupyter (IPython) Notebooks in the directory [`notebooks`](notebooks).


## Python Dependencies

The package dependencies for the scripts and the jupyter notebooks are listed in ```requirements.txt```, which may be used to install the dependencies thus (note the upgrade to pip; must be running **```pip >= 8.1.2```** to successfully install some dependencies):

```
EINARNN-M-80AT:ncc einarnn$ virtualenv v
New python executable in v/bin/python2.7
Also creating executable in v/bin/python
Installing setuptools, pip, wheel...done.
EINARNN-M-80AT:ncc einarnn$ . v/bin/activate
(v)EINARNN-M-80AT:ncc einarnn$ pip install --upgrade pip
Requirement already up-to-date: pip in ./v/lib/python2.7/site-packages
(v)EINARNN-M-80AT:ncc einarnn$ pip install -r requirements.txt
```

This example shows using the virtualenv tool to isolate packages from your global python install. This is recommended. Note that the version of pip installed in the test environment was up to date, and so it did not need upgraded.

Please note that the script `ncc-establish-subscription.py` currently requires a temporarily [forked version](https://github.com/CiscoDevNet/ncclient) of the `ncclient` library.


## Python Scripts

The Python scripts have been radically rationalized and there are now just a few key scripts, with the remainder moved to the [```archived```](archived) directory. The main scripts are:

* [`ncc`](ncc) -- A kind of Swiss Army Knife script with many options to get-config, get, edit-config, pass in parameters for substitution, etc. Can be easily extended by users to have more edit-config templates or more named filter templates. Available content can be seen using the ```--list-templates``` and ```--list-filters``` parameters.

* [`ncc-establish-subscription.py`](ncc-establish-subscription.py) -- Simple script to allow the creation of multiple dynamic telemetry subscriptions per an early draft of the IETF YANG Push functionality. Currently supported on IOS-XE 16.6.1 and later. Initial support was for switching platforms, with other platforms being supported in subsequent releases. **Note that this script requires a fork of the `ncclient` library. Once the Python dependencies above have been installed, the forked version may be installed using the command `pip install --upgrade git+https://github.com/CiscoDevNet/ncclient.git`**. Please see [here](https://github.com/CiscoDevNet/ncclient/blob/master/README.md) for more details.

* [`ncc-filtered-get.py`](ncc-filtered-get.py) -- Very simple script that takes a subtree filter and does a get.

* [`ncc-get-all-schema`](ncc-get-all-schema) -- Script that attempts to download all the supported schema that the box has and tries to compile them, determine missing includes or imports, etc.

* [`ncc-get-schema`](ncc-get-schema) -- Script to get a single names schema and dup it to ```STDOUT```.

* [`ncc-capture-schema`](ncc-capture-schema) -- Script to capture the schema from a device and commit int a git reposiroty structured per [YangModels/yang](https://github.com/YangModels/yang). Uses netmiko to capture some initial device information, and needs device type passed in from CLI (per netmiko device types). Currently only supports IOS-XR, IOS-XE and NX-OS without changes. Fairly easy to add other device types.

* [`ncc-simple-poller.py`](ncc-simple-poller.py) -- Script that polls a device on a specified cadence for a specified subtree or XPath filter.

* [`rc-xr.py`](rc-xr.py) -- Embryonic RESTCONF sample script using the Python `requests` library.


A couple of the scripts used to have other names, so, for backwards compatibility, the following symlinks currently exist:


### Running The Scripts

The scripts mostly have a fairly common set of options for help, hostname, port, username and password. Just try running with the `--help` option.

> Note that the help text displayed here may be out of step with the actual code. Please run latest version of the script to ensure satisfaction!


### ncc-establish-subscription.py

> Note that this script requires a fork of the `ncclient` library. Once the Python dependencies above have been installed, the forked version may be installed using the command:
>
>`pip install --upgrade git+https://github.com/CiscoDevNet/ncclient.git`.
>
> Please see [here](https://github.com/CiscoDevNet/ncclient/blob/master/README.md) for more details.

```
$ ./ncc-establish-subscription.py --help
usage: ncc-establish-subscription.py [-h] [--host HOST] [-u USERNAME]
                                     [-p PASSWORD] [--port PORT] [-v]
                                     [--delete-after DELETE_AFTER]
                                     [-x XPATHS [XPATHS ...]]
                                     (--period PERIOD | --dampening-period DAMPENING_PERIOD)

Select your telemetry parameters:

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           The IP address for the device to connect to (default
                        localhost)
  -u USERNAME, --username USERNAME
                        Username to use for SSH authentication (default
                        'cisco')
  -p PASSWORD, --password PASSWORD
                        Password to use for SSH authentication (default
                        'cisco')
  --port PORT           Specify this if you want a non-default port (default
                        830)
  -v, --verbose         Exceedingly verbose logging to the console
  --delete-after DELETE_AFTER
                        Delete the established subscription after N seconds
  -x XPATHS [XPATHS ...], --xpaths XPATHS [XPATHS ...]
                        List of xpaths to subscribe to, one or more
  --period PERIOD       Period in centiseconds for periodic subscription
  --dampening-period DAMPENING_PERIOD
                        Dampening period in centiseconds for on-change
                        subscription

```

### ncc

```
$ ncc --help
usage: ncc [-h] [--host HOST] [-u USERNAME] [-p PASSWORD] [--port PORT]
           [--timeout TIMEOUT] [-v] [--default-op DEFAULT_OP]
           [--device-type DEVICE_TYPE] [--snippets SNIPPETS]
           [--ns NS [NS ...]] [--params PARAMS] [--params-file PARAMS_FILE]
           [-f FILTER | --named-filter NAMED_FILTER [NAMED_FILTER ...] | -x
           XPATH]
           (--env | --install-snippets | -c | --is-supported IS_SUPPORTED | --list-templates | --list-filters | -g | --get-oper | --do-edits DO_EDITS [DO_EDITS ...] | -w)

Select your NETCONF operation and parameters:

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           The IP address for the device to connect to (default
                        localhost)
  -u USERNAME, --username USERNAME
                        Username to use for SSH authentication (default
                        'cisco')
  -p PASSWORD, --password PASSWORD
                        Password to use for SSH authentication (default
                        'cisco')
  --port PORT           Specify this if you want a non-default port (default
                        830)
  --timeout TIMEOUT     NETCONF operation timeout in seconds (default 60)
  -v, --verbose         Exceedingly verbose logging to the console
  --default-op DEFAULT_OP
                        The NETCONF default operation to use (default 'merge')
  --device-type DEVICE_TYPE
                        The device type to pass to ncclient (default: None)
  --snippets SNIPPETS   Directory where 'snippets' can be found; default is
                        location of script
  --ns NS [NS ...]      Specify list of prefix=NS bindings or JSON files with
                        bindings. @filename will read a JSON file and update
                        the set of namespace bindings, silently overwriting
                        with any redefinitions.
  --params PARAMS       JSON-encoded string of parameters dictionary for
                        templates
  --params-file PARAMS_FILE
                        JSON-encoded file of parameters dictionary for
                        templates
  -f FILTER, --filter FILTER
                        NETCONF subtree filter
  --named-filter NAMED_FILTER [NAMED_FILTER ...]
                        List of named NETCONF subtree filters
  -x XPATH, --xpath XPATH
                        NETCONF XPath filter
  --env                 Display environment variables a user can set.
  --install-snippets    Use git to obtain the snippets from GitHub and copy to
                        the current directory
  -c, --capabilities    Display capabilities of the device.
  --is-supported IS_SUPPORTED
                        Query the server capabilities to determine whether the
                        device claims to support YANG modules matching the
                        provided regular expression. The regex provided is not
                        automatically anchored to start or end. Note that the
                        regex supplied must be in a format valid for Python
                        and that it may be necessary to quote the argument.
  --list-templates      List out named edit-config templates
  --list-filters        List out named filters
  -g, --get-running     Get the running config
  --get-oper            Get oper data
  --do-edits DO_EDITS [DO_EDITS ...]
                        Execute a sequence of named templates with an optional
                        default operation and a single commit when candidate
                        config supported. If only writable-running support,
                        ALL operations will be attempted.
  -w, --where           Print where script is and exit
```

In subsequent sections some of its capabilities will be expanded on.

#### Device Capabilities

It is now possible to query the device either to return a categorized list of capabilities and models or to return the models matching a provided Python regular expression.

To get device capabilities:

```
python ncc --host=192.239.42.222 --capabilities
IETF NETCONF Capabilities:
	urn:ietf:params:netconf:capability:rollback-on-error:1.0
	urn:ietf:params:netconf:base:1.1
	urn:ietf:params:netconf:capability:candidate:1.0
	urn:ietf:params:netconf:capability:validate:1.1
	urn:ietf:params:netconf:capability:confirmed-commit:1.1
IETF Models:
	ietf-netconf (urn:ietf:params:xml:ns:netconf:base:1.0)
	ietf-syslog-types (urn:ietf:params:xml:ns:yang:ietf-syslog-types)
	ietf-yang-smiv2 (urn:ietf:params:xml:ns:yang:ietf-yang-smiv2)
	ietf-netconf-with-defaults (urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults)
	ietf-netconf-monitoring (urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring)
	ietf-yang-types (urn:ietf:params:xml:ns:yang:ietf-yang-types)
	iana-if-type (urn:ietf:params:xml:ns:yang:iana-if-type)
	ietf-inet-types (urn:ietf:params:xml:ns:yang:ietf-inet-types)
OpenConfig Models:
	openconfig-bgp-multiprotocol (http://openconfig.net/yang/bgp-multiprotocol)
	openconfig-bgp-policy (http://openconfig.net/yang/bgp-policy)
	openconfig-bgp-types (http://openconfig.net/yang/bgp-types)
	openconfig-mpls-rsvp (http://openconfig.net/yang/rsvp)
	openconfig-routing-policy (http://openconfig.net/yang/routing-policy)
	openconfig-bgp-operational (http://openconfig.net/yang/bgp-operational)
	openconfig-extensions (http://openconfig.net/yang/openconfig-ext)
	openconfig-telemetry (http://openconfig.net/yang/telemetry)
	openconfig-mpls-sr (http://openconfig.net/yang/sr)
	openconfig-if-ethernet (http://openconfig.net/yang/interfaces/ethernet)
	openconfig-vlan (http://openconfig.net/yang/vlan)
	openconfig-policy-types (http://openconfig.net/yang/policy-types)
	openconfig-types (http://openconfig.net/yang/openconfig-types)
	openconfig-mpls-types (http://openconfig.net/yang/mpls-types)
	openconfig-if-ip (http://openconfig.net/yang/interfaces/ip)
	openconfig-if-aggregate (http://openconfig.net/yang/interface/aggregate)
	openconfig-bgp (http://openconfig.net/yang/bgp)
	openconfig-mpls (http://openconfig.net/yang/mpls)
	openconfig-interfaces (http://openconfig.net/yang/interfaces)
	openconfig-mpls-ldp (http://openconfig.net/yang/ldp)
...etc...
```

To query for supported models (running against an IOS-XR image):

```
15:10 $ python ncc --host=192.239.42.222 --is-supported '(?i)snmp'
SNMP-NOTIFICATION-MIB
SNMP-MPD-MIB
Cisco-IOS-XR-snmp-entstatemib-cfg
Cisco-IOS-XR-snmp-agent-oper
SNMP-FRAMEWORK-MIB
Cisco-IOS-XR-snmp-agent-cfg
SNMP-COMMUNITY-MIB
Cisco-IOS-XR-snmp-entitymib-oper
Cisco-IOS-XR-snmp-test-trap-act
Cisco-IOS-XR-snmp-syslogmib-cfg
Cisco-IOS-XR-snmp-ifmib-oper
SNMPv2-TC
SNMP-USER-BASED-SM-MIB
SNMPv2-MIB
Cisco-IOS-XR-snmp-ifmib-cfg
Cisco-IOS-XR-snmp-mib-rfmib-cfg
Cisco-IOS-XR-snmp-ciscosensormib-cfg
SNMP-VIEW-BASED-ACM-MIB
Cisco-IOS-XR-snmp-entitymib-cfg
SNMP-TARGET-MIB
Cisco-IOS-XR-snmp-sensormib-oper
Cisco-IOS-XR-snmp-frucontrolmib-cfg
```

Additionally, this example shows how to use case-insentitive regex matches in Python.

#### Snippets

Snippets are a way to pre-define edit-config messages or complex filters that you want to use from the command line. Snippets are simple Jinja2 templates, with parameters provided either from the command line or via a file.

Snippets are by default found in a directory  ```snippets``` colocated with the ```ncc.py``` script.
Named subtree filters are stored in [snippets/filters](snippets/filters) and named edit-config templates are stored in [snippets/editconfigs](snippets/editconfigs). The naming convention is fairly obvious; templates files end in ```.tmpl```, but when referred to via CLI arguments the extension is ommitted.

The command line option ```--snippets``` may be used to define an alternate location for the ```snippets``` directory.
A directory structure as shown below must exist in the location pointed to by the ```--snippets``` parameter.
For example, ```--snippets ./snippets-xe``` would expect the following directory structure.

```
snippets-xe
├── editconfigs
└── filters
```

The snippets for both edit config messages and named filters now support a JSON format for specifying parameters either on the command line of in a provided file. For example, we may have the filter snippet in file ```intf-brief.tmpl```:

```
<interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
  <interface-briefs>
    <interface-brief>
      <interface-name>{{INTF_NAME}}</interface-name>
    </interface-brief>
</interfaces>
```

Then, run against IOS-XR:

```
$ python ncc --host=192.239.42.222 --get-oper --named-filter intf-brief --params '{"INTF_NAME":"GigabitEthernet0/0/0/0"}'
<data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
   <interface-briefs>
    <interface-brief>
     <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <interface>GigabitEthernet0/0/0/0</interface>
     <type>IFT_GETHERNET</type>
     <state>im-state-admin-down</state>
     <actual-state>im-state-admin-down</actual-state>
     <line-state>im-state-admin-down</line-state>
     <actual-line-state>im-state-admin-down</actual-line-state>
     <encapsulation>ether</encapsulation>
     <encapsulation-type-string>ARPA</encapsulation-type-string>
     <mtu>1514</mtu>
     <sub-interface-mtu-overhead>0</sub-interface-mtu-overhead>
     <l2-transport>false</l2-transport>
     <bandwidth>1000000</bandwidth>
    </interface-brief>
   </interface-briefs>
  </interfaces>
 </data>
```

Or:

```
$ echo '{"INTF_NAME":"GigabitEthernet0/0/0/0"}' > test_params.json
$ python ncc --host=192.239.42.222 --get-oper --named-filter intf-brief --params-file test_params.json
<data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
   <interface-briefs>
    <interface-brief>
     <interface-name>GigabitEthernet0/0/0/0</interface-name>
     <interface>GigabitEthernet0/0/0/0</interface>
     <type>IFT_GETHERNET</type>
     <state>im-state-admin-down</state>
     <actual-state>im-state-admin-down</actual-state>
     <line-state>im-state-admin-down</line-state>
     <actual-line-state>im-state-admin-down</actual-line-state>
     <encapsulation>ether</encapsulation>
     <encapsulation-type-string>ARPA</encapsulation-type-string>
     <mtu>1514</mtu>
     <sub-interface-mtu-overhead>0</sub-interface-mtu-overhead>
     <l2-transport>false</l2-transport>
     <bandwidth>1000000</bandwidth>
    </interface-brief>
   </interface-briefs>
  </interfaces>
 </data>

```
If you do not supply all of the required vars, you will get an error when using the template.  For example in the above

```
python ncc --host=192.239.42.222 --get-oper --named-filter intf-brief
Undefined variable 'INTF_NAME' is undefined.  Use --params to specify json dict

```

If you wish to leave a variable empty (for example in a filter, rather than edit-config, you can just specify it as ""

```
{"INTF_NAME" : ""}
```

When edit-config templates or filters are listed (```--list-templates``` or ```--list-filters```), the variables that need to be substituted are also listed. For example:

```
11:28 $ ncc --list-templates
Edit-config templates:
  add_neighbor                           <<-- template name
    DESCRIPTION                          <<-- substitution
    NEIGHBOR_ADDR
    REMOTE_AS
  add_static_route_default
  del_neighbor
    NEIGHBOR_ADDR
```

## Running The Jupyter Notebooks

The jupyter notebook server should be run inside the same Python virtualenv as you created above for running the Python scripts, with one addition, which is to run ```pip install jupyter``` in the virtual environment, as it is not currently listed in the [```requirements.txt```](requirements.txt) file.

Once Jupyter installed, the notebook server is run up thus:

```
$ pwd
/opt/git-repos/ncc
$ . v/bin/activate
(v) EINARNN-M-D10Q:ncc einarnn$ jupyter notebook
[I 16:39:38.230 NotebookApp] The port 8888 is already in use, trying another port.
[I 16:39:38.240 NotebookApp] Serving notebooks from local directory: /opt/git-repos/ncc
[I 16:39:38.240 NotebookApp] 0 active kernels
[I 16:39:38.240 NotebookApp] The Jupyter Notebook is running at: http://localhost:8889/
[I 16:39:38.240 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
```

When the notebook server is running, it will also open up a web page with your default web browser, pointing to the jupyter notebook server. Just pick one of the notebooks in the [notebooks](notebooks) directory (```*.ipynb```) and away you go!!
