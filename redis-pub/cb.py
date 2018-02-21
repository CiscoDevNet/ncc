#
# Simple sample module showing a way to register a callback
# dynamically. This is the same as in ncc-establish-subscription.py.
#
import json
import jxmlease
import redis
import time
import re


#
# the redis connection
#
conn = redis.Redis()

#
# Match only digits
#
d = re.compile('^\d+$')

#
# Publish a stats event in JSON on a Redis channel called 'yangpush'.
#
def log_items(rx_time, events):
    for event in events:
        id = conn.incr('cpu_usage:id')
        for k, v in event.items():
            if isinstance(v, str) and d.match(v):
                event[k] = int(v)
        event['id'] = id
        event['timestamp'] = rx_time
        event_json = json.dumps(event)
        # print(event_json)
        conn.publish('yangpush', event_json)


#
# If we need to do any pre-analysis based on xpaths that will be
# subscribed to.
#
def init(xpaths):
    pass


#
# the callback for subscription events
#
def callback(notif):
    rx_time = time.time()
    print('-->>')
    print('Event time      : %s' % notif.event_time)
    print('Subscription Id : %d' % notif.subscription_id)
    print('Type            : %d' % notif.type)
    j = jxmlease.parse(notif.datastore_xml)
    try:
        #cpu_usage_process = j["datastore-contents-xml"]["cpu-usage"]["cpu-utilization"]["cpu-usage-processes"]["cpu-usage-process"]
        cpu_usage_process = j.get(
            "datastore-contents-xml").get(
                "cpu-usage").get(
                    "cpu-utilization").get(
                        "cpu-usage-processes").get(
                            "cpu-usage-process")
        if isinstance(cpu_usage_process, dict):
            log_items(rx_time, [cpu_usage_process])
        elif isinstance(cpu_usage_process, list):
            log_items(rx_time, cpu_usage_process)
        else:
            print('Event is unknown!')
    except e:
        print(e)
    print('<<--')


#
# the (currently unused) error callback
#
def errback(notif):
    pass
