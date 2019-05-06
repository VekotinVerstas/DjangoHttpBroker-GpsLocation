import datetime
import logging
import sys

import pytz
import gpxpy
import gpxpy.gpx
from dateutil.parser import parse
from django.core.management.base import BaseCommand

from gpslocation.models import Trackpoint

logger = logging.getLogger('gpslocation')

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def convert_to_seconds(s):
    """
    Convert string like 500s, 120m, 24h, 5d, 16w to equivalent number of seconds
    :param str s: time period length
    :return: seconds
    """
    return int(s[:-1]) * UNITS[s[-1]]


def create_datetime(date_str, hourly=True):
    if date_str is None:
        d = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    else:
        d = parse(date_str)
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        raise ValueError('Start and end time strings must contain timezone information')
    if hourly:
        d = d.replace(minute=0, second=0, microsecond=0)
    return d


def create_gpx_file(trkpts):
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    # prev_time = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(0))
    prev_time = trkpts[0].time
    for trkpt in trkpts:
        if (trkpt.time - prev_time).seconds > 5 * 60:
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(trkpt.lat, trkpt.lon, time=trkpt.time, elevation=trkpt.ele))
        prev_time = trkpt.time
    return gpx.to_xml()


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('--starttime', help='Endtime in YYYY-mm-ddTHH:MM:SSZ format. Default is endtime-7d')
        parser.add_argument('--endtime', help='Endtime in YYYY-mm-ddTHH:MM:SSZ format. Default is current time')
        parser.add_argument("-tl", "--timelength", help="Length of time for dump [e.g. 500s, 10m, 6h, 5d, 4w]",
                            default="1d")
        parser.add_argument('-o', '--outformat', default='gpx', choices=['gpx', 'csv', ], help='Output format')
        parser.add_argument('-O', '--outfile', help='Output destination (filename)')
        parser.add_argument('-dl', '--datalogger', type=int, required=True, help='Datalogger id')

    def handle(self, *args, **options):
        endtime = create_datetime(options['endtime'], hourly=False)
        timelength = convert_to_seconds(options['timelength'])
        if options['starttime'] is not None:
            starttime = create_datetime(options['starttime'], hourly=False)
        else:
            starttime = endtime - datetime.timedelta(seconds=timelength)
        datalogger_id = options['datalogger']
        trkpts = Trackpoint.objects.filter(datalogger__id=datalogger_id)
        if trkpts.count() == 0:
            self.stderr.write(self.style.ERROR(f'Datalogger id {datalogger_id} does not exist :('))
            self.stderr.write(self.style.NOTICE('Try one of these:'))
            for dl in Trackpoint.objects.values('datalogger__devid', 'datalogger__id').distinct():
                self.stderr.write(self.style.NOTICE(f"{dl['datalogger__id']} {dl['datalogger__devid']}"))
            exit()
        trkpts = trkpts.filter(time__gte=starttime, time__lte=endtime).order_by('time')
        if options['outformat'] == 'gpx':
            outdata = create_gpx_file(trkpts)
        if options['outformat'] == 'csv':
            self.stderr.write(self.style.WARNING('Sorry, not implemented yet'))
            exit()
        if options['outfile'] is None:
            self.stderr.write(outdata)
        else:
            with open(options['outfile'], 'wt') as f:
                f.write(outdata)
