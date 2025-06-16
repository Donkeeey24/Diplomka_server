FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Spustí MQTT klienta na pozadí a FastAPI server v popředí
CMD ["sh", "-c", "python async_mqtt_client.py & uvicorn main:app --host 0.0.0.0 --port 8000"]