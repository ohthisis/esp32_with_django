import json
import asyncio
from datetime import datetime, timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import DHT22Data, MQ135Data, PMValueData

class SensorDataConsumer(AsyncWebsocketConsumer):
    data_timeout = 10 

    async def connect(self):
        self.group_name = "sensor_data"
        await self.accept()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        print(f"WebSocket connected: {self.channel_name}")
        self.current_row_ids = {'DHT22': None, 'MQ135': None, 'pmValue': None}
        self.latest_values = {
            'DHT22': {'temC': None, 'humi': None},
            'MQ135': {'value': None, 'quality': None},
            'pmValue': {'PM_1p0': None, 'PM_2p5': None, 'PM_4p0': None, 'PM_10p0': None, 'quality': None}
        }
        self.last_received_time = datetime.now()
        self.last_save_time = self.last_received_time
        asyncio.create_task(self.check_data_timeout())  
        asyncio.create_task(self.hourly_save())  

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data): 
        try:
            data = json.loads(text_data)
            current_time = datetime.now()

            # Process DHT22 data
            if 'DHT22' in data:
                temC = data['DHT22'].get('temC')
                humi = data['DHT22'].get('humi')
                if temC is not None and humi is not None:
                    self.latest_values['DHT22'] = {'temC': temC, 'humi': humi}
                    await self.save_dht22_data(temC, humi, current_time)
                    await self.send_to_group('DHT22', {'temC': temC, 'humi': humi}, current_time)

            # Process MQ135 data
            if 'mq135' in data:
                mq_value = data['mq135'].get('value')
                quality = data['mq135'].get('quality')
                if mq_value is not None and quality is not None:
                    self.latest_values['MQ135'] = {'value': mq_value, 'quality': quality}
                    await self.save_mq135_data(mq_value, quality, current_time)
                    await self.send_to_group('MQ135', {'value': mq_value, 'quality': quality}, current_time)

            # Process PM Values
            if 'pmValue' in data:
                PM_1p0 = data['pmValue'].get('PM_1p0')
                PM_2p5 = data['pmValue'].get('PM_2p5')
                PM_4p0 = data['pmValue'].get('PM_4p0')
                PM_10p0 = data['pmValue'].get('PM_10p0')
                quality = data['pmValue'].get('quality')
                if all(v is not None for v in [PM_1p0, PM_2p5, PM_4p0, PM_10p0]) and quality is not None:
                    self.latest_values['pmValue'] = {'PM_1p0': PM_1p0, 'PM_2p5': PM_2p5, 'PM_4p0': PM_4p0, 'PM_10p0': PM_10p0, 'quality': quality}
                    await self.save_pm_value_data(PM_1p0, PM_2p5, PM_4p0, PM_10p0, quality, current_time)
                    await self.send_to_group('pmValue', {'PM_1p0': PM_1p0, 'PM_2p5': PM_2p5, 'PM_4p0': PM_4p0, 'PM_10p0': PM_10p0, 'quality': quality}, current_time)

            self.last_received_time = current_time  # Update last received time

        except (json.JSONDecodeError, ValueError) as e:
            await self.send_error_message(f"Invalid input format: {str(e)}")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
            await self.send_error_message("Internal server error")

    async def save_dht22_data(self, temC, humi, timestamp):
        latest_time = await self.get_latest_received_time('DHT22')
        if latest_time is None or (timestamp.year, timestamp.month, timestamp.day, timestamp.hour) != (latest_time.year, latest_time.month, latest_time.day, latest_time.hour):
            new_record = await sync_to_async(DHT22Data.objects.create)(
                temC=temC,
                humi=humi,
                timestamp=timestamp
            )
            self.current_row_ids['DHT22'] = new_record.id
        else:
            await sync_to_async(DHT22Data.objects.filter(id=self.current_row_ids['DHT22']).update)(
                temC=temC,
                humi=humi,
                timestamp=timestamp
            )

    async def save_mq135_data(self, value, quality, timestamp):
        latest_time = await self.get_latest_received_time('MQ135')
        if latest_time is None or (timestamp.year, timestamp.month, timestamp.day, timestamp.hour) != (latest_time.year, latest_time.month, latest_time.day, latest_time.hour):
            new_record = await sync_to_async(MQ135Data.objects.create)(
                value=value,
                quality=quality,
                timestamp=timestamp
            )
            self.current_row_ids['MQ135'] = new_record.id
        else:
            await sync_to_async(MQ135Data.objects.filter(id=self.current_row_ids['MQ135']).update)(
                value=value,
                quality=quality,
                timestamp=timestamp
            )

    async def save_pm_value_data(self, PM_1p0, PM_2p5, PM_4p0, PM_10p0, quality, timestamp):
        latest_time = await self.get_latest_received_time('pmValue')
        if latest_time is None or (timestamp.year, timestamp.month, timestamp.day, timestamp.hour) != (latest_time.year, latest_time.month, latest_time.day, latest_time.hour):
            new_record = await sync_to_async(PMValueData.objects.create)(
                PM_1p0=PM_1p0,
                PM_2p5=PM_2p5,
                PM_4p0=PM_4p0,
                PM_10p0=PM_10p0,
                quality=quality,
                timestamp=timestamp
            )
            self.current_row_ids['pmValue'] = new_record.id
        else:
            await sync_to_async(PMValueData.objects.filter(id=self.current_row_ids['pmValue']).update)(
                PM_1p0=PM_1p0,
                PM_2p5=PM_2p5,
                PM_4p0=PM_4p0,
                PM_10p0=PM_10p0,
                quality=quality,
                timestamp=timestamp
            )

    async def get_latest_received_time(self, sensor_type):
        if sensor_type == 'DHT22':
            latest_entry = await sync_to_async(DHT22Data.objects.last)()
        elif sensor_type == 'MQ135':
            latest_entry = await sync_to_async(MQ135Data.objects.last)()
        elif sensor_type == 'pmValue':
            latest_entry = await sync_to_async(PMValueData.objects.last)()
        else:
            return None

        return latest_entry.timestamp if latest_entry else None

    async def check_data_timeout(self):
        while True:
            if (datetime.now() - self.last_received_time).seconds > self.data_timeout:
                await self.send_no_data_message()
            await asyncio.sleep(1)

    async def send_no_data_message(self):
        await self.send(text_data=json.dumps({
            'status': 'no_data',
            'message': 'No data received from sensors.'
        }))

    async def hourly_save(self):
        while True:
            current_time = datetime.now()
            current_hour_start = current_time.replace(minute=0, second=0, microsecond=0)
            last_received_hour_start = self.last_received_time.replace(minute=0, second=0, microsecond=0)
        
            if current_hour_start != last_received_hour_start:
                await self.save_latest_data(self.last_received_time)
                self.last_save_time = current_time
        
            await asyncio.sleep(60)  # Check every minute

    @sync_to_async
    def save_latest_data(self, timestamp):
        for sensor_type, values in self.latest_values.items():
            if sensor_type == 'DHT22':
                temC = values['temC']
                humi = values['humi']
                if temC is not None and humi is not None:
                    if self.current_row_ids['DHT22'] is None:
                        new_record = DHT22Data.objects.create(temC=temC, humi=humi, timestamp=timestamp)
                        self.current_row_ids['DHT22'] = new_record.id
                    else:
                        DHT22Data.objects.filter(id=self.current_row_ids['DHT22']).update(temC=temC, humi=humi, timestamp=timestamp)
            elif sensor_type == 'MQ135':
                mq_value = values['value']
                quality = values['quality']
                if mq_value is not None and quality is not None:
                    if self.current_row_ids['MQ135'] is None:
                        new_record = MQ135Data.objects.create(value=mq_value, quality=quality, timestamp=timestamp)
                        self.current_row_ids['MQ135'] = new_record.id
                    else:
                        MQ135Data.objects.filter(id=self.current_row_ids['MQ135']).update(value=mq_value, quality=quality, timestamp=timestamp)
            elif sensor_type == 'pmValue':
                PM_1p0 = values['PM_1p0']
                PM_2p5 = values['PM_2p5']
                PM_4p0 = values['PM_4p0']
                PM_10p0 = values['PM_10p0']
                quality = values['quality']
                if all(v is not None for v in [PM_1p0, PM_2p5, PM_4p0, PM_10p0]) and quality is not None:
                    if self.current_row_ids['pmValue'] is None:
                        new_record = PMValueData.objects.create(PM_1p0=PM_1p0, PM_2p5=PM_2p5, PM_4p0=PM_4p0, PM_10p0=PM_10p0, quality=quality, timestamp=timestamp)
                        self.current_row_ids['pmValue'] = new_record.id
                    else:
                        PMValueData.objects.filter(id=self.current_row_ids['pmValue']).update(PM_1p0=PM_1p0, PM_2p5=PM_2p5, PM_4p0=PM_4p0, PM_10p0=PM_10p0, quality=quality, timestamp=timestamp)

    async def send_to_group(self, sensor_type, value, timestamp):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'sensor_data_message',
                'value': value,
                'timestamp': timestamp.isoformat(),
                'sensor_type': sensor_type
            }
        )

    async def sensor_data_message(self, event):
        await self.send(text_data=json.dumps({
            'value': event['value'],
            'timestamp': event['timestamp'],
            'sensor_type': event['sensor_type']
        }))

    async def send_error_message(self, message):
        await self.send(text_data=json.dumps({
            'status': 'error',
            'message': message
        }))
