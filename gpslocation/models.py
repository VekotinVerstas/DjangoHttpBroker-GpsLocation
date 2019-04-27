from django.db import models
# from django.contrib.gis.db import models
# from django.contrib.gis.geos import Point
from django.contrib.auth.models import User
from broker.providers.decoder import DecoderProvider

decoders = DecoderProvider.get_plugins()
DECODER_HANDLER_CHOICES = [(f'{a.app}.{a.name}', f'{a.app}.{a.name}') for a in decoders]


class Trackpoint(models.Model):
    """
    Contains all gathered data of single GPS measurement.
    Fields follow mostly elements in GPX standard's <trkpt> element.
    """
    # uid = models.CharField(max_length=40, unique=True, db_index=True, default=get_uid, editable=False)
    datalogger = models.ForeignKey('broker.Datalogger', on_delete=models.CASCADE)
    user = models.ForeignKey(User, db_index=True, blank=True, null=True, on_delete=models.CASCADE)
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)
    # For convenience, lat and lon in numeric form too
    lat = models.FloatField()  # degrees (°) -90.0 - 90.0
    lon = models.FloatField()  # degrees (°) -180.0 - 180.0
    speed = models.FloatField(blank=True, null=True)  # meters per second (m/s)
    course = models.FloatField(blank=True, null=True)  # degrees (°) 0.0 - 360.0
    ele = models.FloatField(blank=True, null=True)  # meters (m)
    # Horizontal and Vertical accuracy (pre-calculated by some GPS chips or software)
    hacc = models.FloatField(blank=True, null=True)
    vacc = models.FloatField(blank=True, null=True)
    # See Dilution of precision at
    # http://en.wikipedia.org/wiki/Dilution_of_precision_%28GPS%29
    hdop = models.FloatField(blank=True, null=True)  # horizontal
    vdop = models.FloatField(blank=True, null=True)  # vertical
    pdop = models.FloatField(blank=True, null=True)  # positional (3D)
    tdop = models.FloatField(blank=True, null=True)  # time
    # Satellites in view and used
    sat = models.IntegerField(blank=True, null=True)
    satavail = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # See http://postgis.refractions.net/documentation/manual-1.5/ch04.html#PostGIS_GeographyVSGeometry
    # geography = models.PointField(geography=True, editable=True)

    class Meta:
        unique_together = ('datalogger', 'time')

    def __str__(self):
        return f'{self.time.isoformat()},{self.lat},{self.lon} {self.datalogger}'
