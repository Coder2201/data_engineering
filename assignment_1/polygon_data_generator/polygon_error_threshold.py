import pickle
import pandas as pd
from polygon_data_generator import portfolio

# Targeting the currency pairs for which we need to train data
train_currency_pairs = [["USD","CAD",[],portfolio("USD","CAD")],
                  ["USD","JPY",[],portfolio("USD","JPY")],
                  ["USD","MXN",[],portfolio("USD","MXN")],
                  ["EUR","USD",[],portfolio("EUR","USD")],
                  ["AUD","USD",[],portfolio("AUD","USD")],
                  ["USD","CZK",[],portfolio("USD","CZK")],
                  ["USD","PLN",[],portfolio("USD","PLN")],
                  ["USD","INR",[],portfolio("USD","INR")]]

# ************************ Code Change #7 for HWK5 ************************

# Calculating the error thresholds for each currency pair
error_thresholds = {}

# Reading the csv files for each currency pair
for pair in train_currency_pairs:
    df = pd.read_csv("csv_files/pred_return_"+pair[0]+pair[1]+".csv")

    # Calculating the mean of the MAE
    error_mean = df['error'].mean()

    # Calculating the standard deviation of the MAE
    error_deviation = df['error'].std()

    # Calculating the upper limit of the error threshold
    upper_limit = error_mean + 2*error_deviation

    # Saving the error threshold for each currency pair
    error_thresholds[pair[0] + pair[1]] = upper_limit

# Save the error thresholds in a pickle file
print(error_thresholds)
with open('models/error/error_thresholds.pkl', 'wb') as f:
    pickle.dump(error_thresholds, f)

# *******************************************************************************