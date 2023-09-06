In this document, we discuss further advanced topics.

# Table of Content

- [Table of Content](#table-of-content)
- [Installing the project on an Ubuntu host](#installing-the-project-on-an-ubuntu-host)
- [Training models](#training-models)
  - [Training Dataset](#training-dataset)
  - [3. Prepare label script](#3-prepare-label-script)
  - [4. Merge Label script](#4-merge-label-script)
  - [5. Model Training](#5-model-training)


# Installing the project on an Ubuntu host

While we recommend you use this project in a Docker environment, in theory, it is possible to set this project on an Ubuntu host.
As of testing, we found that this project has some dependencies.
Thus, the version of libraries is crucial. 
Below are the components used with its version.

1. Ubuntu 22.04
2. python3.10.6
3. GDAL 3.4.1

After you have set up your Ubuntu machine, the following script will install Python3 and GDAL via apt.

```shell
$ sudo apt install -y python3.10 python3-pip
$ sudo apt install -y gdal-bin libgdal-dev  
$ export CPLUS_INCLUDE_PATH=/usr/include/gdal
$ export C_INCLUDE_PATH=/usr/include/gdal
```

Once you have Python3 and GDAL, you can use the following scripts to install all Python3 libraries needed for this project.
If the machine is intended to run multiple Python projects, we recommend you use some sort of virtual environment to prevent library conflict.

```shell
$ pip3 install GDAL==3.4.1
$ pip3 install basemap==1.3.6
$ pip3 install h5py==3.8.0
$ pip3 install ipykernel==6.22.0
$ pip3 install ipywidgets==8.0.5
$ pip3 install lightgbm==3.3.5
$ pip3 install matplotlib==3.6.3
$ pip3 install netCDF4==1.6.3
$ pip3 install numpy==1.23.5
$ pip3 install pandas==1.5.3
$ pip3 install pyinterpolate==0.3.7
$ pip3 install rasterio==1.3.6
$ pip3 install rioxarray
$ pip3 install scikit-learn==1.2.2
$ pip3 install wget==3.2
$ pip3 install xgboost==1.7.4
```

# Training models

If you want to train additional models, you can do it via our project.

$$ X = [Satellite, Landuse, DEM, Season, GPS] $$
$$ y = rainfall $$
$$ model(X) = \hat{y} $$
$$ model(Satellite, Landuse, DEM, Season, GPS) = \hat{rainfall} $$

Recalling the equation, we need to prepare data first. 
The data may seem to be the same as the prediction.
However, in theory, the model should be trained on a very large set of data (training dataset).
Therefore, we will talk about the training dataset first.

## Training Dataset

In general, the training dataset must include $X$ and $y$.
In our case, 

$$ X = [Satellite, Landuse, DEM, Season, GPS] $$
$$ y = rainfall $$

Since the Landuse and DEM are sort of constant, there is not much to discuss.
All you need is the Tif files of both data.

- Landuse: `lu_all_match_mode.tif`
- DEM: `Thailand_DEM_match.tif`

`Satellite` and rainfall ($y$) are harder to get.

First, you need to consider the size of the training data you want to have.
Let's say we will train the model on the data for the year 2022.
Thus, you will need to have `Satellite` and rainfall ($y$) data for the year 2022. 

The `Satellite` can be obtained using the script discussed in the main README.md file.
The rainfall ($y$) is a 


First, you need to have training data. 


## 3. Prepare label script

Before we can run this script, you have to make sure you have the following files ready.

1. CSV label files
2. IMERG 1KM
3. GSMAP 1KM
4. Landuse - `lu_all_match_mode.tif`
5. DEM - `Thailand_DEM_match.tif`

This script will extend the columns of the CSV label file.
Extended columns are listed in the `config.py`.

```yaml
  column_names:
    # column: column_name
    imerg: IMERG
    gsmap: GSMAP
    dem: DEM
    month: month
    season: season
    landuse: lun
    lat: lat_sat
    lon: lon_sat
```

imerg: The data is queried from the IMERG 1KM.
gsmap: The data is queried from the GSMAP 1KM.
dem: the data is queried from `Thailand_DEM_match.tif`.
month: the data is calculated from the date.
season: the data is calculated from the date and a configuration in the `config.py`.
landuse: the data is queried from the `Thailand_DEM_match.tif`
lat: the data is an integer of `lat` from the satellite data.
lon: the data is an integer of `lon` from the satellite data.

Below is the full configuration of Prepare label script

```yaml
prepare_label:
  mode: 1 # 0: singleband, 1: multiband
  source_path: /root/projects/data/label 
  destination_path: /root/projects/data_preprocessed/label_multiband
  imerg_source: /root/projects/data_preprocessed/IMERG_multiband/*/1KM
  gsmap_source: /root/projects/data_preprocessed/GSMAP_multiband/*/1KM
  dem_source: /root/projects/data/DEM/Thailand_DEM_match.tif
  landuse_source: /root/projects/data/landuse/lu_all_match_mode.tif
  resolution:
    satellite: 0.01
  season:
    # season: [list of month]
    rain: [5,6,7,8,9,10]
    winter: [11,12,1]
    sunny: [2,3,4]
  column_names:
    imerg: IMERG
    gsmap: GSMAP
    dem: DEM
    month: month
    season: season
    landuse: lun
    lat: lat_sat
    lon: lon_sat
  ignore_rain_nan: False # will exclude any row with rain(mm) = nan
  threads: -1 # -1: use all server threads
  log_level: 10
```

The CSV label must contain `lon` and `lat` columns. 
By design, each row is information from each weather station (station_name, rain(mm), station lat and lon). 
We use this location to query information from other `tif` files. 
If the station lat and lon do not fall into an area inside of a `tif` the script will fail.


## 4. Merge Label script

Nothing fancy just concatenating all prepared CSVs into one single file easy for model training.

```yaml
merge_label:
  source_path: /root/projects/data_preprocessed/label_multiband
  destination_path: /root/projects/data_final
  output_name: rain
  auto_increment: True
  drop_na: False
  log_level: 10
```

Here we have an `auto-increment` function. 
If `True`, an output file will have an incremental suffix. 
If not, the output will replace an existing one.
`drop_na` as `True` will drop any row with `rain(mm)` as `NA`.

## 5. Model Training

[TO DO]