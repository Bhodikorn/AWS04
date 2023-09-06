from typing import Union
from components.logger import init_logger
import logging
import yaml
from glob import glob
import os
import multiprocessing as mp
from multiprocessing import Manager 
from itertools import product

from sklearn.base import RegressorMixin, ClassifierMixin
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, accuracy_score
import pickle
import rioxarray
import xarray
from xarray.core.dataset import Dataset
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def get_data_from_csv(csv:pd.DataFrame, feature_dict:dict, target_name:str) -> tuple:
    # drop empty
    csv.dropna(inplace=True)
    # Get Target "y"
    y = csv[target_name]
    # Append feature "X"
    X = []
    for feature in feature_dict:
        # name: season
        # is_category: True
        name = feature['name']
        is_category = feature['is_category']
        if(is_category):
            # Need one-hot-encoding
            encoded = pd.get_dummies(csv[name], prefix=name, dtype=int)
            X.append(encoded)
        else:
            # Let's skip standardized
            X.append(csv[name])
    X = pd.concat(X, axis=1)
    return X,y

def train_model(model_names:list, X:pd.DataFrame, y:pd.Series):
    for model_name in model_names:
        assert model_name in MODEL_AVAILABEL.keys(), f"{model_name=} is not defined in either {MODEL_LIST_REGRESSORS.keys()=} and {MODEL_LIST_CLASSIFIERS.keys()=}"

        # Save RECEIPTS
        if(os.path.exists(RECEIPTS_SOURCE) == False):
            os.makedirs(RECEIPTS_SOURCE)
        X.to_csv(os.path.join(RECEIPTS_SOURCE,f'{model_name}_X.csv'))
        y.to_csv(os.path.join(RECEIPTS_SOURCE,f'{model_name}_y.csv'))
        
        model = MODEL_AVAILABEL[model_name]()

        # Prepare y if classify task
        if(model_name in MODEL_LIST_CLASSIFIERS.keys()):
            y = y.astype(int)
        
        model.fit(X,y)
        pred = model.predict(X)
        message = ""
        if(model_name in MODEL_LIST_REGRESSORS):
            score = mean_squared_error(y_pred=pred, y_true=y)
            message = f"Score [mean_squared_error] is {score}"
        elif(model_name in MODEL_LIST_CLASSIFIERS):
            score = accuracy_score(y_pred=pred, y_true=y)
            message = f"Score [accuracy_score] is {score}"
        else:
            raise ValueError(f"{model_name=} is not exists in {MODEL_LIST_REGRESSORS=} and {MODEL_LIST_CLASSIFIERS=}")

        with open(os.path.join(RECEIPTS_SOURCE, f"{model_name}_score.txt"), 'w') as f:
            f.write(message)

        save_path = os.path.join(MODEL_SOURCE, model_name)
        with open(save_path, 'wb') as f:
            pickle.dump(model, f)


def build_model(csv:pd.DataFrame, model_names:list, feature_dict:dict, target_name:str):
    # Get Data
    X,y = get_data_from_csv(csv=csv, feature_dict=feature_dict, target_name=target_name)
    # print(f"{type(X)=} {type(y)=}")
    train_model(model_names=model_names, X=X, y=y)


def _main():
    # LOAD CSV
    csv = pd.read_csv(CSV_PATH, index_col=[0])
    for model_dict in MODELS:
        model_names:list = model_dict['names']
        feature_dict = model_dict['X']
        target_name = model_dict['y']
        build_model(csv=csv.copy(), model_names=model_names, feature_dict=feature_dict, target_name=target_name)

if __name__ == "__main__":
    # Logger
    init_logger(name='main', filename='train_model')
    logger = logging.getLogger('main')
    
    with open('./train_config.yaml', 'r') as f:
        config = yaml.safe_load(f)['train_model']

    logger.info(f"""=====CONFIG=====
    csv_path={config['csv_path']}
    receipts_source={config['receipts_source']}
    model_source={config['model_source']}
    models={config['models']}
    threads={config['threads']}
    log_level={config['log_level']}
    """)

    logger.setLevel(config['log_level'])
    THREADS:int = config['threads']
    if(THREADS == -1):
        THREADS = mp.cpu_count()

    CSV_PATH:str = config['csv_path']
    RECEIPTS_SOURCE:str = config['receipts_source']
    MODEL_SOURCE:str = config['model_source']

    MODELS:list = config['models']
    # MODEL_REGRESSORS = Union[LinearRegression,RandomForestRegressor]
    MODEL_LIST_REGRESSORS = {
        'LinearRegression':LinearRegression,
        'RandomForestRegressor':RandomForestRegressor,
    }
    # MODEL_CLASSIFIER = Union[LogisticRegression,RandomForestClassifier]
    MODEL_LIST_CLASSIFIERS = {
        'LogisticRegression':LogisticRegression,
        'RandomForestClassifier':RandomForestClassifier,
    }

    MODEL_AVAILABEL = MODEL_LIST_REGRESSORS.copy()
    MODEL_AVAILABEL.update(MODEL_LIST_CLASSIFIERS)
    _main()