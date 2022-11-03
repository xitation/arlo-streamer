import base64 as b64
import json
import asyncio_mqtt as aiomqtt
from aiostream import stream
import logging
from decouple import config
import asyncio

MQTT_BROKER = config('MQTT_BROKER')
MQTT_RECONNECT_INTERVAL = config('MQTT_RECONNECT_INTERVAL', default=5)
MQTT_TOPIC_PICTURE = config('MQTT_TOPIC_PICTURE', default='arlo/picture')
MQTT_TOPIC_LOCATION = config('MQTT_TOPIC_LOCATION', default='arlo/location')
MQTT_TOPIC_CONTROL = config('MQTT_TOPIC_CONTROL', default='arlo/control/{name}')


async def mqtt_client(cameras):
    while True:
        try:
            async with aiomqtt.Client(MQTT_BROKER) as client:
                logging.info(f"MQTT client connected to {MQTT_BROKER}")
                await asyncio.gather(
                    pic_streamer(client, cameras),
                    mqtt_reader(client, cameras)
                    )
        except aiomqtt.MqttError as error:
            logging.info(f'MQTT "{error}". reconnecting.')
            await asyncio.sleep(MQTT_RECONNECT_INTERVAL)


async def pic_streamer(client, cameras):
    pics = stream.merge(*[c.get_pictures() for c in cameras])
    async with pics.stream() as streamer:
        async for name, data in streamer:
            await client.publish(
                MQTT_TOPIC_PICTURE.format(name=name),
                payload=json.dumps({
                    "filename": "test.jpg",
                    "payload": b64.b64encode(data).decode("utf-8")
                    }))


async def mqtt_reader(client, cameras):
    cams = {MQTT_TOPIC_CONTROL.format(name=c.name): c for c in cameras}
    async with client.unfiltered_messages() as messages:
        for name, _ in cams.items():
            await client.subscribe(name)
        async for message in messages:
            if message.topic in cams:
                await cams[name].mqtt_control(
                    message.payload.decode("utf-8"))