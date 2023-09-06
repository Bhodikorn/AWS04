'''
This file only merg prepared label into one file.
This will always recreate final_file.
'''

from components.logger import init_logger
import logging
import yaml
from glob import glob
import os

import pandas as pd


def merge_label(merge_list:list[str]):
    csvs = []
    for filename in merge_list:
        csv = pd.read_csv(f"{SOURCE_PATH}/{filename}", encoding="TIS-620")
        if('tmd' in filename):
            csv['agency_name'] = 'TMD'
        csvs.append(csv)
    df = pd.concat(csvs)

    if(DROP_NA):
        df.dropna(inplace=True, subset='rain(mm)')
    
    # Select instead of drop
    df = df[SELECT_COLUMNS]

    # save
    if(os.path.exists(DESTINATION_PATH) == False):
        os.makedirs(DESTINATION_PATH)

    save_name = os.path.join(DESTINATION_PATH,f"{OUTPUT_NAME}.csv")
    if(AUTO_INCREMENT):
        count = 1
        while os.path.exists( f"{save_name}" ):
            save_name = os.path.join(DESTINATION_PATH,f"{OUTPUT_NAME} ({count}).csv")
            count += 1

    df.to_csv(f"{save_name}")
    logger.info(f"file {save_name} has been created.")
def _main():
    # Look up for all csv in source_path
    temp:list[str] = glob(f"{SOURCE_PATH}/*.csv")
    list_of_raw = list(map(lambda x: os.path.split(x)[1], temp))
    logger.debug(f"list_of_raw={list_of_raw}")
    logger.info(f"Found list_of_raw={len(list_of_raw)}")

    if(len(list_of_raw) == 0):
        logger.info('Nothing to do')
    else:
        list_of_raw.sort()
        merge_label(list_of_raw)
    


if __name__ == "__main__":
    # Logger
    init_logger(name='main', filename='merge_label')
    logger = logging.getLogger('main')
    
    with open('./merge_label_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['merge_label']

    logger.info(f"""=====CONFIG=====
    source_path={config['source_path']}
    destination_path={config['destination_path']}
    select_columns={config['select_columns']}
    output_name={config['output_name']}
    drop_na={config['drop_na']}
    auto_increment={config['auto_increment']}
    log_level={config['log_level']}
    """)

    logger.setLevel(config['log_level'])
    SOURCE_PATH:str = config['source_path']
    DESTINATION_PATH:str = config['destination_path']
    SELECT_COLUMNS:list = config['select_columns']
    OUTPUT_NAME:str = config['output_name']
    DROP_NA:bool = config['drop_na']
    AUTO_INCREMENT:bool = config['auto_increment']
    _main()