"""InfluxDB Water Quality Sensor Ingester
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

def setup_client(host, port, topic, userdata):
    client = mqtt.Client(userdata=userdata)
    client.on_message = on_message
    keepalive = 60
    client.connect(host, port, keepalive)
    client.subscribe(topic)
    return client

def on_message(client, userdata, message):
    msg = str(message.payload.decode('utf-8'))
    silent_mode = userdata['silent']
    if not silent_mode:
        print('message received ' , msg)
    json_data = json.loads(msg)
    send_data_to_influx(json_data, silent_mode, userdata['config'])

def send_data_to_influx(json_data, silent_mode, config):
    line_data = convert_json_to_linedata(json_data, config)
    api_url = config['destination']['influxdb']['api_endpoint']
    org = config['destination']['influxdb']['org']
    bucket = config['destination']['influxdb']['bucket']
    precision = config['destination']['influxdb']['precision']
    token = config['destination']['influxdb']['token']
    url = '%s?org=%s&bucket=%s&precision=%s' % (api_url, org, bucket, precision)
    header = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": "Token %s" % (token) }
    if not silent_mode:
        print('POSTing to %s linedata %s' % (url,line_data))
    try:
        response = requests.post(url,data=line_data, headers=header, verify=False)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    if not silent_mode:
        print('API response: %d %s' % (response.status_code, response.reason))

def convert_json_to_linedata(json_data, config):
    # example json:     {"TIMESTAMP": "2020-04-27 11:46:24.922982", "RECORD": 44, "Station": "DummyRiverWQ", "LoggerBattV": 12.7, "EXO_TempC": 24.64, "EXO_pH": 6.73, "EXO_DOPerSat": 22.05, "EXO_TurbNTU": 28.45, "EXO_Depthm": 1.558}
    # example limedata: sensors,station=DummyRiverWQ RECORD=44,LoggerBattV=12.7,EXO_TempC=24.64,EXO_pH=6.73,EXO_TurbNTU=28.45,EXO_Depthm=1.558 1556896326
    station_name = json_data['Station']
    timestamp = json_data['TIMESTAMP']
    from_zone = tz.gettz(config['source']['timezone'])
    to_zone = tz.gettz(config['destination']['timezone'])
    from_dt = datetime.strptime(timestamp,config['source']['timestamp_format'])
    from_dt = from_dt.replace(tzinfo=from_zone)
    to_dt = from_dt.astimezone(to_zone)
    timestamp_nano = '{0:.0f}'.format(to_dt.timestamp() * 1000000)
    fields = ','.join([k + '=' + str(json_data[k]) for k in json_data if k not in ['TIMESTAMP','Station']])
    line_data = 'sensors,station=%s %s %s' % (station_name, fields, timestamp_nano)
    return line_data

def main(arguments):

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
                print(exc)
    else:
        print('Config file must be provided')

    if args.silent:
        print('SILENT mode')
        silent_mode = True
    else:
        silent_mode = False

    if config['source']['mqtt']:
        host = config['source']['mqtt']['hostname']
        port = config['source']['mqtt']['port']
        topic = config['source']['mqtt']['topic']
        print('Waiting for data from MQTT %s:%s on %s' % (host, port, topic))
        userdata = {'config': config, 'silent': silent_mode}
        mqtt_client = setup_client(host, port, topic, userdata)
    else:
        print('No MQTT source configured. Exiting.')

    if mqtt_client:
        mqtt_client.loop_forever()
        print('Exited MQTT listening loop')

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
