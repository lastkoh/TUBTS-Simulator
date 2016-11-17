from datetime import datetime
from datetime import timedelta
import requests
import json
import logging

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("requests").setLevel(logging.WARNING)

SIMULATION_TABLE_ROUTE_ID = "route_id"
SIMULATION_TABLE_TRIP_ID = "trip_id"
SIMULATION_TABLE_TIME = "trigger_time"
SIMULATION_TABLE_LAT = "lat"
SIMULATION_TABLE_LNG = "lng"
SIMULATION_TABLE_STOP_ID = "stop_id"
SIMULATION_TABLE_ETA = "eta_mins"

GM_ELEVATION_API_URL = "https://maps.googleapis.com/maps/api/elevation/json?"
GM_ELEVATION_API_KEY = "AIzaSyDPe6VoojLxtO--daxclqdIT8q2cJRfXQE"
GM_ELEVATION_API_PATH = "path=enc:"
GM_ELEVATION_API_SAMPLE = "samples="

API_URL = "https://fyp-postgrest.herokuapp.com/routes"

TIME_FM = '%H:%M:%S'
refreshIntervalSeconds = 60

def getPayloadStr(params):
   payload_str = "&".join("%s=%s" % (k,v) for k,v in params.items())
   return payload_str

def getStopOverDurationSecs(departuresTime,arrivalsTime):
  stopOverDuration = []
  for i in range(1,len(departuresTime)):
    departureTime = datetime.strptime(departuresTime[i],TIME_FM)
    arrivalTime = datetime.strptime(arrivalsTime[i],TIME_FM)
    stopOverDuration.append((departureTime - arrivalTime).total_seconds())
    
  return stopOverDuration

def getdiffInSec(departuresTime,arrivalsTime):
  diffInSec = []
  for i in range(0,len(departuresTime)-1):
    departureTime = datetime.strptime(departuresTime[i],TIME_FM)
    arrivalTime = datetime.strptime(arrivalsTime[i+1],TIME_FM)
    diffInSec.append((arrivalTime - departureTime).total_seconds())
  
  return diffInSec

def interpolatePos(routeID,tripID,diffInSec,legs,departuresTime,arrivalsTime,stopOverDurationInSecs,stopsID,nextStopsNames):
  
  for i in range(0,len(legs)):
    sample = str(int(diffInSec[i]/refreshIntervalSeconds) + 1)
    
    tempStr = 'enc:' + legs[i]
    payload = {'key': GM_ELEVATION_API_KEY, 'samples': sample , 'path': tempStr}
    r = requests.get(GM_ELEVATION_API_URL,params=getPayloadStr(payload));
    
    departureTime = datetime.strptime(departuresTime[i],TIME_FM)
    arrivalTime = datetime.strptime(arrivalsTime[i+1],TIME_FM)
    stopID = stopsID[i+1]
    nextStopName = nextStopsNames[i+1]
    currDateTime = departureTime
    stopLatPos = 0
    stopLngPos = 0
    data = r.json();

    results = data['results']
    for k in range(0,len(results)):

      location = results[k]['location']
      if k == len(results)-1:
        eta = 0
      else:
        eta = (arrivalTime - currDateTime).total_seconds()/60;
        
      tempStr = currDateTime.strftime(TIME_FM)[:-2] + '00'
      dbEntry = {'route_id' : routeID,
      'trip_id' : tripID,
      'stop_id' : stopID,
      'lat' : location['lat'],
      'lng' : location['lng'],
      'eta_mins' : int(eta),
      'trigger_time' : tempStr,
      'next_stop_name': nextStopName
              }

      postRequest = requests.post("https://fyp-postgrest.herokuapp.com/simulation", json=dbEntry)
      
      stopLngPos = location['lng']
      stopLatPos = location['lat']
      currDateTime += timedelta(seconds=refreshIntervalSeconds)

    for z in range(0,int((stopOverDurationInSecs[i]-refreshIntervalSeconds)/refreshIntervalSeconds)):
      tempStr = currDateTime.strftime(TIME_FM)[:-2] + '00'
      dbEntry = {
      'route_id' : routeID,
      'trip_id' : tripID,
      'stop_id' : stopID,
      'lat' : stopLatPos,
      'lng' : stopLngPos,
      'eta_mins' : 0,
      'trigger_time' : tempStr,
      'next_stop_name': nextStopName
              }
    
      postRequest = requests.post("https://fyp-postgrest.herokuapp.com/simulation", json=dbEntry)
      currDateTime += timedelta(seconds=refreshIntervalSeconds)

      
print("Program is running......")

# response = requests.delete('https://fyp-postgrest.herokuapp.com/simulation')

payload = {'select': '*,legs{*},trips{trip_id,stops_time{*,stops{*}}}', 
           'order': 'route_id.asc',
           'trips.stops_time.order': 'sequence.asc',
           'legs.order': 'sequence.asc'}
data = requests.get(API_URL,params=getPayloadStr(payload)).json();

for route in data:
  routeId = route['route_id']
  legsJson = route['legs']
  trips = route['trips']
  
  legs = [];
  for leg in legsJson:
    legs.append(leg['path'])
    
  for trip in trips:
    tripId = trip['trip_id']
    stopsTime = trip['stops_time']
    
    arrivalsTime = []
    departuresTime = []
    stopsId = []
    nextStopsNames = []
  
    for i in range(0,len(stopsTime)):
      arrivalsTime.append(stopsTime[i]['arrival_time'])
      departuresTime.append(stopsTime[i]['departure_time'])
      stop = stopsTime[i]['stops']
      stopsId.append(stop['stop_id'])
      nextStopsNames.append(stop['name'])

    stopsOverDuration = getStopOverDurationSecs(departuresTime,arrivalsTime)
    diffInSec = getdiffInSec(departuresTime,arrivalsTime)
    interpolatePos(routeId,tripId,diffInSec,legs,departuresTime,arrivalsTime,stopsOverDuration,stopsId,nextStopsNames)

print("Program is ended!")
  