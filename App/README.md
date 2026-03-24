# CO₂ Sensor Dashboard

## Pages

| Page                   | Description                                                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Live Monitor** | Current CO₂ (colour-coded), temperature, humidity, occupancy. Ventilation banner with configurable thresholds. Window & concentration logging. |
| **Time Series**  | Interactive multi-series charts with date range picker. Toggle CO₂, temp, humidity, occupancy, fan, window, and concentration.                 |
| **Analytics**    | Summary statistics, average CO₂ by hour, CO₂ vs concentration analysis, window open/closed impact.                                            |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run Live_Monitor.py
```

The app opens at `http://localhost:8501`.

## ThingSpeak Channels

| Channel          | ID      | Fields                                                       |
| ---------------- | ------- | ------------------------------------------------------------ |
| CO₂ Sensor      | 3264555 | field1=CO₂, field2=Humidity, field3=Temperature             |
| External API     | 3272729 | field1=Outdoor Temp, field2=Outdoor Humidity                 |
| Output Channel   | 3272730 | field1=Fan Activation                                        |
| External Factors | 3278561 | field1=Occupants, field2=Concentration, field3=Window Status |

## Ventilation Logic

A ventilation banner appears on the Live Monitor page. Opening a window is recommended when **all three** conditions are met:

1. Indoor CO₂ is above the threshold (default 800 ppm, adjustable in sidebar)
2. Outdoor temperature is above the minimum (default 5°C, adjustable)
3. Outdoor humidity is below 85%

The estimated ventilation duration is based on the excess CO₂ above the threshold, assuming roughly 10 ppm reduction per minute.

## Project Structure

```
co2_dashboard/
├── .streamlit/
│   └── config.toml        # Theme and server settings
├── pages/
│   ├── 1__Time_Series.py
│   └── 2__Analytics.py
├── config.py               # Shared config, data fetching, helpers
├── Live_Monitor.py          # Main page (entry point)
├── requirements.txt
└── README.md
```
