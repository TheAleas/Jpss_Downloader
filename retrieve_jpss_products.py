#!/home/lnxadmin/.local/share/pipx/venvs/polar2grid/bin/python3

#version 1.0
# important: set the timezone

import time
import boto3
import os
import argparse
import shutil
from datetime import datetime, timedelta, timezone
import subprocess
from botocore import UNSIGNED
from botocore.client import Config
from PIL import Image
import logging

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

######## Configure logging #####################
log_file = "/var/log/retrieve_jpss_products.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("Starting the JPSS retrieval script")
logging.info("Arguments: " + str(args))

########## Variables #############################

# Set the maximum image pixels to None to avoid the DecompressionBombError
Image.MAX_IMAGE_PIXELS = None

satellite = args.satellite
clean_raw_data = args.clean

#Calculate Start Time
LocalStartTime = datetime.strptime(args.start, '%Y-%m-%dT%H:%M:%S')
ZuluStartTime = LocalStartTime.astimezone(timezone.utc)
StartTime = int(ZuluStartTime.strftime('%H%M%S0'))
logging.info(f'UTC Start Time: {StartTime}')

#Calculate End Time
EndTime = ZuluStartTime
EndTime += timedelta(minutes=args.duration)
EndTime = int(EndTime.strftime('%H%M%S0'))
logging.info(f'UTC End Time: {EndTime}')
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
            'VIIRS-M10-SDR',
            'VIIRS-M11-SDR',
            'VIIRS-M13-SDR', 
            'VIIRS-M15-SDR',
            'VIIRS-MOD-GEO-TC',
            'VIIRS-DNB-GEO',
            'VIIRS-DNB-SDR'
            ]
polar2grid_home = os.environ.get('POLAR2GRID_HOME')

ProductsToMake = 'true_color adaptive_dnb i03 i05 i04'

base_path = '/srv/raw_data/'

user_home = os.path.expanduser("~")

match satellite:
    case 'n21':
        SatelliteName = 'NOAA 21'
    case 'n20':
        SatelliteName = 'NOAA 20'
    case 'snpp':
        SatelliteName = 'Suomi npp'

############## Functions ##################

# Function to remove all files in a directory
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
                    logging.error(f'Failed to delete {file_path}. Reason: {e}')
        else:
            logging.error("The folder "+ folder_path + "does not exist.")
    except Exception as e:
        logging.error(f'Error: {e}')

#Function to convert TIF files to JPEG
def convert_tif_to_jpeg(directory):
    try:
        for filename in os.listdir(directory):
            if filename.endswith(".tif"):
                tif_path = os.path.join(directory, filename)
                jpeg_path = os.path.join("/srv/aws/", os.path.splitext(filename)[0] + ".jpg")
                try:
                    with Image.open(tif_path) as img:
                        img.convert("RGB").save(jpeg_path, "JPEG")
                        logging.debug(f"Converted {filename} to {jpeg_path}")
                except Exception as e:
                    logging.warning(f"Failed to convert {filename}. Reason: {e}")
    except Exception as e:
        logging.error(f"Error processing directory {directory}. Reason: {e}")

#Function to remove zero-byte files
def remove_zero_byte_files(directory):
    """
    Removes all zero-byte (0 KB) files from the specified directory.
    
    Args:
        directory (str): The path to the directory where you want to remove zero-byte files.
    """
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    logging.debug(f"Removed zero-byte file: {file_path}")
        logging.info("All zero-byte files have been removed successfully.")
    except Exception as e:
        logging.error(f"An error occurred while removing zero-byte files: {e}")

############### Main #####################

if clean_raw_data is True :
        remove_all_files(base_path)
        remove_all_files (user_home + '/tmp/')
        logging.info("Old data has been removed successfully.")


logging.info("Fetching Satellite " + SatelliteName)

for product in ProductList:
    logging.info('Fetching product ' + product)
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
                if os.path.isfile(FullPath):
                    logging.info("File exist, skipping")
                else:
                    logging.info("Downloading " + FileName)
                    s3.download_file(bucket_name, obj['Key'], FullPath)
    else:
        logging.warning("No objects found for product " + product)

################# End ######################

logging.info("Processing with polar2grid, creating LCC grid")

polar2grid_arguments = user_home + '/.local/bin/polar2grid -r viirs_sdr -g lcc_fit -w geotiff -f ' + base_path + '*.h5 --num-workers 12 --fill-value 0 -p overview night_overview adaptive_dnb i03'

subprocess.run([polar2grid_arguments], shell=True)

time.sleep(3)

logging.info("Removing empty files")

remove_zero_byte_files(user_home + "/tmp/")

logging.info("Converting TIF to JPEG")

convert_tif_to_jpeg(user_home + "/tmp/")

logging.info('script finished at ' + str(datetime.now()))
