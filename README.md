# Various Scripts

## Dependencies

> Note that if you are running against IOS-XR, you will currently need a version of ncclient that is not in the pypi repository. Please install from https://github.com/einarnn/ncclient. When the necessary changes have been merged upstream, this note will be removed.

The package dependencies for the scripts are listed in ```requirements.txt```, which may be used to install the dependencies thus:

```
EINARNN-M-80AT:ncc einarnn$ virtualenv v
New python executable in v/bin/python2.7
Also creating executable in v/bin/python
Installing setuptools, pip, wheel...done.
EINARNN-M-80AT:ncc einarnn$ . v/bin/activate
(v)EINARNN-M-80AT:ncc einarnn$ pip install -r requirements.txt
```

This example shows using the virtualenv tool to isolate packages from your global python install. This is recommended.

## Running The Scripts

The scripts mostly have a fairly common set of options for help, hostname, port, username and password. For example:

```
(ncc)EINARNN-M-80AT:ncc einarnn$ ./ncc-oc-bgp.py --help
usage: ncc-oc-bgp.py [-h] --host HOST [-u USERNAME] [-p PASSWORD]
                     [--port PORT] [-n NEIGHBOR_ADDR] [-r REMOTE_AS]
                     [--description DESCRIPTION] [-v] [-f FILTER | -o]
                     [-g | -b | -a | -d | --add-del-neighbor | --add-static-route]

Select your simple OC-BGP operation:

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           The device IP or DN
  -u USERNAME, --username USERNAME
                        Go on, guess!
  -p PASSWORD, --password PASSWORD
                        Yep, this one too! ;-)
  --port PORT           Specify this if you want a non-default port
  -n NEIGHBOR_ADDR, --neighbor-addr NEIGHBOR_ADDR
                        Specify a neighbor address, no validation
  -r REMOTE_AS, --remote-as REMOTE_AS
                        Specify the neighbor's remote AS, no validation
  --description DESCRIPTION
                        Specify the neighbor's description, just a string
                        (quote it!)
  -v, --verbose         Do I really need to explain?
  -f FILTER, --filter FILTER
                        XML-formatted netconf subtree filter
  -o, --oc-bgp-filter   XML-formatted netconf subtree filter
  -g, --get-running     Get the running config
  -b, --basic           Establish basic BGP config
  -a, --add-neighbor    Add a BGP neighbor
  -d, --del-neighbor    Delete a BGP neighbor by address
  --add-del-neighbor    And *and* delete a BGP neighbor by address
  --add-static-route    Get routes oper data
```

## The Scripts

The scripts here are listed below with some minimal descriptions, but the real functionality can only be gleaned by reading the code for now. The code is **not** production-ready in general, and if there is no description it may be because the script is no longer used or maintained.

- [ncc-cia.py](ncc-cia.py)
- [ncc-csr1000v.py](ncc-csr1000v.py)
- [ncc-get-all-schema.py](ncc-get-all-schema.py): Get all the schema from a device that are listed in the initial capabilities exchange. Modules that are included or imported are **not** downloaded by the script currently. An output directory must be provided, and all downloaded schema are put there.
- [ncc-get-config-running.py](ncc-get-config-running.py)
- [ncc-get-oper-interface-all.py](ncc-get-oper-interface-all.py)
- [ncc-get-oper-interface-interfacebrief-name.py](ncc-get-oper-interface-interfacebrief-name.py)
- [ncc-get-oper-interface-interfacebriefs.py](ncc-get-oper-interface-interfacebriefs.py)
- [ncc-get-oper-interface-location-view.py](ncc-get-oper-interface-location-view.py)
- [ncc-get-oper-interface-nodetypesets.py](ncc-get-oper-interface-nodetypesets.py)
- [ncc-get-oper-interface-stats-forever.py](ncc-get-oper-interface-stats-forever.py)
- [ncc-get-oper-interface-stats.py](ncc-get-oper-interface-stats.py)
- [ncc-get-oper-interface-system-view.py](ncc-get-oper-interface-system-view.py)
- [ncc-get-oper-interface-xr.py](ncc-get-oper-interface-xr.py)
- [ncc-get-oper-interface.py](ncc-get-oper-interface.py)
- [ncc-get-schema.py](ncc-get-schema.py): Get a specific named schema. The schema is printed to STDOUT.
- [ncc-list-caps.py](ncc-list-caps.py)
- [ncc-list-schema.py](ncc-list-schema.py): List the schema advertised in the initial capabilities exchange.
- [ncc-oc-bgp.py](ncc-oc-bgp.py): A variety of OpenConfig operations combined with some generic "get the config with an optional subtree filter" functionality.
- [ncc-validate.py](ncc-validate.py)
