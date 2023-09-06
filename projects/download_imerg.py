from components.logger import init_logger
from components.helper_download import date_range
import logging
from datetime import datetime
import yaml
from glob import glob
import os
import h5py
import multiprocessing as mp
import subprocess
import time

from typing import Optional, Any

"""
This script will load IMERG files from server using wget.
Uppon developing, it seems that the server only allowed 4 concurrent download sessions.

The idea idea of this script is comparing list of files between server and local. 
"""

def cmd(cmd:str) -> str:
    for i in range(RETRY_MAX):
        try:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=TIMEOUT)
            logger_wget.debug(f"stdout:{result.stdout}|stderr:{result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired as e:
            logger_wget.debug(f"{e}")
            time.sleep(RETRY_WAIT)
            continue
        except subprocess.CalledProcessError as e:
            logger_wget.debug(f"{e}")
            time.sleep(RETRY_WAIT)
            continue
        except Exception as e:
            logger_wget.debug(f"{cmd} failed with {type(e)} - {e}")
            time.sleep(RETRY_WAIT)
            continue
    # Reach RETRY_MAX
    raise TimeoutError(f"The download fails to complete after {RETRY_MAX}.")


def _get_server_list(year:int, date:str) -> list[str]:
    # temp file
    if(os.path.exists(os.path.join(TEMP)) == False):
        os.makedirs(os.path.join(TEMP))
    # temp file
    temp_file = os.path.join(TEMP, f"imerg_server_{year}_{date}.txt")
    if(os.path.exists(temp_file) == True and IGNORE_CACHE == False):
        logger_wget.info(f"temp file={temp_file} exists. Load data from temp.")
        with open(temp_file, 'r') as f:
            result = f.read().splitlines()
    else:
        search_url = f"{IMERG_URL}/{year}/{date}"
        # Get File List in the server
        command = f"wget -q -nH -nd '{search_url}' -O - | grep HDF5\\\" | cut -f4 -d\\\""
        logger_wget.info(f"command={command}")
        result = cmd(command)
        with open(temp_file, 'w') as f:
            f.writelines(result)
        result = result.rstrip('\n').split('\n')
    
    logger.debug(f"server_list={result}")
    return result

def _get_local_list(path:str) -> list[str]:
    files = [ os.path.basename(f) for f in glob(pathname=f"{path}/*.HDF5")]
    return files

def write_list_to_file(file_list:list[str], year:int, doy:str, destination_folder:str) -> str:
    # add '\n' after each item of a list
    file_list = [f"{IMERG_URL}/{year}/{doy}/{i}\n" for i in file_list]
    destination = os.path.join(destination_folder,f"imerg_missing_{year}_{doy}.txt")
    with open(f'{destination}', 'w') as fp:
        fp.writelines(file_list)
    return destination

def cmd_file(url:str, destination:str) -> str:
    url = url.rstrip()
    _,filename = os.path.split(url)
    full_path = os.path.join(destination,filename)
    for i in range(RETRY_MAX):
        try:
            command = f"wget --user <username> --password <password> {url} -P {destination}"
            logger_wget.info(f"command={command}")
            command = command.replace('<username>',IMERG_USERNAME)
            command = command.replace('<password>',IMERG_PASSWORD)
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=TIMEOUT)
            logger_wget.debug(f"stdout:{result.stdout}|stderr:{result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired as e:
            os.remove(full_path)
            logger_wget.debug(f"{e}")
            time.sleep(RETRY_WAIT)
            continue
        except subprocess.CalledProcessError as e:
            os.remove(full_path)
            logger_wget.debug(f"{e}")
            time.sleep(RETRY_WAIT)
            continue
        except Exception as e:
            os.remove(full_path)
            logger_wget.debug(f"{url} failed with {type(e)} - {e}")
            time.sleep(RETRY_WAIT)
            continue
        except KeyboardInterrupt as e:
            logger_wget.error(f"Interrupt!!! Delete file")
            os.remove(full_path)
            raise KeyboardInterrupt
    # Reach RETRY_MAX
    _,filename = os.path.split(url)
    raise TimeoutError(f"{filename} | The download fails to complete after {RETRY_MAX}.")


def _wget_imerg(file:str, destination:str='./data') -> None:
    # Check that the destication is exist
    if(os.path.exists(destination) == False):
        os.makedirs(destination)
    
    with open(file, 'r') as f:
        list_of_url:list[str] = f.readlines()
    try:
        pool = mp.Pool(LIMIT)
        results = [pool.apply_async( cmd_file, args=(url, destination) ) for url in list_of_url]
        results = [result.get() for result in results]
    except KeyboardInterrupt as e:
        pool.terminate()
    finally:
        pool.close()
        pool.join()




    # # create an async tasks
    # tasks: list[asyncio.Task[Any]] = []
    # # read each url from the file
    # with open(file, 'r') as f:
    #     for url in f.read().splitlines():
    #         tasks.append(asyncio.create_task(cmd_file(url, destination)))
    #     await asyncio.gather(*tasks)


def _load_imerg(year:int, doy:str) -> None:
    # Compare the list of files in server and local
    file_server = _get_server_list(year, doy)
    file_local = _get_local_list(path=f"{DESTINATION}/{year}/{doy}")

    file_missing = set(file_server).difference(set(file_local))

    # The first intension is to use `wget -i` option but it runs slowly.
    # To grunularly monitor the downloading process, I change the `wget` download each file seperately.
    # However, I keep the list of files to download. 
    file_with_list = write_list_to_file(file_list=list(file_missing), year=year, doy=doy, destination_folder=TEMP)
    if( len(file_missing) != 0):
        _wget_imerg(file=file_with_list, destination=f"{DESTINATION}/{year}/{doy}")

def load_imerg(start_date: datetime, stop_date: Optional[datetime]=None) -> None:
    '''
    start_date: datetime = the start of load range
    stop_date: datetime  = the end of load range. if None then load until today. Stop date is inclusive.
    '''
    if stop_date == None:
        stop_date = datetime.now()

    logger.info(f"start_date={start_date}|stop_date={stop_date}")

    for date in date_range(start_date=start_date, stop_date=stop_date):
        logger.debug(f"begin:{date}")
        year = date.year
        # date of year
        doy = date.strftime('%j')
        _load_imerg(year, doy)
        logger.info(f'{year}_{doy} downloaded')

if __name__ == "__main__":
    # Logger
    init_logger(name='imerg', filename='download_imerg')
    init_logger(name='imerg_wget', filename='download_imerg_wget')
    logger = logging.getLogger('imerg')
    logger_wget = logging.getLogger('imerg_wget')

    # Secret
    with open('./.secret.yaml', 'r') as f:
        secret = yaml.safe_load(f)['imerg']
    IMERG_USERNAME = secret['username']
    IMERG_PASSWORD = secret['password']
    del secret
    
    # Limit the `wget` concerency to only 4
    # From the developing phase, more than this creates 503 service unavailable 
    LIMIT = 4

    # Config and parameter
    with open('./download_imerg_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['imerg']

    logger.info(f"""=====CONFIG=====
    start_date={config['start_date']}
    stop_date={config['stop_date']}
    imerg_url={config['imerg_url']}
    destination={config['destination']}
    retry_max={config['retry_max']}
    retry_wait={config['retry_wait']}
    timeout={config['timeout']}
    ignore_cache={config['ignore_cache']}
    log_level={config['log_level']}
    log_wget_level={config['log_wget_level']}
    """)

    logger.setLevel(config['log_level'])
    logger_wget.setLevel(config['log_wget_level'])

    TEMP:str = os.path.join('./temp','IMERG')
    if(os.path.exists(TEMP) == False):
        os.makedirs(TEMP)
        
    DESTINATION = config['destination']
    IMERG_URL = config['imerg_url']

    RETRY_MAX:int = config['retry_max']
    RETRY_WAIT:int = config['retry_wait']
    TIMEOUT:int = config['timeout']
    IGNORE_CACHE:bool = config['ignore_cache']

    start_date = datetime.strptime(config['start_date'], '%d-%m-%Y')
    
    stop_date = datetime.now()
    if(config['stop_date'] != None):
        stop_date = datetime.strptime(config['stop_date'], '%d-%m-%Y')

    # Async call
    try:
        load_imerg(start_date=start_date, stop_date=stop_date)
    except KeyboardInterrupt:
        pass