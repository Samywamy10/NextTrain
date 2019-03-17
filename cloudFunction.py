from hashlib import sha1
import hmac
import binascii
from google.cloud import firestore
import requests
import json
from datetime import datetime, timedelta

def getUrl(request):
    devId = 3001062
    key = b'd4c3374c-4679-4c39-81dc-fc1a3f910581'
    request = request + ('&' if ('?' in request) else '?')
    raw = request+'devid={0}'.format(devId)
    hashed = hmac.new(key, raw.encode('utf-8'), sha1)
    signature = hashed.hexdigest()
    return 'https://timetableapi.ptv.vic.gov.au{0}&signature={1}'.format(raw, signature)

db = firestore.Client()

def getNextPlatforms(request):
    FlindersStUrl = getUrl('/v3/departures/route_type/0/stop/1071')
    FlindersStData = requests.get(FlindersStUrl).json()
    FlindersStDepartures = FlindersStData['departures']
    nextTrains = {}
    nextTrains['southern_cross'] = []
    nextTrains['parliament'] = []
    nextTrains['richmond'] = []
    nextTrains['north_melbourne'] = []
    nextStopsCollection = db.collection('nextStops').get()
    nextStopsDict = convertCollectionToDict(nextStopsCollection)
    for departure in FlindersStDepartures:
        theDate = datetime.strptime(departure['scheduled_departure_utc'],'%Y-%m-%dT%H:%M:%SZ')
        if theDate > datetime.utcnow() and theDate < datetime.utcnow() + timedelta(minutes = 20):
            theDate = theDate + timedelta(hours = 11)
            routeId = departure['route_id']
            directionId = departure['direction_id']
            stopId = departure['stop_id']
            nextStop = getNextStop(stopId,str(routeId),str(directionId), nextStopsDict)
            next_train = {}
            next_train['platform_number'] = int(departure['platform_number'])
            next_train['dateTime'] = theDate.strftime('%Y-%m-%dT%H:%M:%S')
            if nextStop['stop_id'] == 1181: #Southern cross
                nextTrains['southern_cross'].append(next_train)
            elif nextStop['stop_id'] == 1155: #Parliament
                nextTrains['parliament'].append(next_train)
            elif nextStop['stop_id'] == 1162: #Richmond
                nextTrains['richmond'].append(next_train)
            elif nextStop['stop_id'] == 1144: #North Melbourne
                nextTrains['north_melbourne'].append(next_train)
    return json.dumps(nextTrains)

def getNextStop(stopId,routeId,directionId, nextStopsDict):
    key = '{0}{1}{2}'.format(stopId,routeId,directionId)
    fetchNextStop = nextStopExists(nextStopsDict,key)
    if not fetchNextStop:
        stops = getStops(routeId, directionId)
        stops = getStops(routeId,directionId)
        checkNextStop = False
        for stop in stops:
            if stop['stop_id'] == stopId:
                checkNextStop = True
            elif checkNextStop == True:
                nextStopDoc = db.collection('nextStops').document(key)
                nextStopDoc.set(stop)
                return stop
        return "end of line"
    else:
        return fetchNextStop

def convertCollectionToDict(collection):
    collectionDict = {}
    for document in collection:
        collectionDict[document.id] = document.to_dict()
    return collectionDict


def nextStopExists(nextStopsDict, key):
    if key in nextStopsDict:
        return nextStopsDict[key]
    return False

def getStops(routeId,directionId):
    stopsUrl = getUrl('/v3/stops/route/{0}/route_type/0?direction_id={1}'.format(routeId,directionId))
    stopsData = requests.get(stopsUrl).json()['stops']
    stopsData.sort(key=lambda x: x['stop_sequence'])
    return stopsData


print(getNextPlatforms('hello'))