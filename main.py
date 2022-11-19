from datetime import datetime, timedelta
from geopy.distance import geodesic
from mapbox import Directions, Geocoder
import pytz
import requests
from tzwhere.tzwhere import tzwhere
import env
from objects import Waypoint, WeatherCode


addr1 = input('Origin >> ')
if len(addr1) == 0:
    exit()
addr2 = input('Destination >> ')
if len(addr2) == 0:
    exit()
dept_time = input('Departure time [ISO] (optional) >> ')
print('Working...')


# get geojson features for origin and destination
geo = Geocoder(access_token=env.MAPBOX_ACCESS_TOKEN)
resp = geo.forward(addr1).geojson()
origin = resp['features'][0]
resp = geo.forward(addr2).geojson()
dest = resp['features'][0]


# get waypoints for entire route from origin to destination
service = Directions(access_token=env.MAPBOX_ACCESS_TOKEN)
resp = service.directions([origin, dest]).geojson()
waypoint_coords = resp['features'][0]['geometry']['coordinates']
waypoints = [Waypoint(w[1], w[0]) for w in waypoint_coords] # api gives lat/lon backwards
total_time_minutes = float(resp['features'][0]['properties']['duration']) / 60
total_distance_miles = float(resp['features'][0]['properties']['distance']) * 0.000621371


# set up timezone info
tzname = tzwhere().tzNameAt(*waypoints[0].as_tuple())
user_timezone = pytz.timezone(tzname)
if len(dept_time) == 0:
    start_time = datetime.utcnow()
else:
    start_time = datetime.fromisoformat(dept_time).astimezone(user_timezone)
    start_time = start_time - start_time.utcoffset()


# grab waypoints that are roughly 50 miles of driving apart
weather_waypoints = []
dist_traveled = 0
for i in range(len(waypoints) - 1):
    distance_mi = geodesic(waypoints[i].as_tuple(), waypoints[i+1].as_tuple()).miles
    dist_traveled += distance_mi
    if len(weather_waypoints) == 0 or dist_traveled - weather_waypoints[-1].distance > 50:
        last_waypoint = dist_traveled
        weather_waypoint = Waypoint(*waypoints[i+1].as_tuple())
        weather_waypoint.distance = dist_traveled
        weather_waypoint.distance_percentage = dist_traveled / total_distance_miles
        weather_waypoint.eta_utc = start_time + timedelta(minutes=total_time_minutes * weather_waypoint.distance_percentage)
        weather_waypoint.eta_utc.replace(minute=0, second=0, microsecond=0) + timedelta(hours=weather_waypoint.eta_utc.minute//30)
        weather_waypoint.eta_tz = user_timezone.fromutc(weather_waypoint.eta_utc)
        resp = geo.reverse(weather_waypoint.longitude, weather_waypoint.latitude).geojson()
        name = resp['features'][0]['place_name']
        weather_waypoint.nickname = name
        weather_waypoints.append(weather_waypoint)


# get weather at each waypoint for the time we will be there
for w in weather_waypoints:
    coords = w.as_tuple()
    eta_utc_fmt = w.eta_utc.strftime('%Y-%m-%dT%H:00')
    eta_tz_fmt = w.eta_tz.strftime('%H:00')

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&hourly=temperature_2m,precipitation,weathercode,visibility,windspeed_10m,windgusts_10m"
    hourly = requests.get(weather_url).json()['hourly']
    try:
        index = hourly['time'].index(eta_utc_fmt)
    except ValueError:
        print(f"No forecast available for {coords} -> ({eta_tz_fmt})")
        continue
    temperature = hourly['temperature_2m'][index]
    precipitation = hourly['precipitation'][index]
    weathercode = hourly['weathercode'][index]
    visibility = float(hourly['visibility'][index]) / 5280
    wind_speed = hourly['windspeed_10m'][index]
    wind_gusts = hourly['windgusts_10m'][index]
    w.set_weather(temperature, precipitation, weathercode, visibility, wind_speed, wind_gusts)


# show forecast
for w in weather_waypoints:
    # print(w.details())
    # print('---')
    print(w)
