"""InfluxDB Sensor Data Ingester

This script takes Sensor data from a source in JSON format, converts it to linedata (an InfluxDB format)
and pushes it to a destination. The source and destination configuration are controlled by a config file.

As implemented, this script works correctly when reading from MQTT and pushing to an InfluxDB API
write method (assumed to be an HTTP POST). Any other formats will need to be tested and 
might require code changes.
"""

import os
import sys
import argparse
import yaml
import time
from datetime import datetime
from dateutil import tz
from abc import ABC, abstractmethod
import json
import paho.mqtt.client as mqtt
import requests
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Number of messages processed before diplaying progress in silent mode
TIMING_INTERVAL = 500

def setup_client(host, port, topic, userdata):
    """Setup the MQTT client

    Parameters
    ----------
    host : str
        The host name
    port : int
        The MQTT port
    topic : str
        The MQTT topic to subscribe to containing JSON messages to ingest
    userdata : [str]
        Stateful data available when messages are received
    """

    client = mqtt.Client(userdata=userdata)
    client.on_message = on_message
    keepalive = 60
    client.connect(host, port, keepalive)
    client.subscribe(topic)
    return client

def on_message(client, userdata, message):
    """Callback method when an ingest message is received

    Parameters
    ----------
    client : obj
        An instantiated MQTT client
    userdata : [str]
        Stateful data available when messages are received
    message : obj
        The message received on the topic
    """

    msg = str(message.payload.decode('utf-8'))
    userdata['received'] += 1
    silent_mode = userdata['silent']
    ingested = userdata['ingested']
    if not silent_mode:
        logger.debug('Message #%d received: %s' % (userdata['received'],msg))
    json_data = json.loads(msg)
    if send_data_to_influx(json_data, silent_mode, userdata['config']):
        ingested += 1
    userdata['ingested'] = ingested
    if silent_mode and userdata['received'] % TIMING_INTERVAL == 0:
        now = datetime.now()
        took_seconds = (now - userdata['last_datetime']).total_seconds()
        ingest_per_second = TIMING_INTERVAL / took_seconds
        userdata['last_datetime'] = now
        logger.info('%s Received: %d, Ingested: %d, Took: %d secs, Rate (per sec): %.2f' % (now,userdata['received'],userdata['ingested'],took_seconds,ingest_per_second))

def is_successful_ingest(response):
    """Was the ingested successful?

    Parameters
    ----------
    response : obj
        The response object from the HTTP request
    
    Returns
    -------
    bool
        True if ingest was successful else false
    """

    return response.status_code == 204

def send_data_to_influx(json_data, silent_mode, config):
    """Send the received data to Influx

    Parameters
    ----------
    json_data : obj
        The received JSON data as a Python object
    silent_mode : bool
        True if we are in slinet mode, which means we only display progress data accoring to the TIMING_INTERVAL
    config : dict
        The configuration extracted from the passed in config file

    Returns
    -------
    bool
        Returns True if data was sucessfuly ingested

    Raises
    ------
    SystemExit
        When ingest into Influx has a RequestException
    """

    line_data = convert_json_to_linedata(json_data, config)
    api_url = config['destination']['influxdb']['api_endpoint']
    org = config['destination']['influxdb']['org']
    bucket = config['destination']['influxdb']['bucket']
    precision = config['destination']['influxdb']['precision']
    token = config['destination']['influxdb']['token']
    url = '%s?org=%s&bucket=%s&precision=%s' % (api_url, org, bucket, precision)
    header = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": "Token %s" % (token) }

    if not silent_mode:
        logger.debug('POSTing to %s linedata %s' % (url,line_data))
    
    try:
        # Send data to InfluxDB
        response = requests.post(url,data=line_data, headers=header, verify=False)
    except requests.exceptions.RequestException as e:
        logger.exception(e)
        raise SystemExit(e)

    if not silent_mode:
        logger.debug('API response: %d %s' % (response.status_code, response.reason))
    return is_successful_ingest(response)

def convert_json_to_linedata(json_data, config):
    """Convert the provided JSON data in Python object format into InfluxDb liendata format

    Parameters
    ----------
    json_data : obj
        JSON sensor data as a Python object
        eg. {"TIMESTAMP": "2020-04-27 11:46:24.922982", "RECORD": 44, "Station": "DummyRiverWQ", "LoggerBattV": 12.7, "EXO_TempC": 24.64, "EXO_pH": 6.73, "EXO_DOPerSat": 22.05, "EXO_TurbNTU": 28.45, "EXO_Depthm": 1.558}
    config : dict
        The configuration extracted from the passed in config file
    
    Returns
    -------
    str
        The sensor data in InfluxDb linedata format
        eg. sensors,station=DummyRiverWQ RECORD=44,LoggerBattV=12.7,EXO_TempC=24.64,EXO_pH=6.73,EXO_TurbNTU=28.45,EXO_Depthm=1.558 1556896326
    """

    # IMPORTANT! All incoming JSON messages must contain a 'Station' and a 'TIMESTAMP' field
    station_name = json_data['Station']
    timestamp = json_data['TIMESTAMP']

    # Convert the TIMESTAMP to Influx's required Unix timestamp format, taking timezones into account
    from_zone = tz.gettz(config['source']['timezone'])
    to_zone = tz.gettz(config['destination']['timezone'])
    from_dt = datetime.strptime(timestamp,config['source']['timestamp_format'])
    from_dt = from_dt.replace(tzinfo=from_zone)
    to_dt = from_dt.astimezone(to_zone)
    timestamp_nano = '{0:.0f}'.format(to_dt.timestamp() * 1000000)

    # Append the fields together into linedata format
    fields = ','.join([k + '=' + str(json_data[k]) for k in json_data if k not in ['TIMESTAMP','Station']])
    line_data = 'sensors,station=%s %s %s' % (station_name, fields, timestamp_nano)
    return line_data

def main(arguments):
    """Main method"""

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--configfile', help="Config file")
    parser.add_argument('--silent', action='store_true', help="Silent mode")
    args = parser.parse_args(arguments)

    if args.configfile:
        with open(args.configfile) as config_file:
            try:
                config = yaml.safe_load(config_file)
            except yaml.YAMLError as exc:
                logger.exception(exc)
    else:
        logger.error('Config file must be provided')

    if not config:
        sys.exit(1)

    if args.silent:
        logger.info('SILENT mode')
        logging.getLogger().setLevel(logging.ERROR)
        silent_mode = True
    else:
        silent_mode = False

    if config['source']['mqtt']:
        host = config['source']['mqtt']['hostname']
        port = config['source']['mqtt']['port']
        topic = config['source']['mqtt']['topic']
        userdata = {'config': config, 'silent': silent_mode, 'received': 0, 'ingested': 0, 'last_datetime': datetime.now()}
        logger.info('Waiting for data from MQTT %s:%s on %s' % (host, port, topic))
        mqtt_client = setup_client(host, port, topic, userdata)

        # Kick off MQTT listening loop
        mqtt_client.loop_forever()
        logger.info('Exited MQTT listening loop')

    else:
        logger.info('No source configured. Exiting.')

    logger.info('Exiting program')
    
if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:
        logger.exception(exc)
        sys.exit(1)
