#!/home/lnxadmin/.local/share/pipx/venvs/polar2grid/bin/python3

from skyfield.api import load, Topos, EarthSatellite
from skyfield.iokit import parse_tle_file
import json
import datetime
import numpy as np
import logging
from crontab import CronTab
import argparse
import os

########## Parameters ######################

parser = argparse.ArgumentParser(
                    prog='retrieve_jpss_products',
                    description='This program downloads JPSS data from the cloud',
                    epilog='Text at the bottom of help')

parser.add_argument('--satellite', type=str, required=True, help='Name of the satellite')
parser.add_argument('--predict', type=int, required=False, help='How far ahead to predict in hours', default=72)
parser.add_argument('--clean', action=argparse.BooleanOptionalAction, help='Cleanup old cron jobs before starting')
args = parser.parse_args()


### Configure logging

##### Functions ######################


#### Variables

SatelliteToPredict = args.satellite
clean_CronJobs = args.clean
HoursToPredict = args.predict

ts = load.timescale()
num_samples = 1000

SatToPredictID = '0'

if SatelliteToPredict == 'NOAA 21':
    SatToPredictID = 54234
    SatShortName = 'n21'
elif SatelliteToPredict == 'NOAA 20':
    SatToPredictID = 43013
    SatShortName = 'n20'
elif SatelliteToPredict == 'SNPP':
    SatToPredictID = 37849
    SatShortName = 'snpp'
else:
    raise ValueError(f"Unknown satellite: {SatelliteToPredict}")


max_days = 7.0         # download again once 7 days old
TleFileName = 'weather.tle'  # custom filename, not 'gp.php'

base = 'https://celestrak.org/NORAD/elements/gp.php'
url = base + '?GROUP=weather&FORMAT=tle'

if not load.exists(TleFileName) or load.days_old(TleFileName) >= max_days:
    load.download(url, filename=TleFileName)


with load.open(TleFileName) as f:
    satellites = list(parse_tle_file(f, ts))

print('Loaded', len(satellites), 'satellites')

by_number = {sat.model.satnum: sat for sat in satellites}

if SatToPredictID in by_number:
    satellite = by_number[SatToPredictID]
else:
    raise KeyError(f"Satellite ID {SatToPredictID} not found in the TLE data.")

# Load the coordinates from a file named location.txt line 1 is latitude and line 2 is longitude
# The file should be in the same directory as this script
try:
    with open('location.txt', 'r') as file:
        lines = file.readlines()
        latitude, longitude = map(float, lines[:2])  # Read the first two lines as latitude and longitude
        location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
except (FileNotFoundError, ValueError, IndexError) as e:
    raise RuntimeError("Failed to load coordinates from location.txt. Ensure the file exists and contains valid latitude and longitude.") from e


now = datetime.datetime.now(datetime.timezone.utc)
start_time = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)
end_datetime = now + datetime.timedelta(hours=HoursToPredict)
end_time = ts.utc(end_datetime.year, end_datetime.month, end_datetime.day,
                    end_datetime.hour, end_datetime.minute, end_datetime.second)

# Predict the satellite events when its altitude is above 10 degrees.
# find_events returns: times of events and an array of event codes (0: rise, 1: culmination, 2: set)
#t_events, events = satellite.find_events(location, t, altitude_degrees=10.0)

t_events, events = satellite.find_events(location, start_time, end_time, altitude_degrees=10.0)

user_home = os.path.expanduser("~")

# Process the events in groups of three: each pass should give you a rising, culmination, and setting.

local_tz = datetime.datetime.now().astimezone().tzinfo

cron = CronTab(user=True)  # Use the current user's crontab

# Remove all existing cron jobs
if clean_CronJobs is True :
    logging.info("Removing all existing cron jobs...")
    cron.remove_all()
    cron.write()


print("Predicted satellite passes:")
for i in range(0, len(events) // 3 * 3, 3):
    if events[i] == 0 and events[i+1] == 1 and events[i+2] == 2:
        t_rise = t_events[i].astimezone(local_tz)
        t_culm = t_events[i+1].astimezone(local_tz)
        t_set = t_events[i+2].astimezone(local_tz)
        Estdelivery_Time = (t_events[i+2] + datetime.timedelta(hours=2)).astimezone(local_tz)
        # Format the times for the cron job
        cron_hour = Estdelivery_Time.hour
        cron_minute = Estdelivery_Time.minute
        cron_day = Estdelivery_Time.day
        cron_month = Estdelivery_Time.month
        cron_year = Estdelivery_Time.year
        t_rise_str = t_rise.strftime('%Y-%m-%dT%H:%M:%S')
        # Create a new cron job
        job = cron.new(command=f'cd ' + user_home + '/tmp && ' + user_home + '/scripts/retrieve_jpss_products.py --satellite ' + SatShortName + ' --start '+ t_rise_str + ' --duration 15 --clean')
        # Set the time for the cron job
        job.setall(f"{cron_minute} {cron_hour} {cron_day} {cron_month} *")
        # Write the cron job to the crontab
        cron.write()
        print(f"Cron job created to run at {Estdelivery_Time.strftime('%Y-%m-%d %H:%M:%S')} for pass at: {t_rise_str}") 
