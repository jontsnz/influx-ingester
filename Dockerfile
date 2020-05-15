FROM python:alpine3.7

ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ARG config_file
ENV CONFIG_FILE=$config_file
RUN echo "CONFIG_FILE: $config_file"

ARG silent_flag
ENV SILENT_FLAG=$silent_flag
RUN echo "SILENT_FLAG: $silent_flag"

CMD ["sh", "-c", "echo $SILENT_FLAG; python influx-ingester.py -c $CONFIG_FILE $SILENT_FLAG"]
