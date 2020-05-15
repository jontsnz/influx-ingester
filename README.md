# Influx Ingester Project

Ingests water quality data from a configurable source and pushes to Influx

## Getting Started

### Prerequisites

You will need InfluxDB running. YOu will also need docker and docker-compose if you want to use the pre-configured setups.

### Starting the MQTT ingester ONLY using docker (when MQTT already running)

Note that in the example below we rely on the MQTT instance and the InfluxDB instance being on the same docker network, with the MQTT container named ```mosquitto``` and the InfluxDB container named ```influxdb```. Config files are held external to the container and accessed from the container via the bound mount at ```/influx-ingester/config/```.

```bash
# Build the container
docker build --pull --rm -t influx-ingester:latest "."

# In verbose mode
docker run -it --name influx-ingester-dummy-mqtt --network="influx-test_default" --mount type=bind,source=/Users/john/coding/sandbox/iot/influx2/influx-ingester/config,destination=/influx-ingester/config -e CONFIG_FILE="/influx-ingester/config/dummy-mqtt-network.yaml" influx-ingester:latest

# In silent mode
docker run -it --name influx-ingester-dummy-mqtt --network="influx-test_default" --mount type=bind,source=/Users/john/coding/sandbox/iot/influx2/influx-ingester/config,destination=/influx-ingester/config -e CONFIG_FILE="/influx-ingester/config/dummy-mqtt-network.yaml" -e SILENT_FLAG="--silent" influx-ingester:latest
```

### Start the MQTT ingester using docker compose

Use ```docker-compose``` to start up the MQTT influx ingester.

```bash
# First the dummy sensor ingester...
docker-compose -f docker-compose-dummy-mqtt.yml build
docker-compose -f docker-compose-dummy-mqtt.yml up -d

# Now the CR1000 ingester...
docker-compose -f docker-compose-cr1000-mqtt.yml build
docker-compose -f docker-compose-cr1000-mqtt.yml up -d
```

### Runing the ingester manually

You can run the ingester directly from your Python virtual environment. You will need to ensure you already have the ingestion source running (eg. MQTT):

```bash
pip install -r requirements.txt

python influx-ingester.py -c config/dummy-mqtt-localhost.yaml
```
