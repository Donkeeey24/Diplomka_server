FROM python:3.11-slim

WORKDIR /app
COPY mqtt_fake_sender.py .
RUN pip install paho-mqtt

CMD ["python", "mqtt_fake_sender.py"]