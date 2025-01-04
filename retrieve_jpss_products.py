#version 1.0

import boto3
import os
import argparse
import shutil
from datetime import datetime, timedelta, timezone
import subprocess
from botocore import UNSIGNED
from botocore.client import Config

######### Parameters ######################

parser = argparse.ArgumentParser(
                    prog='retrieve_jpss_products',
                    description='This program downloads JPSS data from the cloud',
                    epilog='Text at the bottom of help')

parser.add_argument('--satellite', type=str, required=True, help='Name of the satellite')
parser.add_argument('--start', type=str, required=True, help='Start Time in the format YYYY-MM-DDTHH:MM:SS')
parser.add_argument('--duration', type=int, required=True, help='Duration in minutes')
parser.add_argument('--clean', action=argparse.BooleanOptionalAction, help='Cleanup raw directory before starting')
args = parser.parse_args()

########## Variables #############################

satellite = args.satellite
clean_raw_data = args.clean


#Calculate Start Time
LocalStartTime = datetime.strptime(args.start, '%Y-%m-%dT%H:%M:%S')
ZuluStartTime = LocalStartTime.astimezone(timezone.utc)
StartTime = int(ZuluStartTime.strftime('%H%M%S0'))
print(f'UTC Start Time: {StartTime}')

#Calculate End Time
EndTime = ZuluStartTime
EndTime += timedelta(minutes=args.duration)
EndTime = int(EndTime.strftime('%H%M%S0'))
print(f'UTC End Time: {EndTime}')
# Create an S3 client with unsigned configuration
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

bucket_name = 'noaa-nesdis-' + satellite + '-pds'
date_year = (ZuluStartTime.strftime("%Y"))
date_month = (ZuluStartTime.strftime("%m"))
date_day = (ZuluStartTime.strftime("%d"))
ProductList = ['VIIRS-IMG-GEO-TC',
            'VIIRS-IMG-GEO',
            'VIIRS-I1-SDR',
            'VIIRS-I2-SDR',
            'VIIRS-I3-SDR',
            'VIIRS-I4-SDR',
            'VIIRS-I5-SDR',
            'VIIRS-M1-SDR',
            'VIIRS-M3-SDR',
            'VIIRS-M4-SDR',
            'VIIRS-M5-SDR',
            'VIIRS-M7-SDR',
            'VIIRS-M11-SDR',
            'VIIRS-M13-SDR',
            'VIIRS-MOD-GEO-TC',
            'VIIRS-DNB-GEO',
            'VIIRS-DNB-SDR'
            ]
polar2grid_home = os.environ.get('POLAR2GRID_HOME')

base_path = polar2grid_home + '/raw_data/'

match satellite:
    case 'n21':
        SatelliteName = 'NOAA 21'
    case 'n20':
        SatelliteName = 'NOAA 20'
    case 'snpp':
        SatelliteName = 'Suomi npp'

############## Functions ##################

def remove_all_files(folder_path):
    try:
        # Check if the folder exists
        if os.path.exists(folder_path):
            # Iterate over all the files in the folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                try:
                    # Check if it is a file and remove it
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    # Check if it is a directory and remove it
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
            print("Old data has been removed successfully.")
        else:
            print("The folder does not exist.")
    except Exception as e:
        print(f'Error: {e}')


############### Main #####################

if clean_raw_data is True :
    remove_all_files (base_path)


print("Fetching Satellite " + SatelliteName)

for product in ProductList:
    print('Fetching product ' + product)
    LookupString = product + '/' + date_year + '/' + date_month + '/' + date_day + '/'
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=LookupString)
    if 'Contents' in response:
        for obj in response['Contents']:
            FileName = (obj['Key']).split("/")[4]
            FileNameValues = FileName.split("_")
            ObservationStartTime = int(FileNameValues[3].lstrip('t'))
            ObservationEndTime = int(FileNameValues[4].lstrip('e'))
            if ObservationStartTime > StartTime and ObservationEndTime < EndTime :
                FullPath = base_path + FileName
                #print(FullPath)
                if os.path.isfile(FullPath):
                    print("File exist, skipping")
                else:
                    print("Downloading " + FileName)
                    s3.download_file(bucket_name, obj['Key'], FullPath)
    else:
        print("No objects found for product " + product)

################# End ######################

print('please run $POLAR2GRID_HOME/bin/polar2grid.sh -r viirs_sdr -w geotiff -f ~/raw_data/*.h5 --num-workers 12 --progress --list-products')