#!/usr/bin/env python
from jinja2 import Template
from argparse import ArgumentParser

script_template=Template("""
#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from ncclient import manager

data = '''<filter>
  {{FILL_THIS}}
</filter>'''
        
        
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
    
    args = parser.parse_args()

    m =  manager.connect(host=args.host,
                         port=args.port,
                         username=args.username,
                         password=args.password,
                         device_params={'name':"csr"})
    print m.get(data)
""")

if __name__ == '__main__':
    parser = ArgumentParser(description='Select options.')
    parser.add_argument('--xml', type=str, required=True,
                        help="The XML to wrap up in a get")
    args = parser.parse_args()
    print script_template.render(FILL_THIS=args.xml)
