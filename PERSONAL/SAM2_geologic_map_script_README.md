# Meta SAM2 Geologic Map Integration

Allows for use of Meta SAM2 model to identify and vectorize regions of a geologic map. Install steps important!

## Table of Contents

1. [Overview](#overview)
2. [Dependencies](#dependencies)
3. [Usage](#usage)
4. [Configuration/Install](#configuration_install)
5. [Important Notes](#important_notes)

## Overview

Accepts image file of a geologic map (or other image with features that the user wishes to isolate/identify), then allows for manual object selection by clicking parts of the image. Meta's Segment Anything Model 2 is then run on the image, and the mask output is shown. This output is then rasterized, then vectorized, and kept to the same dimensions as the original image to allow for easy georeferencing by using the GCPs saved from georeferencing the original map image. 

## Dependencies

numpy
tkinter
torch
matplotlib
Pillow (PIL)
rasterio
gdal
ogr
PyQt5

All dependencies are checked for and installed if missing upon script run.


## Usage

Upon running the script, all required packages are checked and installed if missing. The user is then prompted to select their input image as well as the output file. Along with the designated output file, a few other vector files will be generated, so it is recommended to place the output file in its own folder so as to keep things contained and avoid overwrite issues with other outputs. The user is then prompted to select the objects of interest by placing one or more points. Points on visually distinct objects will result in different masks, but multiple points within the same object will contribute to further refinement of the output mask for that object. Once these points are confirmed, the model is then run on the image and an output is displayed, showing the masks as translucent colored shapes over selected objects. Once the result window is closed, the masks are rasterized, then vectorized. The output raster and vector masks are set to be the same size/shape as the input map image, so that they can be easily georeferenced using saved GCPs from georeferencing the original map. 

## Configuration_Install

Along with the required packages listed above, this script also requires install/download of two components of the SAM2 model itself: installing the model, and downloading the model checkpoints. These can be done by the following steps (BEFORE RUNNING THE SCRIPT!)

`cd <main_repo_folder>`
`pip install -e ".[demo]"` (installs sam2)
`cd .\checkpoints\`
`bash ./download_ckpts.sh` (downloads checkpoints)

An important note for being able to download the checkpoints: `download_ckpts.sh` should be in LF line endings, NOT CRLF. It should be in LF by default, but if it isn't, make sure to change it before running `bash ./download_ckpts.sh`. This can be done by opening `download_ckpts.sh` in VScode, then clicking "CRLF" in the bottom right corner, then selecting LF. By default, Git changes line endings to CRLF, but this repository should be set to default to LF instead. 

## Important_Notes

- When running in conda environments (or potentially any python interpreter), GDAL occasionally returns an error saying it either isn't installed or cannot be found. If it has been installed (which it should be at the start of the script), it often means that the PATH environment variable to gdal is missing. This fix should be incorporated into the start of the script, but if it doesn't work for some reason, it can be fixed by manually setting the environment variable: assign GDAL_DATA to "anaconda3\envs\conda_env\Library\share\gdal". A system restart may be needed for the changes to take place. 

- Often the output vector is quite messy. The easiest way to clean it (at least as of now) is to select all polygons (CTRL/CMD+A) in QGIS or other GIS software, then deselect the few you want to keep, then delete those that are still selected. 

- Due to the above known issue, the best application for this script at the moment is to generate a mask to aid in cropping a map to the area of interest. With further refinement, this tool may be able to be used to rapidly digitize geologic maps, but for now the output is simply too messy to be used. 