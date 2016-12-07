'''
CP Halo Modular Input Script

Copyright (C) 2012 Splunk, Inc.
All Rights Reserved
Copyright (C) 2013 Cloud Passage, Inc.
All Rights Reserved

'''

import sys,logging
import xml.dom.minidom, xml.sax.saxutils
import json, md5
import os.path
import datetime
import time
from event import Event
import cpapi, cputils

#set up logging
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
#with zero args , should go to STD ERR
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>CloudPassage Halo events</title>
    <description>Stream CloudPassage Halo events using the Halo API</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>
            <arg name="auth_id">
                <title>Key ID</title>
                <description>The ID of the account, used for authorization</description>
            </arg>
            <arg name="auth_secret">
                <title>Key Secret</title>
                <description>The Key Secret of the account, used for authorization</description>
            </arg>
            <arg name="endpoint">
                <title>The Portal Endpoint URL</title>
                <description>The URL of the Halo Portal (including port, if not default)</description>
            </arg>
            <arg name="startdate">
                <title>The Earliest Event Date/Time</title>
                <description>Date/Time (ISO-8601) for earliest event to be fetched</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="proxy">
                <title>HTTP Proxy</title>
                <description>A proxy for HTTP connections, if required</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def isPresent(obj,key):
    if (key in obj):
        return len(obj[key]) > 0
    else:
        return False

def do_validate():
    config = get_validation_config()
    #TODO
    #if error , print_validation_error & sys.exit(2)
    if not isPresent(config,'auth_id'):
        print_validation_error("Missing Authorization ID")
        sys.exit(2)
    if not isPresent(config,'auth_secret'):
        print_validation_error("Missing Authorization Secret")
        sys.exit(2)
    if not isPresent(config,'endpoint'):
        print_validation_error("Missing Portal/Endpoint URL")
        sys.exit(2)
    if isPresent(config,'startdate'):
        timestamp = config['startdate']
        (ok, msg) = cputils.verifyISO8601(timestamp)
        if (not ok):
            print_validation_error("start date: %s" % msg)
            sys.exit(2)
    # should do more validation on config['endpoint'], like making sure it's a proper URL

def do_run():
    config = get_input_config()
    #TODO , poll for data and print output to STD OUT
    #if error , logging.error & sys.exit(2)
    url = config['name']
    apiURL = config['endpoint']
    authKeyID = config['auth_id']
    proxy = None
    if ('proxy' in config) and (config['proxy'] != ''):
        proxy = config['proxy']
        logging.info("cphalo: proxy=%s" % proxy)
    else:
        logging.info("cphalo: no proxy")
    authSecret = config['auth_secret']
    logging.info("cphalo: apiURL=%s" % apiURL)
    apiCon = cpapi.CPAPI()
    (apiCon.key_id, apiCon.secret) = (authKeyID, authSecret)
    if apiURL.endswith('/'):
        apiURL = apiURL[:-1] # strip off final / if present
    apiCon.base_url = apiURL
    if (proxy != None):
        apiCon.setProxy(proxy)
    logging.info("cphalo: config= %s" % config)
    timestamp = load_checkpoint(config, url)
    logging.info("cphalo: load_checkpoint= %s" % timestamp)

    if not timestamp:
        if 'startdate' in config:
            (ok, msg) = cputils.verifyISO8601(config['startdate'])
            if not ok:
                logging.error("Formatting Error -- start date: %s" % msg)
                sys.exit(1)
            timestamp = config['startdate']
        else:
            timestamp = datetime.datetime.today().date() - datetime.timedelta(days=90)

    logging.info("cphalo: startingTimestamp=%s" % timestamp)
    timestamp = processEventBatches(timestamp, authKeyID, authSecret)
    logging.info("cphalo: lastEventTimestamp=%s" % timestamp)
    if (timestamp != None):
        # # timestamp = cputils.getNowAsISO8601() # use this for current system time
        # if type(timestamp) is datetime.date:
        #     timeObj = timestamp
        # else:
        #     timeObj = cputils.strToDate(timeObj)
        # if (timeObj != None):
        #     twoMillisecond = datetime.timedelta(0,0,2000)
        #     newTimeObj = timeObj + twoMillisecond
        #     timestamp = cputils.formatTimeAsISO8601(newTimeObj)
        logging.info("cphalo: checkpointTimestamp=%s" % timestamp)
        save_checkpoint(config,url,timestamp)
    else:
        logging.info("cphalo: no events, not updating checkpoint")

def processEventBatches(connLastTimestamp, authKeyID, authSecret):
    event = Event(authKeyID, authSecret)
    print "<stream>"
    logging.info("cphalo: processEventBatches_first %s" % type(connLastTimestamp))

    initial_event_id = event.latest_event("1", "", "1")["events"][0]["id"]
    flag = True
    while flag:
        try:
            batched = event.batch(connLastTimestamp)
        except TypeError:
            return connLastTimestamp
        start_date, connLastTimestamp = event.loop_date(batched, connLastTimestamp)
        logging.info("cphalo: processEventBatches")
        formatEvents(batched)
        if event.id_exists_check(batched, initial_event_id):
            flag = False
    print "</stream>"
    return connLastTimestamp

def formatEvents(eventList):
    """ Formats a list of events according to the user's settings.

        We can format in JSON, text, or key-value pairs. Once the
        event is formatted, it's passed to writeEventString() to be
        written to the destination.
    """
    firstEv = True
    for ev in eventList:
        evStr = json.dumps(ev)
        xmlStr = "<event><data>%s</data></event>" % xml.sax.saxutils.escape(evStr)
        print xmlStr
        if (firstEv):
            firstEv = False
            logging.info("cphalo: first event in batch: %s" % xmlStr)


# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

# prints XML stream
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % xml.sax.saxutils.escape(s)

# prints XML stream
def print_xml_multi_instance_mode(s,stanza):
    print "<stream><event stanza=""%s""><data>%s</data></event></stream>" % stanza,xml.sax.saxutils.escape(s)

# prints simple stream
def print_simple(s):
    print "%s\n" % s

def usage():
    print "usage: %s [--scheme|--validate-arguments]"
    logging.error("Incorrect Program Usage")
    sys.exit(2)

def do_scheme():
    print SCHEME

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."


    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

def get_encoded_file_path(config, url):
    # encode the URL (simply to make the file name recognizable)
    name = ""
    for i in range(len(url)):
        if url[i].isalnum():
            name += url[i]
        else:
            name += "_"
    # MD5 the URL
    m = md5.new()
    m.update(url)
    name += "_" + m.hexdigest()
    return os.path.join(config["checkpoint_dir"], name)

# simply creates a checkpoint file indicating that the URL was checkpointed
def save_checkpoint(config, url, timestamp):
    chk_file = get_encoded_file_path(config, url)
    # just create an empty file name
    logging.info("Checkpointing url=%s file=%s time=%s", url, chk_file, timestamp)
    f = open(chk_file, "w")
    print >> f, "%s" % timestamp
    f.close()

# returns true if the checkpoint file exists
def load_checkpoint(config, url):
    chk_file = get_encoded_file_path(config, url)
    s = None
    # try to open this file
    try:
        f = open(chk_file, "r")
        s = f.read()
        if (s != None):
            s.strip()
        f.close()
    except:
        # assume that this means the checkpoint is not there
        return None
    return s

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

if __name__ == '__main__':

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        do_run()

    sys.exit(0)
