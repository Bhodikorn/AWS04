from components.logger import init_logger
from components.helper_download import date_range
import logging
import yaml
import os
from glob import glob
import numpy as np
from datetime import datetime, timedelta
import gzip
import multiprocessing as mp
from multiprocessing import Manager
import netCDF4 as nc
import rioxarray
from rasterio.enums import Resampling
import xarray 
import pandas as pd
"""
preprocess will proform the following:
[x] 0. Bound to the target area
[x] 1. Interpolate from 10KM (0.1◦) to 1KM (0.01◦)
[x] 2. Aggregate to 1 day
    [x] GSMaP: 60 mins -> 1 day
[x] 3. Save the file as GeoTiff
"""
def _get_year_month_day(path:str) -> tuple[str,str, str]:
    l = path.split('/')
    year = l[-3]
    month = l[-2]
    day = l[-1]
    return year, month, day

def _get_datetime(path:str) -> datetime:
    year, month, day = _get_year_month_day(path)
    return datetime(year=int(year), month=int(month), day=int(day))

def get_gsmap_dat(filename:str) -> np.ndarray:
    gz = gzip.GzipFile(filename,'rb')
    data=np.frombuffer(gz.read(),dtype=np.float32).reshape((1200,3600))
    return data

def _get_gsmap_txt(filename:str, column_value:str) -> xarray.DataArray:
    df = pd.read_csv(filename)
    # The column name comes with space as prefix
    name_dict = {}
    for old_name in df.columns:
        name_dict[old_name] = old_name.strip()
    df = df.rename(columns=name_dict)
    xr = df.set_index(['Lat','Lon']).to_xarray()
    return xr[column_value]

def _get_filelist_by_source(source:str, timezone:str, target_day:datetime) -> list[str]:
    source_list = []

    for i in range(0, 24):
        d1 = target_day + timedelta(hours=int(timezone), minutes=(i * 60))
        # gsmap_mvk.20220101.0000.v7.3112.0.dat.gz
        f1 = glob(f"{source}/{d1.strftime('%Y/%m/%d')}/*{d1.strftime('%Y%m%d.%H%M')}*.dat.gz")
        assert len(f1) == 1, f"There is no file {d1.strftime('%Y%m%d.%H%M')}. Therefore, process of date '{target_day}' with timezone {timezone} is not possible."
        source_list.append(f1[0])
    logger.debug(f"{source_list=}")
    assert len(source_list) == 24, f"There should be 24 files but only {len(source_list)} is found. {source_list}"
    
    return source_list




def _aggregate(target_day:datetime, lock, destination:str, netcdf_filename:str) -> None:
    # Prepare parameter
    lon_range = BOUNDING_BOX['lon_range']
    lat_range = BOUNDING_BOX['lat_range']
    # year = str(target_day.year)
    lon_gen = np.linspace(0.05,359.95,3600)
    lat_gen = np.linspace(59.95,-59.95,1200)

    # Prepare Destination
    if(os.path.exists(destination) == False):
        lock.acquire()
        if(os.path.exists(destination) == False):
            os.makedirs(destination)
        lock.release()    

    target_filename = os.path.join(destination, netcdf_filename)
    # Get list of files to aggregate
    band_names:list[str] = list(SOURCE_PATHS.keys())
    raw_files_of_band = dict()
    for band_name in band_names:
        raw_files_of_band[band_name] = _get_filelist_by_source(source=SOURCE_PATHS[band_name], timezone=TIMEZONE, target_day=target_day)

    # 0. Bound to the target area
    bound_lon = np.logical_and(lon_gen >= lon_range[0], lon_gen <= lon_range[1])
    bound_lat = np.logical_and(lat_gen >= lat_range[0], lat_gen <= lat_range[1])    

    ### Prepare NetCDF file
    ds = nc.Dataset(target_filename, 'w', format='NETCDF4')
    lat = ds.createDimension('lat', sum(bound_lat))
    lon = ds.createDimension('lon', sum(bound_lon))
    lats = ds.createVariable('lat', 'f4', ('lat',))
    lons = ds.createVariable('lon', 'f4', ('lon',))
    values = dict()
    for band_name in band_names:
        values[band_name] = ds.createVariable(band_name, 'u2', ('lat', 'lon',))
    # values.units = 'Unknown'

    lats[:] = list(lat_gen[bound_lat])
    lons[:] = list(lon_gen[bound_lon])
    # 0. Bound to the target area
    data = dict()
    for band_name in band_names:
        raw_data = get_gsmap_dat(raw_files_of_band[band_name][0])

        bounded = raw_data[bound_lat]
        bounded = bounded[:, bound_lon]
        data[band_name] = np.zeros(bounded.shape)
    # Ignore minus of every bound
    # -4, -8 as 0
    # -99 that cell is broken


    # 2. Aggregate to 1 day
    for band_name in band_names:
        for f in raw_files_of_band[band_name]:
            # if(f != raw_files[3]): continue
            # print(f)
            raw_data = get_gsmap_dat(f)
            bounded = raw_data[bound_lat]
            bounded = bounded[:, bound_lon]
            temp = bounded.copy()
            if(sum(sum(temp < 0)) > 0): 
                logger.log(f"{target_filename}-{f} has data < 0")
            data[band_name] += temp

    # if(sum(sum(data < 0)) > 0): 
    #     logger.log(f"{target_filename} has data < 0")

    # data = np.ceil(data * 10).astype(np.uint16)
    for band_name in band_names:
        sel = data[band_name]
        sel = sel * 10
        sel[sel < 0] = 29999
        sel.astype(np.uint16)
        values[band_name][:, :] = np.expand_dims(sel, 0)
    ds.close()

def _convert_to_geotiff(target_date:datetime, full_path:str):
    filename_with_ext = os.path.split(full_path)[-1]
    filename = os.path.splitext(filename_with_ext)[0]
    rds = rioxarray.open_rasterio(full_path, decode_times=False)
    rds.rio.write_crs('epsg:4326', inplace=True)

    # 1. Interpolate from 10KM (0.1◦) to 1KM (0.01◦)
    upscale_factor = 10
    new_width = rds.rio.width * upscale_factor
    new_height = rds.rio.height * upscale_factor
    xds_upsampled = rds.rio.reproject(
        rds.rio.crs,
        shape=(new_height, new_width),
        resampling=Resampling.cubic,
    )

    # units, reference_date = rds.time.attrs['units'].split('since')
    # rds['Time'] = pd.date_range(start=reference_date, periods=rds.sizes['Time'], freq='MS')
    # rds.rio.set_nodata(29999, inplace=True)
    folder_10km = f'{GEOTIFF_PATH}/{target_date.year}/10KM'
    folder_1km = f'{GEOTIFF_PATH}/{target_date.year}/1KM'
    if(os.path.exists( folder_10km ) == False):
        os.makedirs(folder_10km)
    if(os.path.exists( folder_1km ) == False):
        os.makedirs(folder_1km)
    rds.squeeze().rio.to_raster(f'{folder_10km}/{filename}.tiff')
    xds_upsampled.squeeze().rio.to_raster(f'{folder_1km}/{filename}.tiff')
    rds.close()
    xds_upsampled.close()


def task(unprocess_date:datetime, lock):
    destination = os.path.join(AGGREGATED_PATH,str(unprocess_date.year))
    netcdf_filename = f'GSMAP_{unprocess_date.strftime("%Y%m%d")}_{TIMEZONE}.nc'
    full_path = os.path.join(destination, netcdf_filename)
    try:
        logger.info(f"Processing={unprocess_date}")
        # 2. Aggregate to 1 day
        _aggregate(unprocess_date, lock, destination, netcdf_filename)
        logger.info(f"Aggregated file={netcdf_filename}")
        # 3. Save the file as GeoTiff
        _convert_to_geotiff(unprocess_date, full_path)
    except KeyboardInterrupt:
        print(f"Interrupt: {full_path}")
        os.remove(full_path)
    except Exception as e:
        logger.error(f"{e=}\nError from '{unprocess_date}' with timezone={TIMEZONE}")
        os.remove(full_path)

def preprocess(start_date:datetime, stop_date:datetime) -> None:
    # get a list of date in the raw gsmap dataset
    # first_path = list(SOURCE_PATHS.values())[0]
    # temp:list[str] = glob(f"{first_path}/*/*/*")
    # list_of_rawdates:list[datetime] = [ _get_datetime(f) for f in temp]
    list_of_rawdates:list[datetime] =  list(date_range(start_date=start_date, stop_date=stop_date))
    # get a list of date that already preprocessd
    temp:list[str] = glob(f'{AGGREGATED_PATH}/*/*.nc')
    list_of_preprocessd:list[datetime] = [ datetime.strptime(os.path.split(f)[1][6:14],'%Y%m%d') for f in temp]

    logger.debug(f"list_of_rawdates={list_of_rawdates}")
    logger.debug(f"list_of_preprocessd={list_of_preprocessd}")
    logger.info(f"Found list_of_rawdates={len(list_of_rawdates)} and list_of_preprocessd={len(list_of_preprocessd)}")

    list_of_unprocesses:list[datetime] = list(set(list_of_rawdates).difference(list_of_preprocessd))
    if(len(list_of_unprocesses) == 0):
        # Nothing to process
        logger.info('Nothing to do')
    else:
        list_of_unprocesses.sort()
        logger.info(f"list_of_unprocesses={list_of_unprocesses}")
        manager = Manager()
        pool = mp.Pool(THREADS)
        lock = manager.Lock()
        try:
            results = [pool.apply_async( task, args=(unprocess_date, lock) ) for unprocess_date in list_of_unprocesses]
            results = [result.get() for result in results]
        finally:
            pool.close()
            pool.join()        



if __name__ == "__main__":
    # Logger
    init_logger(name='main', filename='preprocess_gsmap')
    logger = logging.getLogger('main')

    with open('./preprocess_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['preprocess']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    timezone={config['timezone']}
    bounding_box={config['bounding_box']}
    source_path={config['gsmap_dat_multiband']['source_path']}
    aggregated_path={config['gsmap_dat_multiband']['aggregated_path']}
    geotiff_path={config['gsmap_dat_multiband']['geotiff_path']}
    threads={config['threads']}
    log_level={config['log_level']}
    """)

    start_date = datetime.strptime(config['start_date'], '%d-%m-%Y')
    
    stop_date = datetime.now()
    if(config['stop_date'] != None):
        stop_date = datetime.strptime(config['stop_date'], '%d-%m-%Y')


    logger.setLevel(config['log_level'])
    THREADS:int = config['threads']
    if(THREADS == -1):
        THREADS = mp.cpu_count()
    BOUNDING_BOX = config['bounding_box']
    SOURCE_PATHS = config['gsmap_dat_multiband']['source_path']
    AGGREGATED_PATH = config['gsmap_dat_multiband']['aggregated_path']
    GEOTIFF_PATH = config['gsmap_dat_multiband']['geotiff_path']
    TIMEZONE = config['timezone']
    preprocess(start_date=start_date, stop_date=stop_date)