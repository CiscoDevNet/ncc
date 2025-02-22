#!/usr/bin/env python
#
# Copyright (c) 2018 Cisco and/or its affiliates
#
import sys
import requests
from argparse import ArgumentParser
from requests.auth import HTTPBasicAuth


def send_request(protocol, host, port, username, password):
    '''Generate a simple RESTCONF request.
    '''
    # url = "{}://{}:{}/restconf/data/Cisco-IOS-XR-ifmgr-cfg:interface-configurations/interface-configuration=act,GigabitEthernet0%2f0%2f0%2f0/description".format(
    url = "{}://{}:{}/restconf/data/Cisco-IOS-XR-ifmgr-cfg:interface-configurations".format(
        protocol, host, port)
    try:
        response = requests.get(
            auth=HTTPBasicAuth(username, password),
            url=url,
            params={
                "content": "config",
            },
            headers={
                "Accept": "application/yang.data+json, application/yang.errors+json",
            },
        )
        print('Response HTTP Status Code: {status_code}'.format(
            status_code=response.status_code))
        print('Response HTTP Response Body: {content}'.format(
            content=response.content))
    except requests.exceptions.RequestException:
        print('HTTP Request failed')


if __name__ == '__main__':

    parser = ArgumentParser(description='Do a RESTCONF operation:')

    # Input parameters
    parser.add_argument('--host', type=str, required=True,
                        help="The device IP or DN")
    parser.add_argument('-u', '--username', type=str, default='cisco',
                        help="Go on, guess!")
    parser.add_argument('-p', '--password', type=str, default='cisco',
                        help="Yep, this one too! ;-)")
    parser.add_argument('--port', type=int, default=830,
                        help="Specify this if you want a non-default port")

    args = parser.parse_args()

    send_request( "http", args.host, args.port, args.username, args.password)
