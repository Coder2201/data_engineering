# -*- coding: utf-8 -*-
"""HWK1_Trishita.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oo622GXhSrpFgB2j6JPUehv0nXpgvruE
"""

# Import required libraries
#pip install polygon-api-client~=0.1.0
import datetime
from random import randint
import time
from polygon import RESTClient
from sqlalchemy import create_engine 
from sqlalchemy import text
import pickle
import pandas as pd
from math import sqrt
from math import isnan
import matplotlib.pyplot as plt
from numpy import mean
from numpy import std
from math import floor
import numpy as np

# The following 10 blocks of code define the classes for storing the the return data, for each
# currency pair.
    
# Installing the created package hosted on PyPI
#!pip install polygon-data-generator~=0.1.12

# Importing the created packages from the library 
from polygon_data_generator import data_writer
from polygon_data_generator import portfolio
from polygon_data_generator import currency_volatility_thresholds
from pycaret.regression import *

#A dictionary defining the set of currency pairs we will be pulling data for
currency_pairs = [["USD","CAD",[],portfolio("USD","CAD")],
                   ["USD","JPY",[],portfolio("USD","JPY")],
                   ["USD","MXN",[],portfolio("USD","MXN")],
                   ["EUR","USD",[],portfolio("EUR","USD")],
                   ["AUD","USD",[],portfolio("AUD","USD")],
                   ["USD","CZK",[],portfolio("USD","CZK")],
                   ["USD","PLN",[],portfolio("USD","PLN")],
                  ["USD","INR",[],portfolio("USD","INR")]]

# Importing function to randomly assign a currency pair for long and short positions
import random

# Randomly assign 5 currency pairs for a long trade and the rest for a short trade
long_pairs = random.sample(currency_pairs,4)
short_pairs = [x for x in currency_pairs if x not in long_pairs]

# Assign the position for each currency pair
for pair in long_pairs:
    pair[3].position = "LONG"
for pair in short_pairs:
    pair[3].position = "SHORT"
currency_pairs = long_pairs + short_pairs

# Print the currency pairs and their positions
for i in currency_pairs:
    print(i[0],i[1],i[3].position)

# Run the main data collection loop
# Making a class
data_writer = data_writer(currency_pairs)

# Calling the function
data_writer.acquire_data_and_write()
'''
# ******************* Code Changes for HWK4 ******************************************************
# Targeting the currency pairs for which we need to train data
train_currency_pairs = [["USD","CAD",[],portfolio("USD","CAD")],
                  ["USD","JPY",[],portfolio("USD","JPY")],
                  ["USD","MXN",[],portfolio("USD","MXN")],
                  ["EUR","USD",[],portfolio("EUR","USD")],
                  ["AUD","USD",[],portfolio("AUD","USD")],
                  ["USD","CZK",[],portfolio("USD","CZK")],
                  ["USD","PLN",[],portfolio("USD","PLN")],
                  ["USD","INR",[],portfolio("USD","INR")]]

# Making a class for storing the volatility thresholds for each currency pair
class currency_volatility_thresholds(object):
    def __init__(self, class_1_lower, class_1_higher, class_2_lower, class_2_higher, class_3_lower, class_3_higher):
        self.class_1_lower = class_1_lower
        self.class_1_higher = class_1_higher
        self.class_2_lower = class_2_lower
        self.class_2_higher = class_2_higher
        self.class_3_lower = class_3_lower
        self.class_3_higher = class_3_higher
   
# Statistically classify the VOL and the FD into 3 different classes for each currency pair:
# 1. High VOL and high FD (top 33 data points);
# 2. Medium VOL and high FD (following 34 data points); and
# 3. Low VOL and high FD (lower 33 data points).

# Sort the data points by VOL in each training set for each currency pair
train_set = {}
volatility_thresholds = {}
for pair in train_currency_pairs:
    df = pd.read_csv("csv_files/keltner_vector_"+pair[0]+pair[1]+".csv")
    df = df.sort_values(by=['volatility'],ascending=False)
    
    # Store the sorted data in a dictionary
    vol_values_1 = df.iloc[0:33]['volatility'].to_numpy()
    vol_values_2 = df.iloc[34:67]['volatility'].to_numpy()
    vol_values_3 = df.iloc[68:99]['volatility'].to_numpy()

    # Assign the class labels to the volatility values and fd values based on the ranking. First 33 as class 1. 
    df.iloc[0:33, df.columns.get_loc('volatility')] = "1"
    df.iloc[0:33, df.columns.get_loc('fd')] = "1"

    # The next 34 data points are classified as medium VOL and high FD
    df.iloc[34:67, df.columns.get_loc('volatility')] = "2"
    df.iloc[34:67, df.columns.get_loc('fd')] = "2"
    
    # The last 33 data points are classified as low VOL and high FD
    df.iloc[68:99, df.columns.get_loc('volatility')] = "3"
    df.iloc[68:99, df.columns.get_loc('fd')] = "3"
    
    # Save the data frame as a csv file
    df.to_csv("Train_set_"+pair[0]+pair[1]+".csv",index=False)
    volatility_thresholds[pair[0] + pair[1]] = currency_volatility_thresholds(vol_values_1.min(),vol_values_1.max(),
                                                                              vol_values_2.min(),vol_values_2.max(),
                                                                              vol_values_3.min(),vol_values_3.max())
   
    train_set[pair[0] + pair[1]] = pd.read_csv("Train_set_" + pair[0] + pair[1] + ".csv")

# Save the volatility thresholds in a pickle file
with open('volatility_thresholds.pkl', 'wb') as f:
    pickle.dump(volatility_thresholds, f)

# The regression model is the Linear Regression model.
for pair in train_currency_pairs:
    # Create a new regression model for each currency pair
    # initialize setup
    setup( train_set[pair[0]+pair[1]], target = 'return_price', numeric_features = ['fd', 'volatility', 'average_price'], html = False)
    # create a model
    model = create_model('lr')
    # compare models
    best = compare_models()
    # add tuning parameters
    tuned_model = tune_model(model)
    # save the tuned model as the best regression model
    best_tuned = save_model(tuned_model, 'tuned_model_'+pair[0]+pair[1])

# Use the Linear Regression model to predict the hourly Return vector for each currency pair in the test set collecting data in real time
for pair in train_currency_pairs:
    # load the model
    model = load_model('tuned_model_'+pair[0]+pair[1])
    # load the test set
    test_set = pd.read_csv("test_files/test_set_"+pair[0]+pair[1]+".csv")
    #prepare test data

# The test set is prepared in the same way as the training set
    test_set.loc[test_set['volatility'] > volatility_thresholds[pair[0] + pair[1]].class_1_lower, 'fd'] = "1"
    test_set.loc[(test_set['volatility'] < volatility_thresholds[pair[0] + pair[1]].class_1_lower)
                  & (test_set['volatility'] > volatility_thresholds[pair[0] + pair[1]].class_3_higher), 'fd'] = "2"
    test_set.loc[test_set['volatility'] < volatility_thresholds[pair[0] + pair[1]].class_3_higher, 'fd'] = "3"

    test_set.loc[test_set['volatility'] > volatility_thresholds[pair[0] + pair[1]].class_1_lower, 'volatility'] = 1
    test_set.loc[(test_set['volatility'] < volatility_thresholds[pair[0] + pair[1]].class_1_lower)
                  & (test_set['volatility'] > volatility_thresholds[pair[0] + pair[1]].class_3_higher), 'volatility'] = 2
    test_set.loc[ test_set['volatility'] < volatility_thresholds[pair[0] + pair[1]].class_3_higher, 'volatility'] = 3

    # Predict the hourly Return vector
    predictions = predict_model(model, data=test_set)
    # Add the predicted hourly Return vector to the test set
    test_set['Predicted Return'] = predictions['prediction_label']
    # Save the test set
    test_set.to_csv("Test_set_"+pair[0]+pair[1]+".csv",index=False)

# Make a csv file for each currency pair with the following columns: Return, Predicted Return and MAE
for pair in train_currency_pairs:
    test_set = pd.read_csv("Test_set_"+pair[0]+pair[1]+".csv")
    test_set['MAE'] = np.abs(test_set['return_price']-test_set['Predicted Return'])
    test_set.to_csv("Test_set_"+pair[0]+pair[1]+".csv",index=False)

'''
