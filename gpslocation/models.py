from django.db import models

from broker.providers.decoder import DecoderProvider

decoders = DecoderProvider.get_plugins()
DECODER_HANDLER_CHOICES = [(f'{a.app}.{a.name}', f'{a.app}.{a.name}') for a in decoders]


class Trackpoint(models.Model):
    datalogger = models.ForeignKey('broker.Datalogger', on_delete=models.CASCADE)
    lat = models.FloatField()
    lon = models.FloatField()
    alt = models.FloatField(blank=True, null=True)
    acc = models.FloatField(blank=True, null=True)
    vac = models.FloatField(blank=True, null=True)
    vel = models.FloatField(blank=True, null=True)
    batt = models.FloatField(blank=True, null=True)
    conn = models.CharField(max_length=16, blank=True)
    tid = models.CharField(max_length=16, blank=True)
    time = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('datalogger', 'time')

    def __str__(self):
        return f'{self.time.isoformat()},{self.lat},{self.lon} {self.datalogger}'
