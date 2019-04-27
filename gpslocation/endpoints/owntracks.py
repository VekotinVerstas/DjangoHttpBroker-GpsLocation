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
from gpslocation.models import Trackpoint

logger = logging.getLogger('gpslocation')

"""
Data sent by OwnTracks may look like this:
{"_type":"location",
      "acc":25,"alt":39,"batt":69,"conn":"m",
      "lat":60.171661,"lon":24.94480,
      "tid":"42","tst":1556014153,"vac":10,"vel":0
}
"""


def set_field(tp, key, field, data):
    try:
        val = float(data[key])
        setattr(tp, field, val)
    except (ValueError, KeyError) as err:
        pass


def create_trackpoint(datalogger, data, save=True):
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
        trkpt = Trackpoint(datalogger=datalogger, time=timestamp, lat=lat, lon=lon)
    else:
        return
    # Map OwnTracks data format to Trackpoint model's fields
    set_field(trkpt, 'acc', 'hacc', data)
    set_field(trkpt, 'alt', 'ele', data)
    set_field(trkpt, 'vac', 'vacc', data)
    set_field(trkpt, 'vel', 'speed', data)
    if save:
        trkpt.save()
    return trkpt


class OwnTracksEndpoint(EndpointProvider):
    description = 'Receive HTTP POST requests from OwnTracks Android app'

    def handle_request(self, request):
        if request.method != 'POST':
            return HttpResponse('Only POST with JSON body is allowed', status=405)
        serialised_request = serialize_django_request(request)
        print(serialised_request)
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
        key = create_routing_key('gpslocation', devid)
        send_message(settings.RAW_HTTP_EXCHANGE, key, message)
        ok, body = decode_json_body(serialised_request['request.body'])
        if ok is False:
            return HttpResponse(f'JSON ERROR: {body}', status=400, content_type='text/plain')
        datalogger, created = get_datalogger(devid=devid, update_activity=True)
        try:
            trkpt = create_trackpoint(datalogger, body, save=False)
            if user:
                trkpt.user = user
                trkpt.save()
            # response_msg = {'status': 'ok'}
        except ValueError as err:
            logger.error(err)
            # response_msg = {'status': 'error', 'msg': err}
        response_msg = {}  # Response just with empty json object
        return HttpResponse(json.dumps(response_msg), content_type='application/json')
