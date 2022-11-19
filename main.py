from datetime import datetime, timedelta
from geopy.distance import geodesic
from mapbox import Directions, Geocoder
import pytz
import requests
from tzwhere.tzwhere import tzwhere
import env


class Waypoint:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.nickname = None
        self.eta_utc = None
        self.eta_tz = None
        self.distance = -1
        self.distance_percentage = -1
        self.temperature_degf = -1
        self.precipitation_in = -1
        self.visiblity_mi = -1
        self.windspeed_mph = -1
        self.windgusts_mph = -1

    def __repr__(self):
        return f"{self.eta_tz.strftime('%m/%d %H:00')} - [ {self.temperature_degf:.0f}F | {self.precipitation_in:.1f}\" | {self.windspeed_mph:.0f}/{self.windgusts_mph:.0f}mph\t| {self.visiblity_mi:.1f}mi ] - ({self.latitude}, {self.longitude})"
        
    def as_tuple(self):
        return (self.latitude, self.longitude)

    def details(self):
        return f"""{self.eta_tz.strftime('%m/%d %H:00')} - "{self.nickname}"
Temperature: {self.temperature_degf:.0f} deg F
Precipitation: {self.precipitation_in:.1f}\"
Wind/Gusts: {self.windspeed_mph:.0f}mph / {self.windgusts_mph:.0f}mph
Visibility: {self.visiblity_mi:.1f}mi
Coordinates: ({self.latitude}, {self.longitude})"""

    def set_weather(self, temperature_degf, precipitation_in, visibility_mi, windspeed_mph, windgusts_mph):
        self.temperature_degf = temperature_degf
        self.precipitation_in = precipitation_in
        self.visiblity_mi = visibility_mi
        self.windspeed_mph = windspeed_mph
        self.windgusts_mph = windgusts_mph


# get geojson features for origin and destination
geo = Geocoder(access_token=env.MAPBOX_ACCESS_TOKEN)
resp = geo.forward('6265 Sand Lake Vista Dr, Orlando, FL 32819').geojson()
origin = resp['features'][0]
resp = geo.forward('614 Armandale St, Pittsburgh, PA 15212').geojson()
dest = resp['features'][0]


# get waypoints for entire route from origin to destination
service = Directions(access_token=env.MAPBOX_ACCESS_TOKEN)
resp = service.directions([origin, dest]).geojson()
waypoint_coords = resp['features'][0]['geometry']['coordinates']
waypoints = [Waypoint(w[1], w[0]) for w in waypoint_coords] # api gives lat/lon backwards
total_time_minutes = float(resp['features'][0]['properties']['duration']) / 60
total_distance_miles = float(resp['features'][0]['properties']['distance']) * 0.000621371


# set up timezone info
start_time = datetime.utcnow()
tzname = tzwhere().tzNameAt(*waypoints[0].as_tuple())
user_timezone = pytz.timezone(tzname)


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

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&hourly=temperature_2m,precipitation,visibility,windspeed_10m,windgusts_10m"
    hourly = requests.get(weather_url).json()['hourly']
    try:
        index = hourly['time'].index(eta_utc_fmt)
    except ValueError:
        print(f"No forecast available for {coords} -> ({eta_tz_fmt})")
        continue
    temperature = hourly['temperature_2m'][index]
    precipitation = hourly['precipitation'][index]
    visibility = float(hourly['visibility'][index]) / 5280
    wind_speed = hourly['windspeed_10m'][index]
    wind_gusts = hourly['windgusts_10m'][index]
    w.set_weather(temperature, precipitation, visibility, wind_speed, wind_gusts)


# show forecast
for w in weather_waypoints:
    print(w.details())
    print('---')
