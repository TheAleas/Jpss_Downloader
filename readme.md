# Version

Version 1.0

# Requirements

- CSPP polar2grid
- python 3.10
- boto3 python module

# Install

1. Install polar2Grid in a location of your choice.
2. create 'raw_data' and 'output' under the polar2grid install directory



# Usage

1. Run the retrieve_jpss_products.py script
    Example
```
    python3 ~/script/retrieve_jpss_products.py  --start 2024-12-27T01:12:19 --duration 15 --satellite n21 --clean
```
2. Run polar2grid to process the data and output the images.
    Example
```
#List available products

$POLAR2GRID_HOME/bin/polar2grid.sh -r viirs_sdr -w geotiff -f ~/raw_data/*.h5 --num-workers 4 --progress --list-products

#Produce a color images both in True Color and False Color.

$POLAR2GRID_HOME/bin/polar2grid.sh -r viirs_sdr -w geotiff -f ~/raw_data/*.h5 --num-workers 12 --progress -p true_color false_color

#Produce DNB (day night Band ) images. Useful for night viewing

$POLAR2GRID_HOME/bin/polar2grid.sh -r viirs_sdr -w geotiff -f ~/raw_data/*.h5 --num-workers 12 --progress -p adaptive_dnb dynamic_dnb histogram_dnb

```