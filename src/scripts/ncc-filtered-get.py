#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
import sys
from argparse import ArgumentParser
from ncclient import manager
from lxml import etree

if __name__ == '__main__':

    parser = ArgumentParser(description='Select options.')

    # Input parameters
    parser.add_argument('--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")
    parser.add_argument('--filter', type=str, required=True,
                        help="The filter to use for the get operation")
    
    args = parser.parse_args()

    m =  manager.connect(host=args.host,
                         port=args.port,
                         username=args.username,
                         password=args.password,
                         device_params={'name':"csr"})
    data = m.get('<filter>'+args.filter+'</filter>')
    print etree.tostring(etree.fromstring(data.xml), pretty_print=True)
