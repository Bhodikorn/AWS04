from components.logger import init_logger
from components.helper_download import date_range
import logging
import yaml
from datetime import datetime
from typing import Optional
import os
from glob import glob

import h5py
from preprocess_gsmap_dat_multiband import get_gsmap_dat

_FILE_TYPE_H5PY:int = 0
_FILE_TYPE_DAT:int = 1

def check_file_exist(file_list:list[str], files_number:int):
    if(CHECK_FILE_EXIST == False):
        return
    # logger.debug(f"checking {file_list=}")
    assert len(file_list) == files_number, f"Incomplete download. Missing file!"


def check_file_corrupt(file_list:list[str], filetype:int):
    if(CHECK_FILE_CORRUPT == False):
        return
    for filename in file_list:
        try:
            if(filetype == _FILE_TYPE_H5PY):
                h = h5py.File(filename, 'r')
            elif(filetype == _FILE_TYPE_DAT):
                get_gsmap_dat(filename=filename)
        except:
            logger.error(f"file={filename} is corrupted")

def check_imerg(date: datetime):
    year = str(date.year)
    doy = date.strftime('%j')
    folder = os.path.join(IMERG_SOURCE,year,doy)
    file_list = glob(f"{folder}/*")
    # check file exist
    try:
        check_file_exist(file_list=file_list, files_number=48)
    except:
        logger.error(f"File missing in {folder=}")
    # check corrupt
    check_file_corrupt(file_list=file_list, filetype=_FILE_TYPE_H5PY)

def check_gsmap(date: datetime):
    year = str(date.year)
    month = date.strftime('%m')
    day = date.strftime('%d')
    folder = os.path.join(GSMAP_SOURCE,year,month,day)
    file_list = glob(f"{folder}/*")
    # check file exist
    try:
        check_file_exist(file_list=file_list, files_number=24)
    except:
        logger.error(f"File missing in {folder=}")
    # check corrupt
    check_file_corrupt(file_list=file_list, filetype=_FILE_TYPE_DAT)

def check_gsmap_g(date: datetime):
    year = str(date.year)
    month = date.strftime('%m')
    day = date.strftime('%d')
    folder = os.path.join(GSMAP_G_SOURCE,year,month,day)
    file_list = glob(f"{folder}/*")
    # check file exist
    try:
        check_file_exist(file_list=file_list, files_number=24)
    except:
        logger.error(f"File missing in {folder=}")
    # check corrupt
    check_file_corrupt(file_list=file_list, filetype=_FILE_TYPE_DAT)

def _main(start_date: datetime, stop_date: Optional[datetime]=None):
    '''
    start_date: datetime = the start of load range
    stop_date: datetime  = the end of load range. if None then load until today. Stop date is inclusive.
    '''
    if stop_date == None:
        stop_date = datetime.now()
    logger.info(f"start_date={start_date}|stop_date={stop_date}")
    for date in date_range(start_date=start_date, stop_date=stop_date):
        logger.debug(f"begin:{date.strftime('%Y/%m/%d')}")
        check_imerg(date=date)
        check_gsmap(date=date)
        check_gsmap_g(date=date)

if __name__ == "__main__":
    # Logger
    init_logger(name='check', filename='check_download')
    logger = logging.getLogger('check')

    # Config and parameter
    with open('./check_download.yaml', 'r') as f:
        config = yaml.safe_load(f)['check']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    imerg_source={config['imerg_source']}
    gsmap_source={config['gsmap_source']}
    gsmap_g_source={config['gsmap_g_source']}
    check_file_exist={config['check_file_exist']}
    check_file_corrupt={config['check_file_corrupt']}
    log_level={config['log_level']}
    """)

    logger.setLevel(config['log_level'])

    IMERG_SOURCE:str = config['imerg_source']
    GSMAP_SOURCE:str = config['gsmap_source']
    GSMAP_G_SOURCE:str = config['gsmap_g_source']
    CHECK_FILE_EXIST:bool = config['check_file_exist']
    CHECK_FILE_CORRUPT:bool = config['check_file_corrupt']

    start_date:datetime = datetime.strptime(config['start_date'], '%d-%m-%Y')
    stop_date:datetime = datetime.now()
    if(config['stop_date'] != None):
        stop_date = datetime.strptime(config['stop_date'], '%d-%m-%Y')

    _main(start_date=start_date, stop_date=stop_date)