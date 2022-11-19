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
        self.weathercode = -1
        self.weather_description = None
        self.visiblity_mi = -1
        self.windspeed_mph = -1
        self.windgusts_mph = -1

    def __repr__(self):
        return f"{self.eta_tz.strftime('%m/%d %H:00')} - {self.temperature_degf:.0f}F - {self.weather_description}"
        
    def as_tuple(self):
        return (self.latitude, self.longitude)

    def details(self):
        return f"""{self.eta_tz.strftime('%m/%d %H:00')} - "{self.nickname}"
Temperature: {self.temperature_degf:.0f} deg F
Description: {self.weather_description}
Precipitation: {self.precipitation_in:.1f}\"
Wind/Gusts: {self.windspeed_mph:.0f}mph / {self.windgusts_mph:.0f}mph
Visibility: {self.visiblity_mi:.1f}mi
Coordinates: ({self.latitude}, {self.longitude})"""

    def set_weather(self, temperature_degf, precipitation_in, weathercode, visibility_mi, windspeed_mph, windgusts_mph):
        self.temperature_degf = temperature_degf
        self.precipitation_in = precipitation_in
        self.weathercode = weathercode
        self.weather_description = WeatherCode.interpret(weathercode)
        self.visiblity_mi = visibility_mi
        self.windspeed_mph = windspeed_mph
        self.windgusts_mph = windgusts_mph


class WeatherCode:
    values = {
        0 : 'Clear',
        1 : 'Mostly clear',
        2 : 'Partly cloudy',
        3 : 'Overcast',
        45 : 'Foggy',
        48 : 'Icy fog',
        51 : 'Light drizzle',
        53 : 'Moderate drizzle',
        55 : 'Heavy drizzle',
        56 : 'Light freezing drizzle',
        57 : 'Heavy freezing drizzle',
        61 : 'Light rain',
        63 : 'Moderate rain',
        65 : 'Heavy rain',
        66 : 'Light freezing rain',
        67 : 'Heavy freezing rain',
        71 : 'Light snow',
        73 : 'Moderate snow',
        75 : 'Heavy snow',
        77 : 'Ice',
        80 : 'Light rain showers',
        81 : 'Moderate rain showers',
        82 : 'Heavy rain showers',
        85 : 'Light snow showers',
        86 : 'Heavy snow showers',
        95 : 'Thunderstorms',
        96 : 'Thunderstorms with hail',
        99 : 'Thunderstorms with severe hail',
    }
    def interpret(number):
        return WeatherCode.values.get(number)
