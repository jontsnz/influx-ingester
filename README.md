# Influx Ingester Project

Ingests water quality data from an MQTT source and pushes to Influx

## Getting Started

### Prerequisites

You will need MQTT and InfluxDB running

### Starting the ingester directly

You can run the ingester directly from your Python virtual environment:

```bash
pip install -r requirements.txt

python influx-ingester.py -c influx-ingester-config.yaml
```
