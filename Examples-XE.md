# A bunch of examples for Using the XE filters and editconfigs

## Environment vars
This will same specifying username and password.  It also will point to the XE snippets directory.

```buildoutcfg
source local_vars
```
This file contains the following shell environment variables
```buildoutcfg
export NCC_USERNAME=myuser
export NCC_PASSWORD=my-password
export NCC_SNIPPETS=./ncc/snippets-xe
```

## Basic Requests
These will get the capabilities.
```buildoutcfg
./ncc/ncc.py --host=adam-csr --capabilities
./ncc/ncc.py --host=adam-csr --get-oper -x /netconf-state/schemas
./ncc/ncc.py --host=adam-csr --get-oper -x //schemas

```

## oper-data
A couple of requests for oper-data

```buildoutcfg
./ncc/ncc.py --host=adam-csr --get-oper -x /interfaces-state
./ncc/ncc.py --host=adam-3850 --get-oper -x "/interfaces-state/interface[name='GigabitEthernet1/0/1']"
./ncc/ncc.py --host=adam-3850 --get-oper -x "/interfaces-state/interface[substring(name,1, 7) = 'Gigabit']"
./ncc/ncc.py --host=adam-csr --get-oper -x "/IF-MIB/ifTable"
./ncc/ncc.py --host=adam-3850 --get-oper -x "/routing-state"
```

## Interfaces
```buildoutcfg
./ncc/ncc.py --host=adam-csr --get-running -x /interfaces
./ncc/ncc.py --host=adam-csr --get-running -x /interfaces//name
./ncc/ncc.py --host=adam-3850 --get-running --named-filter ietf-intf-named --params='{ "INTF_NAME" : "GigabitEthernet1/0/1"}'
./ncc/ncc.py --host=adam-3850 --get-running --named-filter openconfig-intf --params='{ "INTF_NAME" : "GigabitEthernet1/0/1"}'
./ncc/ncc.py --host=adam-csr --get-running --named-filter openconfig-intf --params='{ "INTF_NAME" : "GigabitEthernet3"}'

./ncc/ncc.py --host=adam-3850 --do-edits native-intf-shutdown  --params '{"INTF_NAME" : "1/0/18"}'
./ncc/ncc.py --host=adam-3850 --get-running -x "/native/interface/GigabitEthernet[name='1/0/18']"
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-no-shut  --params '{"INTF_NAME" : "1/0/18"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-vlan-change  --params '{"INTF_NAME" : "1/0/19", "VLAN" : "20"}'
```
## vlan
```buildoutcfg
./ncc/ncc.py --host=adam-3850 --do-edits native-create-vlan  --params '{"VLAN" : "120"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/vlan"
./ncc/ncc.py --host=adam-3850 --do-edits native-delete-vlan  --params '{"VLAN" : "120"}'

```

## ACL

```buildoutcfg
./ncc/ncc.py --host=adam-3850 --do-edits native-create-acl --params '{"ACL_NAME": "canary_ip_in"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/ip/access-list/extended[name='canary_ip_in']"
./ncc/ncc.py --host=adam-3850 --do-edits native-delete-acl --params '{"ACL_NAME": "canary_ip_in"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-add-acl --params '{"INTF_NAME" : "1/0/18","ACL": "canary_ip_in"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-delete-acl --params '{"INTF_NAME" : "1/0/18","ACL": "canary_ip_in"}'
./ncc.py --host=adam-csr --get-oper -x '/native/ip/object-group'
```

## IP address / vlan change
Remember you can only configure a switchport in L3 mode if you "no switchport" it.
```buildoutcfg
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-no-switchport  --params '{"INTF_NAME" : "1/0/19"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/interface/GigabitEthernet[name='1/0/19']"
./ncc/ncc.py --host=adam-3850 --do-edits openconfig-intf-ip-address --params  '{"INTF_NAME" : "GigabitEthernet1/0/19", "IP_ADDR" : "12.12.12.2"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-switchport  --params '{"INTF_NAME" : "1/0/19"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-vlan-change  --params '{"INTF_NAME" : "1/0/19", "VLAN" : "20"}'
```

## QOS
```buildoutcfg
./ncc/ncc.py --host=adam-3850 --do-edits native-create-class-map --params '{"C_NAME" : "prm-EZQOS_12C#BROADCAST"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/policy/class-map[name='prm-EZQOS_12C#BROADCAST']"
./ncc/ncc.py --host=adam-3850 --do-edits native-create-policy-map --params '{"P_NAME": "prm-dscp#QUEUING_OUT","C_NAME" : "prm-EZQOS_12C#BROADCAST"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/policy/policy-map[name='prm-dscp#QUEUING_OUT']"
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-add-qos  --params '{"INTF_NAME" : "1/0/18","P_NAME": "prm-dscp#QUEUING_OUT"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-intf-delete-qos  --params '{"INTF_NAME" : "1/0/18","P_NAME": "prm-dscp#QUEUING_OUT"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-delete-policy-map --params '{"P_NAME": "prm-dscp#QUEUING_OUT"}'
./ncc/ncc.py --host=adam-3850 --do-edits native-delete-class-map --params '{"C_NAME" : "prm-EZQOS_12C#BROADCAST"}'
```

## OSPF
```buildoutcfg
./ncc/ncc.py --host=adam-3850 --do-edits native-router-ospf-add-network --params '{"ROUTER_ID" : "100", "NETWORK":"10.101.1.0", "MASK": "255.255.255.0"}'
./ncc/ncc.py --host=adam-3850 --get-oper -x "/native/router/ospf/network[ip='10.101.1.0']"
./ncc/ncc.py --host=adam-3850 --do-edits native-router-ospf-delete-network --params '{"ROUTER_ID" : "100", "NETWORK":"10.101.1.0","MASK": "255.255.255.0"}'
```
