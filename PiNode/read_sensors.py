import time
import os
from pathlib import Path
import board
import busio
import requests
from datetime import datetime
from dotenv import load_dotenv
from adafruit_seesaw.seesaw import Seesaw
import adafruit_tsl2591
import adafruit_dht

load_dotenv(Path(__file__).with_name(".env"))
API_ROOT = os.environ.get("GREENHOUSE_API_URL", "").rstrip("/")
EDGE_API_KEY = os.environ.get("GREENHOUSE_EDGE_KEY", "")
if not API_ROOT or not EDGE_API_KEY:
    raise RuntimeError(
        "Set GREENHOUSE_API_URL and GREENHOUSE_EDGE_KEY before starting the script."
    )

SENSOR_ENDPOINT = f"{API_ROOT}/api/sensors/"
HEARTBEAT_ENDPOINT = f"{API_ROOT}/api/edges/heartbeat/"
HEARTBEAT_INTERVAL = 30

#Initialize Shared I2C Bus & Devices (Soil: 0x36, Light: 0x29)
i2c = busio.I2C(board.SCL, board.SDA)

try:
    soil_sensor = Seesaw(i2c, addr=0x36)
    soil_active = True
except Exception as err:
    print(f"Warning: STEMMA Soil Sensor initialization failed: {err}")
    soil_active = False

try:
    light_sensor = adafruit_tsl2591.TSL2591(i2c)
    light_sensor.gain = adafruit_tsl2591.GAIN_LOW
    light_sensor.integration_time = adafruit_tsl2591.INTEGRATIONTIME_100MS
    light_active = True
except Exception as err:
    print(f"Warning: TSL2591 Light Sensor initialization failed: {err}")
    light_active = False

#Initialize AM2302 / DHT22 (Single-bus GPIO 4 / Pin 7)
dht_sensor = adafruit_dht.DHT22(board.D4)

print("Starting sensor data acquisition with timestamps (Press Ctrl+C to terminate)...")
print("-" * 75)

#Continuous Acquisition Loop
try:
    last_heartbeat = 0.0
    while True:
        # Standard formatted timestamp: YYYY-MM-DD HH:MM:SS
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Query Soil Sensor
        soil_moisture_reading = None
        soil_moisture_val = "N/A"
        soil_temp_val = "N/A"
        if soil_active:
            try:
                moisture = soil_sensor.moisture_read()
                temp_c = soil_sensor.get_temp()
                soil_moisture_reading = float(moisture)
                soil_moisture_val = f"{moisture}"
                soil_temp_val = f"{temp_c:.1f} °C"
            except Exception as e:
                soil_moisture_val = f"Err: {e}"

        # Query TSL2591 Light Sensor
        light_reading = None
        lux_val = "N/A"
        vis_val = "N/A"
        ir_val = "N/A"
        if light_active:
            try:
                lux = light_sensor.lux
                if lux is not None:
                    light_reading = float(lux)
                lux_val = f"{lux:.2f} Lux" if lux is not None else "Saturated/None"
                vis_val = f"{light_sensor.visible}"
                ir_val = f"{light_sensor.infrared}"
            except Exception as e:
                lux_val = f"Err: {e}"

        # Query AM2302 (DHT22) Air Temperature & Relative Humidity
        air_temperature_reading = None
        air_humidity_reading = None
        air_temp_val = "N/A"
        air_humidity_val = "N/A"
        try:
            temp_air = dht_sensor.temperature
            hum_air = dht_sensor.humidity
            if temp_air is not None:
                air_temperature_reading = float(temp_air)
                air_temp_val = f"{temp_air:.1f} °C"
            if hum_air is not None:
                air_humidity_reading = float(hum_air)
                air_humidity_val = f"{hum_air:.1f} %"
        except RuntimeError:
            # Expected occasional timing loss on Linux single-wire bus
            air_temp_val = "Syncing"
            air_humidity_val = "Syncing"
        except Exception as e:
            air_temp_val = f"Err: {e}"

        # Display block
        print(f"[{timestamp}]")
        print(f"  Soil Sensor  -> Moisture: {soil_moisture_val} | Temperature: {soil_temp_val}")
        print(f"  Light Sensor -> Ambient: {lux_val} | Visible: {vis_val} | IR: {ir_val}")
        print(f"  Air Sensor   -> Temperature: {air_temp_val} | Humidity: {air_humidity_val}")
        print("-" * 75)

        headers = {"X-Edge-Key": EDGE_API_KEY}
        if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
            try:
                response = requests.post(
                    HEARTBEAT_ENDPOINT, headers=headers, timeout=5
                )
                response.raise_for_status()
                print("Backend heartbeat sent")
            except requests.RequestException as error:
                print(f"Backend heartbeat failed: {error}")
            last_heartbeat = time.monotonic()

        reading = {
            "temperature": air_temperature_reading,
            "humidity": air_humidity_reading,
            "soil_moisture": soil_moisture_reading,
            "light": light_reading,
        }
        if all(value is not None for value in reading.values()):
            try:
                response = requests.post(
                    SENSOR_ENDPOINT, json=reading, headers=headers, timeout=5
                )
                response.raise_for_status()
                print("Sensor reading uploaded")
            except requests.RequestException as error:
                print(f"Sensor upload failed: {error}")
        else:
            print("Sensor reading not uploaded: one or more values are unavailable")

        # Minimum required interval for DHT22 stability is 2 seconds
        time.sleep(2.5)

except KeyboardInterrupt:
    print("\nData collection halted by user.")
finally:
    dht_sensor.exit()