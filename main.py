from datetime import datetime, timedelta
from geopy.distance import geodesic
from mapbox import Directions, Geocoder
import pytz
import requests
from tzwhere.tzwhere import tzwhere
import env


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
waypoint_coords = [(w[1], w[0]) for w in waypoint_coords] # api gives lat/lon backwards
total_time_minutes = float(resp['features'][0]['properties']['duration']) / 60
total_distance_miles = float(resp['features'][0]['properties']['distance']) * 0.000621371


# grab waypoints that are roughly 50 miles of driving apart
weather_waypoints = []
weather_waypoint_time_estimates = []
last_waypoint = 0
dist_traveled = 0
for i in range(len(waypoint_coords) - 1):
    distance_mi = geodesic(waypoint_coords[i], waypoint_coords[i+1]).miles
    dist_traveled += distance_mi
    if dist_traveled - last_waypoint > 50 or last_waypoint == 0:
        last_waypoint = dist_traveled
        weather_waypoints.append(waypoint_coords[i+1])
        distance_percentage = dist_traveled / total_distance_miles
        approx_time_reached = total_time_minutes * distance_percentage
        weather_waypoint_time_estimates.append(approx_time_reached)


# get weather at each waypoint for the time we will be there
start_time = datetime.utcnow()
tzname = tzwhere().tzNameAt(*weather_waypoints[0])
user_timezone = pytz.timezone(tzname)
weather = zip(weather_waypoints, weather_waypoint_time_estimates)
for w in weather:
    coords, eta_min = w
    eta = start_time + timedelta(minutes=eta_min)
    eta_rounded = eta.replace(minute=0, second=0, microsecond=0) + timedelta(hours=eta.minute//30)
    eta_rounded_fmt = eta_rounded.strftime('%Y-%m-%dT%H:00')
    eta_rounded_tz = user_timezone.fromutc(eta_rounded).strftime('%H:00')

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&hourly=temperature_2m,precipitation,visibility,windspeed_10m,windgusts_10m"
    hourly = requests.get(weather_url).json()['hourly']
    try:
        index = hourly['time'].index(eta_rounded_fmt)
    except ValueError:
        print(f"No forecast available for {coords} -> ({eta_rounded_fmt})")
        continue
    temperature = hourly['temperature_2m'][index]
    precipitation = hourly['precipitation'][index]
    visibility = float(hourly['visibility'][index]) / 5280
    wind_speed = hourly['windspeed_10m'][index]
    wind_gusts = hourly['windgusts_10m'][index]
    print(f"{coords} -> {temperature}F {precipitation:.1f}\" {visibility:.1f}mi {wind_speed:.1f}mph/{wind_gusts:.1f}mph ({eta_rounded_tz})")
