# Various Scripts & Jupyter Notebooks

## Dependencies


The package dependencies for the scripts and the jupyter notebooks are listed in ```requirements.txt```, which may be used to install the dependencies thus (note the upgrade to pip; must be running pip >= 8.1.2 to successfully install some dependenciues):

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

This example shows using the virtualenv tool to isolate packages from your global python install. This is recommended. Note that the versiojn of pip installed in the test environment was up to date, and so it did not need upgraded.

## Running A Jupyter Notebook

The jupyter notebook server should be run inside the same Python virtualenv as you created above. The server is run up thus:

```
EINARNN-M-D10Q:ncc einarnn$ pwd
/opt/git-repos/ncc
EINARNN-M-D10Q:ncc einarnn$ . v/bin/activate
(v) EINARNN-M-D10Q:ncc einarnn$ jupyter notebook
[I 16:39:38.230 NotebookApp] The port 8888 is already in use, trying another port.
[I 16:39:38.240 NotebookApp] Serving notebooks from local directory: /opt/git-repos/ncc
[I 16:39:38.240 NotebookApp] 0 active kernels
[I 16:39:38.240 NotebookApp] The Jupyter Notebook is running at: http://localhost:8889/
[I 16:39:38.240 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
```

When the notebook server is running, it will also open up a web page with your default web browser, pointing to the jupyter notebook server. Just pick one of the notebooks (```*.ipynb```) and away you go!!


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
