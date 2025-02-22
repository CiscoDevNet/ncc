#
# Simple sample module showing a way to register a callback
# dynamically. This is the same as in ncc-establish-subscription.py.
#
from lxml import etree
import json
import jxmlease
import redis
import time


#
# the redis connection
#
conn = redis.Redis()


#
# log an "event"
#
def log_items(rx_time, events):
    pipe = conn.pipeline(True)
    for event in events:
        id = conn.incr('cpu_usage:id')
        event['id'] = id
        event['timestamp'] = rx_time
        event_key = 'cpu_usage:{id}'.format(id=id)
        pipe.hmset(event_key, event)
        pipe.zadd('cpu_usage', str(id), rx_time)
    pipe.execute()


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
        cpu_usage_process = j["datastore-contents-xml"]["cpu-usage"]["cpu-utilization"]["cpu-usage-processes"]["cpu-usage-process"]
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



"""
Sample Event:

{
  "datastore-contents-xml": {
    "cpu-usage": {
      "cpu-utilization": {
        "cpu-usage-processes": {
          "cpu-usage-process": {
            "avg-run-time": "118",
            "five-minutes": "0",
            "five-seconds": "0",
            "invocation-count": "77552",
            "name": "PuntInject Keepalive Process",
            "one-minute": "0",
            "pid": "89",
            "total-run-time": "9212",
            "tty": "0"
          }
        },
        "five-minutes": "0",
        "five-seconds": "0",
        "five-seconds-intr": "0",
        "one-minute": "0"
      }
    }
  }
}
"""
