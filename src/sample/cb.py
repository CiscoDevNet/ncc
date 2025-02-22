#
# Simple sample module showing a way to register a callback
# dynamically. This is the same as in ncc-establish-subscription.py.
#
from lxml import etree
import json
import jxmlease

#
# If we need to do any pre-analysis based on xpaths that will be
# subscribed to.
#
def init(xpaths):
    pass


def callback(notif):
    print('-->>')
    print('Event time      : %s' % notif.event_time)
    print('Subscription Id : %d' % notif.subscription_id)
    print('Type            : %d' % notif.type)
    print('Data            :')
    j = jxmlease.parse(notif.datastore_xml)
    print(json.dumps(j, indent=2, sort_keys=True))
    print('<<--')


def errback(notif):
    pass
    
