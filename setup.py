#
# Copyright (c) 2018 Cisco and/or its affiliates
#
import os
import versioneer
from setuptools import setup

__author__ = "Einar Nilsen-Nygaard"
__author_email__ = "einarnn@cisco.com"
__copyright__ = "Copyright (c) 2018 Cisco and/or its affiliates."
__license__ = "Apache 2.0"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='ncc',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description=('A set of NETCONF/YANG-focused scripts using ncclient'),
    long_description="""The package ncc contains a set of scripts for working with NETCONF/YANG via the ncclient library. Scripts support simple tasks such as get/get-config/edit-config and schema download and more! Not all scripts in the repository itself are installed.""",
    packages = ['nccutil'],
    scripts=[
        'ncc-capture-schema',
        'ncc-get-all-schema',
        'ncc-get-schema',
        'ncc-yang-push',
        'ncc',
    ],
    author=__author__,
    author_email=__author_email__,
    license=__license__ + "; " + __copyright__,
    url='https://github.com/CiscoDevNet/ncc',
    download_url='https://pypi.python.org/pypi/ncc',
    install_requires=[
        'Jinja2>=2.8',
        'pyang>=1.7.3',
        'ncclient>=0.6.3',
        'GitPython>=2.1.3',
        'beautifulsoup4>=4.6.0',
        'netmiko>=2.0.2'
    ],
    include_package_data=True,
    keywords=['yang', 'netconf'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
