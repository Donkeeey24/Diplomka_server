import asyncio
import json
from gmqtt import Client as MQTTClient
import asyncpg
import datetime

BROKER_HOST = 'mosquitto'
BROKER_PORT = 1883
TOPIC = '/events'

# PostgreSQL connection settings
PG_HOST = 'postgres'
PG_PORT = 5432
PG_USER = 'postgres'
PG_PASSWORD = 'postgres'
PG_DATABASE = 'postgres'

class MyMQTTClient:

    def __init__(self, client_id):
        self.client = MQTTClient(client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.pg_pool = None

    async def connect(self):
        await self.client.connect(BROKER_HOST, BROKER_PORT)

    async def subscribe(self, topic):
        self.client.subscribe(topic)

    def on_connect(self, client, flags, rc, properties):
        print(f'Connected with result code {rc}')

    async def store_message(self, message):
        if self.pg_pool is None:
            print("No database pool, skipping DB insert.")
            return
        try:
            obj = json.loads(message)
            # Parse ISO datetime string to Python datetime object
            dt = datetime.datetime.fromisoformat(obj["time"])
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sensor_data (meteo_uuid, sensor_uuid, value, time) VALUES ($1, $2, $3, $4)",
                    obj["meteo_UUID"], obj["sensor_UUID"], obj["value"], dt
                )
            print(f"Message inserted to DB: {obj}")
        except Exception as e:
            print(f"Error inserting message: {e}")

    def on_message(self, client, topic, payload, qos, properties):
        print(f'Received message on {topic}: {payload.decode()}')
        asyncio.create_task(self.store_message(payload.decode()))

    def on_disconnect(self, client, packet, exc=None):
        print(f'Disconnected from MQTT Broker')

    def on_subscribe(self, client, mid, qos, properties):
        print(f'Subscribed to {TOPIC}')

    async def start(self):
        try:
            self.pg_pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                user=PG_USER,
                password=PG_PASSWORD,
                database=PG_DATABASE,
                min_size=1,
                max_size=5
            )
            print("Connected to PostgreSQL.")
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            self.pg_pool = None

        await self.connect()
        await self.subscribe(TOPIC)
        await asyncio.Event().wait()

async def main():
    mqtt_client = MyMQTTClient(client_id='my-client-id')
    await mqtt_client.start()

if __name__ == '__main__':
    asyncio.run(main())