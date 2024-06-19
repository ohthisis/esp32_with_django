# models.py
from django.db import models

class DHT22Data(models.Model):
    temC = models.FloatField()
    humi = models.FloatField()
    timestamp = models.DateTimeField()

class MQ135Data(models.Model):
    value = models.FloatField()
    quality = models.CharField(max_length=50)
    timestamp = models.DateTimeField()

class PMValueData(models.Model):
    PM_1p0 = models.FloatField()
    PM_2p5 = models.FloatField()
    PM_4p0 = models.FloatField()
    PM_10p0 = models.FloatField()
    quality = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
