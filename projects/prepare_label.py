from components.logger import init_logger
from components.helper_download import date_range
import logging
import yaml
from glob import glob
import os 
from datetime import datetime
import multiprocessing as mp
from multiprocessing import Manager 
import gc
import time
import math

import pandas as pd
import rioxarray
from shapely.geometry import Polygon, Point, box
from pyproj import Transformer

def _get_data_from_rds(rds, station_point:Point, area_width:float) -> float:
    # Find nearest area from point
    lat_idx = abs(rds.y - station_point.y).argmin()
    lon_idx = abs(rds.x - station_point.x).argmin()
    area_center = Point(rds.x[lon_idx], rds.y[lat_idx])
    # create the area
    area = _create_box(area_center, area_width)
    # Make sure the station point does belong to the area
    assert area.contains(station_point), f"station_point={station_point} is not in this area={area} width={area_width}."
    # print(rds[0,lat,lon])
    if(MODE == MODE_SINGLEBAND):
        return rds[0,lat_idx, lon_idx]
    elif(MODE == MODE_MULTIBAND):
        return rds[:,lat_idx, lon_idx]
    else:
        raise ValueError(f"{MODE=} is in valid.")

def _create_box(point:Point, rect_width:float) -> Polygon:
    xmin, ymin = point.x - (rect_width / 2), point.y - (rect_width / 2)
    xmax, ymax = point.x + (rect_width / 2), point.y + (rect_width / 2)
    poly_box = box(minx=xmin, miny=ymin, maxx=xmax, maxy=ymax)
    return poly_box

def _get_data_imerg(date:datetime, point:Point) -> float:
    # look up for imerg list
    search_str = f"{IMERG_SOURCE}/IMERG_{date.strftime('%Y%m%d')}*.tiff"
    list_file:list[str] = glob(search_str)
    assert len(list_file) == 1, f"Expect only 1 result but got {len(list_file)}. list_file={list_file}. date={date}|search_str={search_str}|func=imerg"
    rds = rioxarray.open_rasterio(list_file[0], decode_times=False, lock=False)
    data = _get_data_from_rds(rds, point, area_width=SATELLITE_WIDTH)
    names = rds.attrs['long_name']
    rds.close()
    del rds
    if(MODE == MODE_SINGLEBAND):
        return data.values #type:ignore
    elif(MODE == MODE_MULTIBAND):
        return data.values, names #type:ignore

def _get_data_gsmap(date:datetime, point:Point) -> float:
    # look up for gsmap list
    search_str = f"{GSMAP_SOURCE}/GSMAP_{date.strftime('%Y%m%d')}*.tiff"
    list_file:list[str] = glob(search_str)
    assert len(list_file) == 1, f"Expect only 1 result but got {len(list_file)}. list_file={list_file}. date={date}|search_str={search_str}|func=gsmap"
    rds = rioxarray.open_rasterio(list_file[0], decode_times=False, lock=False)
    data = _get_data_from_rds(rds, point, area_width=SATELLITE_WIDTH)
    names = rds.attrs['long_name']
    rds.close()
    del rds
    if(MODE == MODE_SINGLEBAND):
        return data.values #type:ignore
    elif(MODE == MODE_MULTIBAND):
        return data.values, names #type:ignore

def _get_data_dem(point:Point) -> float:
    # look up for dem list
    # E = int(point.x)
    # N = int(point.y)
    # if(DEM_SOURCE == 'ASTGM'):
    #     filename = f'./data/DEM/ASTGTM/ASTGTMV003_N{N:02d}E{E:03d}_dem.tif'
    #     rds = rioxarray.open_rasterio(filename, decode_times=False, lock=False)
    #     data = _get_data_from_rds(rds, point, area_width=1)
    #     rds.close()
    #     del rds
    # elif(DEM_SOURCE == 'Thailand'):
    # point = _reproject_point(point)
    rds = rioxarray.open_rasterio(DEM_SOURCE, decode_times=False, lock=False)
    data = _get_data_from_rds(rds, point, area_width=SATELLITE_WIDTH)
    # data = _get_data_from_rds(rds, point, area_width=3360)
    rds.close()
    del rds
        # data = _get_data_from_rds(RDS_DEM, point, area_width=0.001*3)

    return data.values #type:ignore

def _get_data_landuse(point:Point) -> float:
    # point = _reproject_point(point)
    rds = rioxarray.open_rasterio(LANDUSE_SOURCE, decode_times=False, lock=False)
    data = _get_data_from_rds(rds, point, area_width=SATELLITE_WIDTH)
    # data = _get_data_from_rds(rds, point, area_width=3360)
    rds.close()
    del rds
    return data.values

def _reproject_point(from_point:Point) -> Point:
    transformer = Transformer.from_crs( "EPSG:4326", "EPSG:32647", always_xy=True)
    x,y = transformer.transform(from_point.x, from_point.y)
    assert (math.isinf(x) == False) and (math.isinf(y) == False),  f"Point={from_point} converts to {x=},{y=}"
    point = Point(x,y)
    return point


###### Catagory function #######
def get_region(province:str) -> str:
    region = DF_REGION.RegionTMD[DF_REGION['station_name_th'] == province]
    assert len(region) == 1, f"{province=} does not return single region {list(region)=}"
    return region.values[0]

def get_lun_definition(lun:int) -> str:
    lun_def = 'Miscellaneous'
    if(lun in DICT_LUN.keys()):
        lun_def = DICT_LUN[lun]
    return lun_def

def convert_dem_to_cat(dem:float) -> str:
    value = None
    if(pd.isna(dem)):
        return pd.NA
    if (dem <0):
        value ='below_0'
    elif (dem >=0 and dem <=100):
        value ='0-100'
    elif (dem >100 and dem <=300):
        value ='101-300'
    elif (dem >300 and dem <=600):
        value ='300-600'
    elif (dem >600):
        value ='600_more'
    else:
        value = 'unknown'
    return value

def get_dem_cat_th(dem_cat:str) -> str:
    if(pd.isna(dem_cat)):
        return pd.NA
    assert dem_cat in DICT_DEM_CAT_TH.keys(), f"{dem_cat=} {DICT_DEM_CAT_TH.keys()}"
    return DICT_DEM_CAT_TH[dem_cat]

def convert_rain_to_cat(rain:float) -> int:
    # 1: ไม่ตก < 0.1
    # 2: ฝนเล็กน้อย (Light rain) มีปริมาณฝนตั้งแต่ 0.1 มิลลิเมตร 10.0 มิลลิเมตร 
    # 3: ฝนปานกลาง (Moderate rain) มีปริมาณฝนตั้งแต่ 10.1 มิลลิเมตร 35.0 มิลลิเมตร 
    # 4: ฝนหนัก (Heavy rain) มีปริมาณฝนตั้งแต่ 35.1 มิลลิเมตร 90.0 มิลลิเมตร 
    # 5: ฝนหนักมาก (Very heavy rain) มีปริมาณฝนตั้งแต่ 90.1 มิลลิเมตรขึ้นไป
    value = None
    if (rain <0.1):
        value = 1
    elif (rain >=0.1 and rain <=10.0):
        value = 2
    elif (rain >10 and rain <=35):
        value = 3
    elif (rain >35 and rain <=90):
        value = 4
    elif (rain >90):
        value = 5  
    else:
        value = pd.NA
    return value 

def get_rain_cat_th(rain_cat:str) -> str:
    if(pd.isna(rain_cat)):
        return pd.NA
    
    assert rain_cat in DICT_RAIN_CAT_TH.keys(), f"{rain_cat=} {DICT_RAIN_CAT_TH.keys()}"
    return DICT_RAIN_CAT_TH[rain_cat]


def add_values(df:pd.DataFrame) -> pd.DataFrame:
    start = time.time()
    for i in df.index:
        if((i+1)%250 == 0):
            print(time.time() - start, f"{i+1}/{len(df.index)}")
            start = time.time()
            gc.collect()

        x,y = df.lon[i], df.lat[i]
        # if(x < y):
        #     x,y = df.lat[i], df.lon[i]

        station_point = Point(x, y)
        # MONTH_COLUMN_NAME
        date = datetime.strptime(df.date[i], '%Y-%m-%d')
        df.loc[i, MONTH_COLUMN_NAME] = date.month

        if(MODE == MODE_SINGLEBAND):
            # IMERG_COLUMN_NAME
            data_imerg = _get_data_imerg(date, station_point)
            df.loc[i, IMERG_COLUMN_NAME] = data_imerg
            # GSMAP_COLUMN_NAME
            data_gsmap = _get_data_gsmap(date, station_point)
            df.loc[i, GSMAP_COLUMN_NAME] = data_gsmap
        elif(MODE == MODE_MULTIBAND):
            # IMERG_COLUMN_NAME
            data_imergs, names = _get_data_imerg(date, station_point)
            for data_idx, name in enumerate(names):
                df.loc[i, f"{IMERG_COLUMN_NAME}_{name}"] = data_imergs[data_idx]
            # GSMAP_COLUMN_NAME
            data_gsmaps, names = _get_data_gsmap(date, station_point)
            for data_idx, name in enumerate(names):
                df.loc[i, f"{GSMAP_COLUMN_NAME}_{name}"] = data_gsmaps[data_idx]


        # DEM_COLUMN_NAME
        data_dem = _get_data_dem(station_point)
        assert len(data_dem) == 1
        if(data_dem[0] != -32767):
            df.loc[i, DEM_COLUMN_NAME] = data_dem[0]

        # SEASON_COLUMN_NAME
        item = list(filter(lambda x: date.month in x[1], SEASON_DICT.items()))
        assert len(item) == 1, f"Filter of mont={date.month} on SEASON_DICT={SEASON_DICT} resolves in more than 1 result={item}"
        season = item[0][0]
        df.loc[i, SEASON_COLUMN_NAME] = season

        # LANDUSE
        data_landuse = _get_data_landuse(station_point)
        assert len(data_landuse) == 1
        df.loc[i, LANDUSE_COLUMN_NAME] = data_landuse[0]
        
        # LAT, LON
        df.loc[i, LAT_COLUMN_NAME] = int(station_point.y)
        df.loc[i, LON_COLUMN_NAME] = int(station_point.x)

    return df

def add_values_cat(df:pd.DataFrame) -> pd.DataFrame:
    region = df['province'].apply(get_region).rename(REGION_COLUMN_NAME)
    lun_def = df[LANDUSE_COLUMN_NAME].apply(get_lun_definition).rename(LANDUSE_DEF_COLUMN_NAME)

    dem_cat = df[DEM_COLUMN_NAME].apply(convert_dem_to_cat).rename(DEM_CAT_COLUMN_NAME)
    dem_cat_th = dem_cat.apply(get_dem_cat_th).rename(DEM_CAT_TH_COLUMN_NAME)

    rain_cat = df['rain(mm)'].apply(convert_rain_to_cat).rename(RAIN_CAT_COLUMN_NAME)
    rain_cat_th = rain_cat.apply(get_rain_cat_th).rename(RAIN_CAT_TH_COLUMN_NAME)

    df = pd.concat([df, region,lun_def,dem_cat,dem_cat_th,rain_cat,rain_cat_th], axis=1)

    # Convert each satllite column to category and concatenate to DataFrame
    satellite_columns = filter(lambda name: 'IMERG' in name or 'GSMAP' in name ,df.columns)
    for column_name in satellite_columns:
        # satellite_cat -> IMERG_precipitationCal_cat
        new_name = SATELLITE_CAT_COLUMN_NAME.replace('satellite',column_name)
        series = df[column_name].apply(convert_rain_to_cat).rename(new_name)
        df = pd.concat([df, series], axis=1)
    return df


def save_file(df:pd.DataFrame, filename:str, lock) -> None:
    if(os.path.exists(DESTINATION_PATH) == False):
        lock.acquire()
        if(os.path.exists(DESTINATION_PATH) == False):
            os.makedirs(DESTINATION_PATH)
        lock.release() 

    target_filename = os.path.join(DESTINATION_PATH,filename)
    df.to_csv(target_filename, encoding="TIS-620")


def task(target_file:str, lock) -> None:
    try:
        logger.info(f"Processing={target_file}")
        # get csv
        df = pd.read_csv(f'{SOURCE_PATH}/{target_file}', encoding="TIS-620")
        if(IGNORE_RAIN_NAN == True):
            df.dropna(subset='rain(mm)', inplace=True)
        # set columns to NA
        # df[IMERG_COLUMN_NAME] = pd.NA
        # df[GSMAP_COLUMN_NAME] = pd.NA
        df[DEM_COLUMN_NAME] = pd.NA
        df[MONTH_COLUMN_NAME] = pd.NA
        df[SEASON_COLUMN_NAME] = pd.NA
        df[LANDUSE_COLUMN_NAME] = pd.NA
        df[LAT_COLUMN_NAME] = pd.NA
        df[LON_COLUMN_NAME] = pd.NA

        df = add_values(df)

        # update satellite data by its value divided by 10
        satellite_columns = filter(lambda name: 'IMERG' in name or 'GSMAP' in name ,df.columns)
        df.update(df[satellite_columns].apply(lambda x: x/10))

        df = add_values_cat(df)
        save_file(df, target_file, lock)
    except Exception as e:
        logger.error(f"{e=}\nError from '{target_file}'")
        # raise e


def main() -> None:
    # look for all csv to process
    temp:list[str] = glob(f"{SOURCE_PATH}/*.csv")
    list_of_raw = list(map(lambda x: os.path.split(x)[1], temp))
    temp:list[str] = glob(f'{DESTINATION_PATH}/*.csv')
    list_of_preprocessed = list(map(lambda x: os.path.split(x)[1], temp))

    logger.debug(f"list_of_raw={list_of_raw}")
    logger.debug(f"list_of_preprocessed={list_of_preprocessed}")
    logger.info(f"Found list_of_raw={len(list_of_raw)} and list_of_preprocessed={len(list_of_preprocessed)}")
    
    list_of_unprocesses:list[str] = list(set(list_of_raw).difference(list_of_preprocessed))
    if(len(list_of_unprocesses) == 0):
        # Nothing to process
        logger.info('Nothing to do')
    else:
        list_of_unprocesses.sort()
        logger.info(f"list_of_unprocesses={list_of_unprocesses}")
        manager = Manager()
        lock = manager.Lock()
        pool = mp.Pool(THREADS)
        results = [pool.apply_async( task, args=(unprocess, lock) ) for unprocess in list_of_unprocesses]
        results = [result.get() for result in results]
        pool.close()
        pool.join()

if __name__ == "__main__":
    # Logger
    init_logger(name='main', filename='prepare_label')
    logger = logging.getLogger('main')
    
    with open('./prepare_label_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['prepare_label']

    logger.info(f"""=====CONFIG=====
    mode={config['mode']}
    source_path={config['source_path']}
    destination_path={config['destination_path']}
    imerg_source={config['imerg_source']}
    gsmap_source={config['gsmap_source']}
    dem_source={config['dem_source']}
    landuse_source={config['landuse_source']}
    region_source={config['region_source']}
    resolution={config['resolution']}
    season={config['season']}
    column_names={config['column_names']}
    ignore_rain_nan={config['ignore_rain_nan']}
    threads={config['threads']}
    log_level={config['log_level']}
    """)

    logger.setLevel(config['log_level'])
    MODE:int = config['mode']
    assert MODE in [0,1], f"{MODE=} is in valid. Only 0 or 1 is support. Read config file for description."
    MODE_SINGLEBAND:int = 0
    MODE_MULTIBAND:int= 1

    SOURCE_PATH:str = config['source_path']
    DESTINATION_PATH:str = config['destination_path']

    IMERG_SOURCE:str = config['imerg_source']
    GSMAP_SOURCE:str = config['gsmap_source']
    DEM_SOURCE:str = config['dem_source']
    # valid_dem_source = ['ASTGM', 'Thailand']
    # assert DEM_SOURCE in valid_dem_source, f"dem_source must be {valid_dem_source}. Got {DEM_SOURCE}"
    LANDUSE_SOURCE:str = config['landuse_source']
    REGION_SOURCE:str = config['region_source']

    IMERG_COLUMN_NAME:str = config['column_names']['imerg']
    GSMAP_COLUMN_NAME:str = config['column_names']['gsmap']
    SATELLITE_CAT_COLUMN_NAME:str = config['column_names']['satellite_category']
    DEM_COLUMN_NAME:str = config['column_names']['dem']
    DEM_CAT_COLUMN_NAME:str = config['column_names']['dem_cateogy']
    DEM_CAT_TH_COLUMN_NAME:str = config['column_names']['dem_cateogy_th']
    LANDUSE_COLUMN_NAME:str = config['column_names']['landuse']
    LANDUSE_DEF_COLUMN_NAME:str = config['column_names']['landuse_def']
    RAIN_CAT_COLUMN_NAME:str = config['column_names']['rain_category']
    RAIN_CAT_TH_COLUMN_NAME:str = config['column_names']['rain_category_th']
    REGION_COLUMN_NAME:str = config['column_names']['region']
    MONTH_COLUMN_NAME:str = config['column_names']['month']
    SEASON_COLUMN_NAME:str = config['column_names']['season']
    LAT_COLUMN_NAME:str = config['column_names']['lat']
    LON_COLUMN_NAME:str = config['column_names']['lon']


    IGNORE_RAIN_NAN:bool = config['ignore_rain_nan']

    SATELLITE_WIDTH:float = config['resolution']['satellite']

    SEASON_DICT:dict = config['season']

    # Category Dictionary
    DF_REGION:pd.DataFrame = pd.read_csv(REGION_SOURCE)
    DICT_LUN:dict = dict({1:'Paddy',
                    2:'Crop',
                    3:'Orchard/Trees',
                    4:'Others Ag',
                    5:'Urban',
                    6:'Forest',
                    7:'Water body',
                    8:'Miscellaneous'
                    })
    DICT_DEM_CAT_TH:dict = dict({'below_0':'ต่ำศุนย์',
                        '0-100':'ที่ราบ',
                        '101-300':'ที่ดอน',
                        '300-600':'ที่ราบสูงเนินเขา',
                        '600_more':'เขาสูง',
                        'unknown':'unknown'
                        })
    DICT_RAIN_CAT_TH:dict = dict({1:'ฝนไม่ตก',
                        2:'ฝนเล็กน้อย',
                        3:'ฝนปานกลาง',
                        4:'ฝนหนัก',
                        5:'ฝนหนักมาก'
                        })

    THREADS:int = config['threads']
    if(THREADS == -1):
        THREADS = mp.cpu_count()
    # xarray.set_options(file_cache_maxsize=32)

    # RDS_DEM = None
    # if DEM_SOURCE == 'Thailand':
    #     RDS_DEM = rioxarray.open_rasterio('./data/DEM/Thailand_DEM.tif', decode_times=False, lock=False)
    #     # RDS_DEM = RDS_DEM.rio.reproject(dst_crs="EPSG:4326")
    # RDS_LANDUSE = rioxarray.open_rasterio('./data/landuse/lu_all_30m_utm.tif', decode_times=False, lock=False)


    main()
    