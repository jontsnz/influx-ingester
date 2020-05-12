# Influx Ingester Project

Ingests water quality data from a configurable source and pushes to Influx

## Getting Started

### Prerequisites

You will need InfluxDB running. YOu will also need docker and docker-compose if you want to use the pre-configured setups.

### Starting the MQTT ingester ONLY using docker (when MQTT already running)

Note that this approach relies on using the localhost network (which is running MQTT and InfluxDB) so the config files must refer to localhost as 127.0.0.1. Note also that the config file is built into the container image, so any config changes must be made before building the image.

```bash
docker build --pull --rm -f "Dockerfile" -t influx-ingester:latest "."

docker run -it --name influx-ingester-dummy-mqtt --network="host" -e CONFIG_FILE="./influx-ingester-dummy-mqtt-config.yaml" influx-ingester:latest
```

### Start the MQTT ingester using docker compose

Use ```docker-compose``` to start up the MQTT influx ingester.

```bash
# First the dummy sensor ingester...
docker-compose -f docker-compose-dummy-mqtt.yaml build
docker-compose -f docker-compose-dummy-mqtt.yaml up -d

# Now the CR1000 ingester...
docker-compose -f docker-compose-cr1000-mqtt.yaml build
docker-compose -f docker-compose-cr1000-mqtt.yaml up -d
```

### Runing the ingester manually

You can run the ingester directly from your Python virtual environment. You will need to ensure you already have the ingestion source running (eg. MQTT):

```bash
pip install -r requirements.txt

python influx-ingester.py -c influx-ingester-mqtt-config.yaml
```
