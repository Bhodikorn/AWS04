from components.logger import init_logger
import logging
import yaml
from glob import glob
import os
import multiprocessing as mp
from multiprocessing import Manager 
from itertools import product

from sklearn.base import RegressorMixin
import pickle
import rioxarray
import xarray
from xarray.core.dataset import Dataset
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def daterange(start_date, stop_date):
    for n in range(int((stop_date - start_date).days)):
        yield start_date + timedelta(n)

def load_raster(dataset:Dataset, source:str, band_name:str, look_up_band_name:str=None) -> Dataset:
    rds = rioxarray.open_rasterio(source, decode_times=False, lock=False)
    # modify Nan
    rds = rds.where(rds != rds.rio.nodata)
    rds.rio.write_nodata(rds.rio.nodata, encoded=True, inplace=True)
    
    band_idx = 0
    if(look_up_band_name != None):
        band_idx = rds.attrs['long_name'].index(look_up_band_name)
        rds.attrs['long_name'] = look_up_band_name

    dataset[band_name] = rds[band_idx]
    rds.close()
    
    return dataset

def get_season_from_date(date:datetime) -> int:
    season:int = list(filter(lambda x: date.month in x[1], SEASON.items()))[0][0]
    return season

# def get_predict(dataset, date, lon, lat):
#     season = get_season_from_date(date)

#     sel = dataset.sel(x=lon, y=lat)
#     lun,dem,imerg,gsmap,_ = map(lambda x: sel[x].values, list(dataset.keys()))
#     # skip if any value is nan
#     if(np.isnan([lun,dem,imerg,gsmap]).any()):
#         return
#     # actual predict
#     # Create X with all value set to 0
#     X = pd.DataFrame(columns=['IMERG','GSMAP','DEM',
#                                 'lun_1','lun_2','lun_3','lun_4','lun_5','lun_6','lun_7','lun_8',
#                                 'Season_rain','Season_sunny','Season_winter',
#                                 'lat_sat','lon_sat'],
#                     data=[[0] * 16])
#     X.loc[0, 'IMERG'] = imerg
#     X.loc[0, 'GSMAP'] = gsmap
#     X.loc[0, 'DEM'] = dem
#     X.loc[0, f"lun_{int(lun)}"] = 1
#     X.loc[0, f'Season_{season}'] = 1
#     X.loc[0, f'lat_sat'] = int(lat)
#     X.loc[0, f'lon_sat'] = int(lon)

#     # Load model
#     with open(MODEL_PATH, 'br') as f:
#         model:RegressorMixin = pickle.load(f)
#     yhat = model.predict(X)
#     dataset['predict'].loc[{'y':lat.values, 'x':lon.values}] = yhat[0][0]


def predict(date:datetime, id:int=0):
    logger.info(f"Predicting date={date.strftime('%d-%m-%Y')}")
    # Checking existing for IMERG and GSMAP tiff file
    imerg_files:list[str] = glob(f"{IMERG_SOURCE}/*{date.strftime('%Y%m%d')}*.tiff")
    assert len(imerg_files) == 1, f"expect len(imerg_files)=1 but got {len(imerg_files)}. {imerg_files=}"
    imerg_file:str = imerg_files[0]

    gsmap_files:list[str] = glob(f"{GSMAP_SOURCE}/*{date.strftime('%Y%m%d')}*.tiff")
    assert len(gsmap_files) == 1, f"expect len(gsmap_files)=1 but got {len(gsmap_files)}. {gsmap_files=}"
    gsmap_file:str = gsmap_files[0]

    # Check the existing of model
    assert os.path.exists(MODEL_PATH), f"Path {MODEL_PATH=} is not exsit."
    # Load model
    with open(MODEL_PATH, 'br') as f:
        model:RegressorMixin = pickle.load(f)
    
    season = get_season_from_date(date)

    # Prepare master raster
    dataset = xarray.Dataset()
    load_raster(dataset=dataset, source=LANDUSE_PATH, band_name='landuse')
    load_raster(dataset=dataset, source=DEM_PATH, band_name='dem')
    load_raster(dataset=dataset, source=imerg_file, band_name='imerg', look_up_band_name=IMERG_COLUMN)
    load_raster(dataset=dataset, source=gsmap_file, band_name='gsmap', look_up_band_name=GSMAP_COLUMN)
    
    data_predict = xarray.DataArray(
                        np.full((len(dataset.y),len(dataset.x)), np.nan,dtype=float), 
                        dims=['y','x'], 
                        name='predict')
    data_predict.rio.write_nodata(np.nan, encoded=True, inplace=True)
    dataset['predict'] = data_predict

    count = 0
    for lon,lat in product(dataset.x, dataset.y):
        sel = dataset.sel(x=lon, y=lat)
        lun,dem,imerg,gsmap,_ = map(lambda x: sel[x].values, list(dataset.keys()))
        # skip if any value is nan
        if(np.isnan([lun,dem,imerg,gsmap]).any()):
            continue
        # actual predict
        # Create X with all value set to 0
        X = pd.DataFrame(columns=['season_rain','season_sunny','season_winter',
                                'lun_1','lun_2','lun_3','lun_4','lun_5','lun_6','lun_7','lun_8',
                                'DEM','IMERG_precipitationCal','GSMAP_hourly_g',
                                'lat_sat','lon_sat'],
                        data=[[0] * 16])
        X.loc[0, 'IMERG_precipitationCal'] = imerg
        X.loc[0, 'GSMAP_hourly_g'] = gsmap
        X.loc[0, 'DEM'] = dem
        X.loc[0, f"lun_{int(lun)}"] = 1
        X.loc[0, f'season_{season}'] = 1
        X.loc[0, f'lat_sat'] = int(lat)
        X.loc[0, f'lon_sat'] = int(lon)
        yhat = model.predict(X)
        # print(yhat)
        dataset['predict'].loc[{'y':lat.values, 'x':lon.values}] = yhat[0]
        if(count % 10000 == 0):
            print(id, count, len(dataset.x) * len(dataset.y))
        count += 1
    destination = os.path.join(DESTINATION_PATH, f"{OUTPUT_NAME_PREFIX}_{date.strftime('%Y%m%d')}.tiff")
    dataset.rio.to_raster(destination)

def _main():

    dates = daterange(START_DATE, STOP_DATE + timedelta(days=1))
    # loop through target date
    # manager = Manager()
    # lock = manager.Lock()
    pool = mp.Pool(THREADS)
    try:
        results = [pool.apply_async( predict, args=(date, id) ) for id, date in enumerate(dates)]
        results = [result.get() for result in results]
    except Exception as e:
        logger.error(f"{e=}")
        raise e
    finally:
        pool.close()
        pool.join()


if __name__ == "__main__":
    # Logger
    init_logger(name='main', filename='inference')
    logger = logging.getLogger('main')
    
    with open('./config.yaml', 'r') as f:
        config = yaml.safe_load(f)['inference']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    model_path={config['model_path']}
    dem_path={config['dem_path']}
    landuse_path={config['landuse_path']}
    imerg_source={config['imerg_source']}
    imerg_column={config['imerg_column']}
    gsmap_source={config['gsmap_source']}
    gsmap_column={config['gsmap_column']}
    destination_path={config['destination_path']}
    season={config['season']}
    threads={config['threads']}
    output_name_prefix={config['output_name_prefix']}
    log_level={config['log_level']}
    """)

    logger.setLevel(config['log_level'])
    THREADS:int = config['threads']
    if(THREADS == -1):
        THREADS = mp.cpu_count()

    START_DATE:datetime = datetime.strptime(config['start_date'], '%d-%m-%Y')
    STOP_DATE:datetime = datetime.strptime(config['stop_date'], '%d-%m-%Y')
    MODEL_PATH:str = config['model_path']
    IMERG_SOURCE:str = config['imerg_source']
    GSMAP_SOURCE:str = config['gsmap_source']
    IMERG_COLUMN:str = config['imerg_column']
    GSMAP_COLUMN:str = config['gsmap_column']
    DEM_PATH:str = config['dem_path']
    LANDUSE_PATH:str = config['landuse_path']
    DESTINATION_PATH:str = config['destination_path']
    SEASON:dict = config['season']
    OUTPUT_NAME_PREFIX:str = config['output_name_prefix']
    _main()