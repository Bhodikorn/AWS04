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

from prepare_label import get_region, get_lun_definition, convert_dem_to_cat, get_dem_cat_th, convert_rain_to_cat, get_rain_cat_th

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

def predict(date:datetime):
    logger.info(f"Predicting date={date.strftime('%d-%m-%Y')}")
    # Checking existing for IMERG and GSMAP tiff file
    imerg_files:list[str] = glob(f"{IMERG_SOURCE}/*{date.strftime('%Y%m%d')}*.tiff")
    assert len(imerg_files) == 1, f"expect len(imerg_files)=1 but got {len(imerg_files)}. {imerg_files=}"
    imerg_file:str = imerg_files[0]

    gsmap_files:list[str] = glob(f"{GSMAP_SOURCE}/*{date.strftime('%Y%m%d')}*.tiff")
    assert len(gsmap_files) == 1, f"expect len(gsmap_files)=1 but got {len(gsmap_files)}. {gsmap_files=}"
    gsmap_file:str = gsmap_files[0]
    
    # Check the existing of model
    for predict_dict in PREDICT_COLUMNS:
        # Check in one go. So if one fails we won't spend time running.
        model_path = os.path.join(MODEL_SOURCE, predict_dict['model'])
        assert os.path.exists(model_path), f"Path {model_path=} is not exsit."

    season = get_season_from_date(date)


    # Prepare master raster
    dataset = xarray.Dataset()
    load_raster(dataset=dataset, source=LANDUSE_PATH, band_name='landuse')
    load_raster(dataset=dataset, source=DEM_PATH, band_name='dem')
    load_raster(dataset=dataset, source=imerg_file, band_name='imerg', look_up_band_name=IMERG_COLUMN)
    load_raster(dataset=dataset, source=gsmap_file, band_name='gsmap', look_up_band_name=GSMAP_COLUMN)
    
    # Get Dataframe from Xarray
    df = dataset.to_dataframe()
    # Prepare X
    # Reset multiindex so wa can manipulate them
    X_df = df.reset_index()
    # Drop any row with Nan value
    X_df.dropna(inplace=True)
    # Create Required columns
    # lon_sat, lat_sat
    X_df['lon_sat'] = X_df['x'].astype(int)
    X_df['lat_sat'] = X_df['y'].astype(int)
    # season
    X_df['season_rain'] = np.zeros(len(X_df.x), dtype=int)
    X_df['season_sunny'] = np.zeros(len(X_df.x), dtype=int)
    X_df['season_winter'] = np.zeros(len(X_df.x), dtype=int)
    X_df[f"season_{season}"] = 1
    # lun
    lun = pd.get_dummies(X_df.landuse.astype(float), prefix='LUN', dtype=int)
    X_df = pd.concat([X_df,lun],axis=1)
    # Rename column to the correct name
    X_df = X_df.rename(columns={'dem':'DEM',
                        'imerg':'IMERG_precipitationCal',
                        'gsmap':'GSMAP_hourly_g'})
    # reset index again
    X_df = X_df.reset_index().drop(columns='index')

    # Add category columns
    # Check if region category cache file exists
    region_csv = 'data/region/region_preprocess.csv'
    if(os.path.exists(region_csv) == False):
        # Create the 'region_csv'
        region_df = pd.read_csv('data/region/tmd_region_lat_lon.csv')
        region = []
        for lon, lat in zip(X_df.x, X_df.y):
            # lat = X_df.iloc[idx]['y']
            # lon = X_df.iloc[idx]['x']
            distance = (region_df.LAT - lat) ** 2 + (region_df.LONG - lon) ** 2
            select_row = np.argmin(distance)
            row = region_df.iloc[select_row]
            region.append(row.RegionTMD)
        region = pd.Series(region)
        region = pd.get_dummies(region, prefix='region', dtype=int)
        region['x'] = X_df.x
        region['y'] = X_df.y
        region.set_index(['x','y']).to_csv(region_csv)
    
    region = pd.read_csv('data/region/region_preprocess.csv')
    region = region.drop(columns=['y','x'])

    # X_df = X_df.join(region,on=['x','y'])

    DEM_cat = X_df['DEM'].apply(convert_dem_to_cat).rename('DEM_cat')
    DEM_cat = pd.get_dummies(DEM_cat, prefix='DEM_cat', dtype=int)
    dem_cats = ['DEM_cat_0-100',
                'DEM_cat_101-300', 
                'DEM_cat_300-600', 
                'DEM_cat_600_more',]
    for dem_cat in dem_cats:
        if(dem_cat not in DEM_cat.columns):
            DEM_cat[dem_cat] = 0

    IMERG_precipitationCal_cat = X_df['IMERG_precipitationCal'].apply(convert_rain_to_cat).rename('IMERG_precipitationCal_cat')
    IMERG_precipitationCal_cat = pd.get_dummies(IMERG_precipitationCal_cat, prefix='IMERG_precipitationCal_cat', dtype=int)
    # Check if all cat exists
    imerg_cats = ['IMERG_precipitationCal_cat_1',
                'IMERG_precipitationCal_cat_2', 
                'IMERG_precipitationCal_cat_3',
                'IMERG_precipitationCal_cat_4', 
                'IMERG_precipitationCal_cat_5',]
    for imerg_cat in imerg_cats:
        if(imerg_cat not in IMERG_precipitationCal_cat.columns):
            IMERG_precipitationCal_cat[imerg_cat] = 0

    GSMAP_hourly_g_cat = X_df['GSMAP_hourly_g'].apply(convert_rain_to_cat).rename('GSMAP_hourly_g_cat')
    GSMAP_hourly_g_cat = pd.get_dummies(GSMAP_hourly_g_cat, prefix='GSMAP_hourly_g_cat', dtype=int)
    # Check if all cat exists
    gsmap_cats = ['GSMAP_hourly_g_cat_1',
                'GSMAP_hourly_g_cat_2', 
                'GSMAP_hourly_g_cat_3',
                'GSMAP_hourly_g_cat_4', 
                'GSMAP_hourly_g_cat_5',]
    for gsmap_cat in gsmap_cats:
        if(gsmap_cat not in GSMAP_hourly_g_cat.columns):
            GSMAP_hourly_g_cat[gsmap_cat] = 0

    X_df = pd.concat([X_df,region,DEM_cat,IMERG_precipitationCal_cat,GSMAP_hourly_g_cat], axis=1)

    for predict_dict in PREDICT_COLUMNS:
        model_path = os.path.join(MODEL_SOURCE, predict_dict['model'])
        band_name = predict_dict['name']
        print(band_name)
        # Load model
        with open(model_path, 'br') as f:
            model:RegressorMixin = pickle.load(f)

        # Drop unwanted columns
        unwanted_columns = set(X_df.columns).difference(set(model.feature_names_in_))
        X = X_df.drop(columns=list(unwanted_columns))
        # Check the columns are match with required columns
        assert set(X.columns) == set(model.feature_names_in_), f"{X.columns=} {model.feature_names_in_=}"
        # Reindex columns becuase model requires the order to be excatly the same
        X = X.reindex(columns=model.feature_names_in_)

        # Predict
        X_df[band_name] = model.predict(X)

    X_df = X_df.set_index(['x','y'])
    
    for predict_dict in PREDICT_COLUMNS:
        model_path = os.path.join(MODEL_SOURCE, predict_dict['model'])
        band_name = predict_dict['name']
        # Set index
        # This works because the index is the same
        df[band_name] = X_df[band_name]

        # Put it back to a new layer
        dataset[band_name] = df[band_name].to_xarray().rio.write_nodata(np.nan, encoded=True, inplace=True)

    # df[region] = X_df[region]
    # # Put it back to a new layer
    # dataset[region] = df[region].to_xarray().rio.write_nodata(np.nan, encoded=True, inplace=True)

    destination = os.path.join(DESTINATION_PATH, f"{OUTPUT_NAME_PREFIX}_{date.strftime('%Y%m%d')}.tiff")
    dataset.rio.to_raster(destination)

def _main():

    dates = daterange(START_DATE, STOP_DATE + timedelta(days=1))
    for date in dates:
        predict(date)
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
    
    with open('./inference_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['inference']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    model_source={config['model_source']}
    predict_columns={config['predict_columns']}
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
    MODEL_SOURCE:str = config['model_source']
    PREDICT_COLUMNS:list = config['predict_columns']
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