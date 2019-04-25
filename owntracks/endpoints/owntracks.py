import datetime
import json
import logging

import pytz
from django.conf import settings
from django.http.response import HttpResponse

from broker.providers.endpoint import EndpointProvider
from broker.utils import (
    decode_json_body, get_datalogger, create_routing_key,
    serialize_django_request, data_pack, send_message,
    basicauth
)
from owntracks.models import Trackpoint

logger = logging.getLogger('owntracks')

"""
Data sent by OwnTracks may look like this:
{"_type":"location",
      "acc":25,"alt":39,"batt":69,"conn":"m",
      "lat":60.171661,"lon":24.94480,
      "tid":"42","tst":1556014153,"vac":10,"vel":0
}
"""


def save_trackpoint(datalogger, data):
    # TODO: test with invalid data and implement some tests in test.py
    try:
        timestamp = datetime.datetime.utcfromtimestamp(data['tst'])
        timestamp = pytz.UTC.localize(timestamp)
    except (ValueError, KeyError) as err:
        msg = f'Invalid timestamp data: ({err}'
        logger.error(msg)
        raise ValueError(msg)
    try:
        lat = float(data['lat'])
        lon = float(data['lon'])
    except (ValueError, KeyError) as err:
        msg = f'Invalid lat/lon data: ({err}'
        logger.error(msg)
        raise ValueError(msg)

    if Trackpoint.objects.filter(datalogger=datalogger, time=timestamp).count() == 0:
        tp = Trackpoint(datalogger=datalogger, time=timestamp, lat=lat, lon=lon)
    else:
        return
    #tp = Trackpoint(datalogger=datalogger, time=timestamp)
    #tp.lat = lat
    #tp.lon = lon
    for key in ["acc", "alt", "batt", "vac", "vel"]:
        try:
            val = float(data[key])
            setattr(tp, key, val)
        except (ValueError, KeyError) as err:
            logger.error(msg)
            continue
    for key in ["tid", "conn"]:
        try:
            val = data[key]
            setattr(tp, key, val)
        except (ValueError, KeyError) as err:
            logger.error(msg)
            continue
    tp.save()


class OwnTracksEndpoint(EndpointProvider):
    description = 'Receive HTTP POST requests from OwnTracks Android app'

    def handle_request(self, request):
        if request.method != 'POST':
            return HttpResponse('Only POST with JSON body is allowed', status=405)
        serialised_request = serialize_django_request(request)
        # TODO: check authentication
        uname, passwd, user = basicauth(request)
        username = request.META.get('HTTP_X_LIMIT_U')
        device_id = request.META.get('HTTP_X_LIMIT_D')
        if username is None or device_id is None:
            return HttpResponse(f'User or device id was not found in headers', status=400, content_type='text/plain')
        devid = f'{username}_{device_id}'
        serialised_request['devid'] = devid
        serialised_request['time'] = datetime.datetime.utcnow().isoformat() + 'Z'
        message = data_pack(serialised_request)
        key = create_routing_key('owntracks', devid)
        send_message(settings.RAW_HTTP_EXCHANGE, key, message)
        ok, body = decode_json_body(serialised_request['request.body'])
        if ok is False:
            return HttpResponse(f'JSON ERROR: {body}', status=400, content_type='text/plain')
        datalogger, created = get_datalogger(devid=devid, update_activity=True)
        try:
            save_trackpoint(datalogger, body)
            response_msg = {'status': 'ok'}
        except ValueError as err:
            response_msg = {'status': 'error', 'msg': err}
        response_msg = {}
        return HttpResponse(json.dumps(response_msg), content_type='application/json')

