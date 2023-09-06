from components.logger import init_logger
from components.helper_download import date_range
import logging
import yaml
from datetime import datetime
import os
from typing import Optional
import ftplib
from glob import glob

def _get_ftp() -> ftplib.FTP:
    ftp = ftplib.FTP(GSMAP_HOST)
    ftp.login(GSMAP_USERNAME, GSMAP_PASSWORD)
    return ftp


def _get_server_list(year:str, month:str, date:str) -> list[str]:
    # temp file
    temp_file = f"./temp/gsmap_txt_server_{year}_{month}_{date}.txt"


    if(os.path.exists(temp_file) == True):
        logger_ftp.info(f"temp file={temp_file} exists. Load data from temp.")
        with open(temp_file, 'r') as f:
            result = f.read().splitlines()
    else:
        # Load data from server
        ftp = _get_ftp()
        ftp.cwd(f'{GSMAP_FILE_PATH}/{year}/{month}/{date}')
        data = ftp.mlsd(facts=['type'])
        data = list(data)
        ftp.quit()
        # Filter and extract only name
        result:list[str] = list(map( lambda x: x[0], filter( lambda x: (x[1]['type'] == 'file') and ("txt.gz" in x[0]), data )))
        with open(temp_file, 'w') as f:
            for name in result:
                f.write(name+"\n")
    
    logger.debug(f"server_list={result}")
    return result

def _get_local_list(path:str) -> list[str]:
    files = [ os.path.basename(f) for f in glob(pathname=f"{path}/*.txt.gz")]
    return files

def write_list_to_file(file_list:list[str], year:str, month:str, day:str, destination_folder:str) -> str:
    # add '\n' after each item of a list
    destination = os.path.join(destination_folder,f"gsmap_txt_missing_{year}_{month}_{day}.txt")
    file_list.sort()
    with open(f'{destination}', 'w') as f:
        for name in file_list:
            f.write(name+"\n")
    return destination


def _ftp_gsmap(temp_file:str, destination:str, year:str, month:str, day:str):
    # Check that the destication is exist
    destination = os.path.join(destination, year, month, day)
    if(os.path.exists(destination) == False):
        os.makedirs(destination)

    ftp = _get_ftp()
    ftp.cwd(f'{GSMAP_FILE_PATH}/{year}/{month}/{day}')
    try:
        with open(temp_file, 'r') as f:
            for filename in f.read().splitlines():
                ftp.retrbinary("RETR " + filename ,open(f"{destination}/{filename}", 'wb').write)
                logger_ftp.debug(f"file={filename} is done downloaded.")
    except EOFError:    # To avoid EOF errors.
        pass
    finally:
        ftp.quit()

    

def _load_gsmap(year:str, month:str, day:str) -> None:
    # Compare the list of files in server and local
    file_server = _get_server_list(year, month, day)
    file_local = _get_local_list(path=f"{DESTINATION}/{year}/{month}/{day}")
    file_missing = set(file_server).difference(set(file_local))
    # print("\n\n\naaaa", file_missing)
    file_with_list = write_list_to_file(file_list=list(file_missing), year=year, month=month, day=day, destination_folder=f"./temp")
    if( len(file_missing) != 0):
        _ftp_gsmap(temp_file=file_with_list, destination=f"{DESTINATION}/", year=year, month=month, day=day)

def load_gsmap(start_date: datetime, stop_date: Optional[datetime]=None) -> None:
    '''
    start_date: datetime = the start of load range
    stop_date: datetime  = the end of load range. if None then load until today. Stop date is inclusive.
    '''
    if stop_date == None:
        stop_date = datetime.now()
    
    logger.info(f"start_date={start_date}|stop_date={stop_date}")
    for date in date_range(start_date=start_date, stop_date=stop_date):
        logger.debug(f"begin:{date}")

        year = str(date.year)
        month = date.strftime('%m')
        day = date.strftime('%d')

        _load_gsmap(year, month, day)
        logger.info(f'{year}_{month}_{day} downloaded')

if __name__ == "__main__":
    # Logger
    init_logger(name='gsmap', filename='download_gsmap')
    init_logger(name='gsmap_ftp', filename='download_gsmap_ftp')
    logger = logging.getLogger('gsmap')
    logger_ftp = logging.getLogger('gsmap_ftp')

    # Secret
    with open('./.secret.yaml', 'r') as f:
        secret = yaml.safe_load(f)['gsmap_txt']
    GSMAP_USERNAME = secret['username']
    GSMAP_PASSWORD = secret['password']
    del secret
    
    # Limit the `wget` concerency to only 4
    # From the developing phase, more than this creates 503 service unavailable 
    # limit = asyncio.Semaphore(4)

    # Config and parameter
    with open('./config.yaml', 'r') as f:
        config = yaml.safe_load(f)['gsmap_txt']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    log_level={config['log_level']}
    log_ftp_level={config['log_ftp_level']}
    gsmap_host={config['gsmap_host']}
    gsmap_file_path={config['gsmap_file_path']}
    destination={config['destination']}
    """)

    logger.setLevel(config['log_level'])
    logger_ftp.setLevel(config['log_ftp_level'])
    start_date = datetime.strptime(config['start_date'], '%d-%m-%Y')
    
    GSMAP_HOST = config['gsmap_host']
    GSMAP_FILE_PATH = config['gsmap_file_path']
    DESTINATION = config['destination']
    stop_date = datetime.now()
    if(config['stop_date'] != None):
        stop_date = datetime.strptime(config['stop_date'], '%d-%m-%Y')

    load_gsmap(start_date=start_date, stop_date=stop_date)

    # Async call
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(load_gsmap(start_date=start_date, stop_date=stop_date))
    # loop.close()