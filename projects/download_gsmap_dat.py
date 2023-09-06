from components.logger import init_logger
from components.helper_download import date_range
import logging
import yaml
from datetime import datetime
import os
from typing import Optional
import ftplib
import time
from glob import glob

def _get_ftp() -> ftplib.FTP:
    ftp = ftplib.FTP(GSMAP_HOST)
    ftp.login(GSMAP_USERNAME, GSMAP_PASSWORD)
    return ftp


def _get_server_list(gsmap_file_path:str, file_prefix:str, year:str, month:str, date:str, suffix:str) -> list[str]:
    # temp file
    if(os.path.exists(os.path.join(TEMP,suffix)) == False):
        os.makedirs(os.path.join(TEMP,suffix))

    temp_file = os.path.join(TEMP,suffix, f"gsmap_server_{year}_{month}_{date}.txt")

    if(os.path.exists(temp_file) == True and IGNORE_CACHE == False):
        logger_ftp.info(f"temp file={temp_file} exists. Load data from temp.")
        with open(temp_file, 'r') as f:
            result = f.read().splitlines()
    else:
        # Load data from server
        ftp = _get_ftp()
        ftp.cwd(f'{gsmap_file_path}/{year}/{month}/{date}')
        data = ftp.mlsd(facts=['type'])
        data = list(data)
        ftp.quit()
        logger.debug(data)
        # Filter and extract only name
        result:list[str] = list(map( lambda x: x[0], filter( lambda x: (x[1]['type'] == 'file') and (file_prefix in x[0]), data )))
        with open(temp_file, 'w') as f:
            for name in result:
                f.write(name+"\n")
    
    logger.debug(f"server_list={result}")
    return result

def _get_local_list(path:str) -> list[str]:
    files = [ os.path.basename(f) for f in glob(pathname=f"{path}/*.dat.gz")]
    return files

def write_list_to_file(file_list:list[str], year:str, month:str, day:str, destination_folder:str,suffix) -> str:
    # add '\n' after each item of a list
    destination = os.path.join(destination_folder,suffix,f"gsmap_missing_{year}_{month}_{day}.txt")
    file_list.sort()
    with open(f'{destination}', 'w') as f:
        for name in file_list:
            f.write(name+"\n")
    return destination


def downlaod_file(ftp:ftplib.FTP, filename:str, destination:str):
    for i in range(RETRY_MAX):
        try:
            ftp.retrbinary("RETR " + filename ,open(f"{destination}/{filename}", 'wb').write)
            logger_ftp.debug(f"file={filename} is done downloaded.")
            return True
        except KeyboardInterrupt as e:
            print('Keyboard Interrupt!!!')
            os.remove(f"{destination}/{filename}")
            raise e
        except EOFError as e:    # To avoid EOF errors.
            logger_ftp.debug(f"EOFError: {filename} failed with {type(e)} - {e}.")
            os.remove(f"{destination}/{filename}")
            time.sleep(RETRY_WAIT)
            continue
        except Exception as e:
            logger_ftp.debug(f"{filename} failed with {type(e)} - {e}.")
            os.remove(f"{destination}/{filename}")
            time.sleep(RETRY_WAIT)
            continue
    # Reach RETRY_MAX
    raise TimeoutError(f"The download fails to complete after {RETRY_MAX}.")

def _ftp_gsmap(gsmap_file_path:str, temp_file:str, destination:str, year:str, month:str, day:str):
    # Check that the destination is exist
    destination = os.path.join(destination, year, month, day)
    if(os.path.exists(destination) == False):
        os.makedirs(destination)

    ftp = _get_ftp()
    ftp.cwd(f'{gsmap_file_path}/{year}/{month}/{day}')
    try:
        with open(temp_file, 'r') as f:
            for filename in f.read().splitlines():
                downlaod_file(ftp=ftp, filename=filename, destination=destination)
    finally:
        ftp.quit()
    

def _load_gsmap(gsmap_file_path:str, file_prefix:str, destination:str, year:str, month:str, day:str, suffix:str) -> None:
    # Compare the list of files in server and local
    file_server = _get_server_list(gsmap_file_path, file_prefix, year, month, day, suffix)
    file_local = _get_local_list(path=f"{destination}/{year}/{month}/{day}")
    file_missing = set(file_server).difference(set(file_local))
    # print("\n\n\naaaa", file_missing)
    file_with_list = write_list_to_file(file_list=list(file_missing), year=year, month=month, day=day, destination_folder=TEMP, suffix=suffix)
    if( len(file_missing) != 0):
        _ftp_gsmap(gsmap_file_path=gsmap_file_path, temp_file=file_with_list, destination=f"{destination}/", year=year, month=month, day=day)

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
        # hourly
        _load_gsmap(HOURLY['gsmap_file_path'],
            HOURLY['file_prefix'],
            HOURLY['destination'], 
            year, month, day,
            suffix='hourly')
        # hourly_g
        _load_gsmap(HOURLY_G['gsmap_file_path'],
            HOURLY_G['file_prefix'],
            HOURLY_G['destination'], 
            year, month, day,
            suffix='hourly_g')
        logger.info(f'{year}_{month}_{day} downloaded')

if __name__ == "__main__":
    # Logger
    init_logger(name='gsmap', filename='download_gsmap')
    init_logger(name='gsmap_ftp', filename='download_gsmap_ftp')
    logger = logging.getLogger('gsmap')
    logger_ftp = logging.getLogger('gsmap_ftp')

    # Secret
    with open('./.secret.yaml', 'r') as f:
        secret = yaml.safe_load(f)['gsmap']
    GSMAP_USERNAME = secret['username']
    GSMAP_PASSWORD = secret['password']
    del secret
    
    # Config and parameter
    with open('./download_gsmap_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['gsmap']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    hourly={config['hourly']}
    hourly_g={config['hourly_g']}
    retry_max={config['retry_max']}
    retry_wait={config['retry_wait']}
    timeout={config['timeout']}
    ignore_cache={config['ignore_cache']}
    log_level={config['log_level']}
    log_ftp_level={config['log_ftp_level']}
    """)

    logger.setLevel(config['log_level'])
    logger_ftp.setLevel(config['log_ftp_level'])
    
    TEMP:str = os.path.join('./temp','GSMAP')
    if(os.path.exists(TEMP) == False):
        os.makedirs(TEMP)
    
    GSMAP_HOST = config['gsmap_host']
    HOURLY:dict = config['hourly']
    HOURLY_G:dict = config['hourly_g']

    RETRY_MAX:int = config['retry_max']
    RETRY_WAIT:int = config['retry_wait']
    TIMEOUT:int = config['timeout']
    IGNORE_CACHE:bool = config['ignore_cache']

    start_date = datetime.strptime(config['start_date'], '%d-%m-%Y')
    stop_date = datetime.now()
    if(config['stop_date'] != None):
        stop_date = datetime.strptime(config['stop_date'], '%d-%m-%Y')
    
    load_gsmap(start_date=start_date, stop_date=stop_date)