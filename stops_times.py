from datetime import datetime
from datetime import timedelta
# import time
import requests
import json
import logging

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger("requests").setLevel(logging.WARNING)

API_URL = "https://fyp-postgrest.herokuapp.com/routes"
# GURL = "https://maps.googleapis.com/maps/api/distancematrix/json" 

TIME_FM = '%H:%M:%S'
stopOverDurationMin = 5

def getPayloadStr(params):
   payload_str = "&".join("%s=%s" % (k,v) for k,v in params.items())
   return payload_str

def toLatLngStr(lat,lng):
  return '%.20f,%.20f' % (lat,lng)

# def getTodayDate(date):
#   return date + timedelta(days=1)

# def getDateDiffInSec(startDate,endDate):
#    return ((endDate - startDate).total_seconds())

print("Program is running......")
# todayDate = getTodayDate(datetime.now())
# # response = requests.delete('https://fyp-postgrest.herokuapp.com/stops_time')

payload = {'select': 'route_id,trips{*},routes_stops{stops{*}},legs{*}', 
           'routes_stops.order': 'sequence.asc',
           'trips.order': 'pickup_time.asc',
           'legs.order': 'sequence.asc'}
data = requests.get(API_URL,params=getPayloadStr(payload)).json()

for result in data:
  routeId = result['route_id']
  trips = result['trips']
  stops = result['routes_stops']
  legs = result['legs']
  
  for trip in trips:
    tripId = trip['trip_id']
    pickupTime =  datetime.strptime(trip['pickup_time'],TIME_FM)
    for i in range(0,len(stops)):
      if i == 0:
        dbData = {  
                    'trip_id' : tripId,
                    'stop_id' : stops[i]['stops']['stop_id'],
                    'sequence' : i+1,
                    'arrival_time' : pickupTime.strftime(TIME_FM),
                    'departure_time' : pickupTime.strftime(TIME_FM),
                  }
      elif (i==len(stops)-1):
        durationMins = legs[i-1]['duration_mins']
        arrivalTime = pickupTime + timedelta(minutes=durationMins)
        pickupTime = arrivalTime + timedelta(minutes=stopOverDurationMin)
        dbData = {  
                    'trip_id' : tripId,
                    'stop_id' : stops[i]['stops']['stop_id'],
                    'sequence' : i+1,
                    'arrival_time' : arrivalTime.strftime(TIME_FM),
                    'departure_time' : arrivalTime.strftime(TIME_FM),
                  }
      else:
        durationMins = legs[i-1]['duration_mins']
        arrivalTime = pickupTime + timedelta(minutes=durationMins)
        pickupTime = arrivalTime + timedelta(minutes=stopOverDurationMin)
        dbData = {  
                    'trip_id' : tripId,
                    'stop_id' : stops[i]['stops']['stop_id'],
                    'sequence' : i+1,
                    'arrival_time' : arrivalTime.strftime(TIME_FM),
                    'departure_time' : pickupTime.strftime(TIME_FM),
                  }

      postRequest = requests.post("https://fyp-postgrest.herokuapp.com/stops_time", json=dbData)

print("Program is ended!")

# print(getTodayDate(datetime.now()).strftime("%a %d/%m/%Y"))
        
      
      