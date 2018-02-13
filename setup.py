import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'ncc',
    version = '0.1.0',
    description = ('A set of NETCONF/YANG-focused scripts using ncclient'),
    long_description = """The package ncc contains a set of scripts for working with NETCONF/YANG via the ncclient library. Scripts support simple tasks such as get/get-config/edit-config and schema download and more! Not all scripts in the repository itself are installed.""",
    # packages = ['ncc'],
    scripts = [
        #'ncc-get-all-schema',
        'ncc-get-schema',
        #'ncc-simple-poller',
        'ncc'
    ],
    author = 'Einar Nilsen-Nygaard',
    author_email = 'einarnn@gmail.com',
    license = 'Apache 2.0',
    url = 'https://github.com/CiscoDevNet/ncc',
    install_requires = [
        'Jinja2>=2.8',
        'pyang>=1.7.3',
        'ncclient>=0.5.3'
    ],
    include_package_data = True,
    keywords = ['yang', 'netconf'],
    classifiers = [],
)
