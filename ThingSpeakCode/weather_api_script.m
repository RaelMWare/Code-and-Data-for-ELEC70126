% Get External Weather Data from Open-Meteo API

run('secrets.m');

% Fetch weather data from Open-Meteo
url = 'https://api.open-meteo.com/v1/forecast?latitude=53.48&longitude=-2.24&current=temperature_2m,relative_humidity_2m,wind_speed_10m';
data = webread(url);

% Extract values
outdoorTemp = data.current.temperature_2m;
outdoorHumidity = data.current.relative_humidity_2m;

% Write to ThingSpeak (Field 4 = Outdoor Temp, Field 5 = Outdoor Humidity)
thingSpeakWrite(weatherChannelID, 'Fields', [1, 2], 'Values', [outdoorTemp, outdoorHumidity], 'WriteKey', weatherWriteKey);

% Display output
fprintf('Outdoor Temperature: %.1f °C\n', outdoorTemp);
fprintf('Outdoor Humidity: %d %%\n', outdoorHumidity);