from django.db import models

# Create your models here.


class SensorReading(models.Model):
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.FloatField()
    light = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sensor reading at {self.timestamp}"