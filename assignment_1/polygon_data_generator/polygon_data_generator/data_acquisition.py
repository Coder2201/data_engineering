import datetime
import os
import time
from polygon import RESTClient
from sqlalchemy import create_engine
from sqlalchemy import text
from math import sqrt
from math import isnan
from math import floor
import pickle
from pycaret.regression import *
import pandas as pd
import csv

# We can buy, sell, or do nothing each time we make a decision.
# This class defies a object for keeping track of our current investments/profits for each currency pair
class portfolio(object):
    def __init__(self, from_, to): 

        # Define the currency pair we are trading
        self.from_ = from_ # The currency we are buying
        self.to = to # The currency we are selling

        self.position = "INACTIVE" # We start with an inactive/closed position
        self.current_units = 0   # We start with no units
        self.units_list = []    # We start with an empty list of units
        self.price_list = []   # We start with an empty list of prices
        self.pnl = 0          # We start with no profit/loss

# Code Change #2 for HWK4
class currency_volatility_thresholds(object):
    def __init__(self, class_1_lower, class_1_higher, class_2_lower, class_2_higher, class_3_lower, class_3_higher):
        self.class_1_lower = class_1_lower
        self.class_1_higher = class_1_higher
        self.class_2_lower = class_2_lower
        self.class_2_higher = class_2_higher
        self.class_3_lower = class_3_lower
        self.class_3_higher = class_3_higher

class data_writer():

    def __init__(self, currency_pairs, location = os.getcwd(), table_name = "final_db"):
        # The api key given by the professor
        self.count = 0
        self.key = "beBybSi8daPgsTp5yx5cHtHpYcrjp5Jq"
        # Currency pairs passed to the class
        self.currency_pairs = currency_pairs
        # Enter location to store the db file
        self.db_location = location
        # Enter name of database
        self.table_name = table_name
        self.aggregate_max = 10 # 6 minutes worth of data - Code change #1 for HWK2
        self.trailing_count = []
        
    # Function slightly modified from polygon sample code to format the date string
    def ts_to_datetime(self, ts) -> str:
        return datetime.datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M:%S')

    # This creates a table for storing the (6 min interval) keltner data vectors
    # Code change #3 for HWK2 
    def initialize_keltner_tables(self,engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(text(
                    "CREATE TABLE " + curr[0] + curr[1] + "_keltner(min_price, max_price, average_price, volatility,fd, return_price,insert_time);"))

#************************ Code Change #1 for HWK5 *******************************************************
# Creating a table for predicted return and actual return
    def initialize_prediction_return_tables(self,engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(text(
                    "CREATE TABLE " + curr[0] + curr[1] + "_pred_return(predicted_return,actual_return,error,insert_time);"))
# *******************************************************************************************************

# Code change #3 for HWK2 
# Define a function to calculate the keltner bands
    def calculate_factors(self, min_bid, max_bid,sum_bid,): 
        avg_price = sum_bid / self.aggregate_max # Calculate the average price
        volatility = (max_bid - min_bid)/avg_price  # Calculate the volatility #5
        upper_bands = [] # Create a list to store the upper bands
        lower_bands = [] # Create a list to store the lower bands
        for i in range(1, 101):
            upper_bands.append(avg_price + i * 0.025 * volatility) # Calculate the upper bands
            lower_bands.append(avg_price - i * 0.025 * volatility) # Calculate the lower bands
        
        return volatility, avg_price,upper_bands,lower_bands # Return the volatility, average price, upper bands and lower bands

    #************************** Code Change #2 for HWK5 ********************************************************************************************
    # Define a function to calculate the predicted return
    def signal_alignment_and_error(self, return_sum, predicted_sum, error_threshold):
        # Check if both are the same sign
        if(return_sum * predicted_sum > 0 ):
            if(abs(return_sum - predicted_sum) < error_threshold):
                return 1  # Return 1 to reinvest
            else:
                return 0  # Return 0 to do nothing
        # Check if both are the same sign
        else:
            return -1  # Return -1 to close trade
    # ***************************************************************************************************************************************************
    
    # Code change #2 for HWK3 
    # Define a function to define position of the stock based on the loss threshold 
    def trailing_layer(self, portfolio, return_sum, threshold, current_value,iter,signal_alignment_value):
        position_for_last_frame = portfolio.position # Get the position of the stock for the last frame
        total_units_last_frame = portfolio.current_units # Get the total units of the stock for the last frame
    
        if return_sum == None: # If the return sum is None
            return 0 # Return 0

        # Calculate the total return on the currency pairs doing long trades
        if(portfolio.position == 'LONG'):
            # Selling price is the current value of the currency pair multiplied by the number of units
            selling_price = current_value * portfolio.current_units
               
            buying_price  = 0
            for i in range(0,len(portfolio.units_list)):
                # Buying price is the sum of the price of the currency pair multiplied by the number of units
                buying_price+=portfolio.units_list[i]*portfolio.price_list[i]
            
            # Calculate the profit and loss
            portfolio.pnl=selling_price - buying_price 

            # Check if the return sum is less than the threshold
            if(return_sum<-threshold or signal_alignment_value==-1):        
                portfolio.position = 'CLOSED' # Close the position
                portfolio.current_units = 0 # Set the current units to 0
                portfolio.units_list = [] # Set the units list to empty
                portfolio.price_list = []  # Set the price list to empty
            
            elif(signal_alignment_value==1):
                step_units = 100 # Set the step units to 100
                portfolio.units_list.append(step_units)   # Append the step units to the units list
                portfolio.price_list.append(current_value) # Append the current value to the price list
                portfolio.current_units+=step_units # Increment the current units by the step units         

        # Calculate the total return on the currency pairs doing short trades
        elif(portfolio.position == 'SHORT'): 
            selling_price = 0
            for i in range(0,len(portfolio.units_list)): # Calculate the selling price
                selling_price+=portfolio.units_list[i]*portfolio.price_list[i]
    
            buying_price  = current_value * portfolio.current_units

            # Calculate the profit/loss
            portfolio.pnl=buying_price - selling_price

            if(return_sum>threshold or signal_alignment_value==-1): # Check if the return sum is greater than the threshold
                portfolio.position = 'CLOSED' # Close the position
                portfolio.current_units = 0 
                portfolio.units_list = [] # Set the units list to empty
                portfolio.price_list = []  # Set the price list to empty
            elif(signal_alignment_value==1):
                step_units = 100
                portfolio.units_list.append(step_units)
                portfolio.price_list.append(current_value)
                portfolio.current_units+=step_units
        
        # Write the position, current units, units list, price list, PnL and return sum to the csv file
        self.write_to_csv(portfolio.from_, portfolio.to, position_for_last_frame, total_units_last_frame, portfolio.pnl, return_sum,iter)
                        
    # Define a function to write the results of total units, total pnl of each currency pair to a csv file
    def write_to_csv(self,from_, to, position, total_units, total_pnl,return_sum,iter):
        # Open the csv file
        with open('csv_files/trailing_layers_'+from_+to+'.csv', 'a', newline='') as file: 
            # Create a csv writer
            writer = csv.writer(file) 
            # Check if the trailing count is 0
            if(self.trailing_count[iter] ==0): 
                # Write the headers to the csv file
                writer.writerow(["Step","Position", "Total Units", "PnL","Return sum"])
            # Increment the trailing count by 10
            self.trailing_count[iter]+=10 
            # Write the position, total units, total pnl and return sum to the csv file
            writer.writerow(["T"+str(self.trailing_count[iter]),position, total_units, total_pnl,return_sum]) 

    # Define a function to calculate the total return of the currency pair
    def get_total_return(self, engine, from_curr, to_curr, time_frame):
        # Calculate the total sum of returns for each currency pair every hour and store it in the database
        total_return = 0

        # Get the current time
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Calculate the current time in seconds
        current_time_seconds = time.mktime(datetime.datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S").timetuple())

        # Calculate the time in seconds for one hour ago
        one_hour_ago_seconds = current_time_seconds - time_frame

        # Sum the return_prices for each currency pair for the last hour
        with engine.begin() as conn:
            result = conn.execute(text("SELECT SUM(return_price) FROM " + from_curr + to_curr + "_keltner WHERE insert_time > :one_hour_ago_seconds;"), [{"one_hour_ago_seconds":one_hour_ago_seconds}])
            for row in result:
                total_return = row[0]

        return total_return

    # ******************************** Code Change #3 for HWK5 ******************************************************************************************************************************************************************** 
    # Define a function to calculate the total predicted return of the currency pair #5
    def get_total_pred_return(self, engine, from_curr, to_curr, time_frame):
        # Calculate the total sum of returns for each currency pair every hour and store it in the database
        total_pred_return = 0

        # Get the current time
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Calculate the current time in seconds
        current_time_seconds = time.mktime(datetime.datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S").timetuple())

        # Calculate the time in seconds for one hour ago
        one_hour_ago_seconds = current_time_seconds - time_frame

        # Sum the return_prices for each currency pair for the last hour
        with engine.begin() as conn:
            result = conn.execute(text("SELECT SUM(predicted_return) FROM " + from_curr + to_curr + "_pred_return WHERE insert_time > :one_hour_ago_seconds;"), [{"one_hour_ago_seconds":one_hour_ago_seconds}])
            for row in result:
                total_pred_return = row[0]

        return total_pred_return

     # Define a function to use the trailing steps on the currency pairs and decide when to close the position       
    def trailing_stops(self, count, engine, from_curr, to_curr, portfolio, current_value,iter, error_threshold):

        # Perform trailing stops for each currency pair
        hour_in_seconds = 3600

        # Check if the count is 1 hour
        if(count == 1 * hour_in_seconds ): 
            threshold = 0.0025

            # Get the total return for the last hour
            total_return = self.get_total_return(engine, from_curr, to_curr, hour_in_seconds)

            # Get the total return for the last hour
            total_pred_return = self.get_total_pred_return(engine, from_curr, to_curr, hour_in_seconds)

            # Calculate the signal alignment value
            signal_alignment_value = self.signal_alignment_and_error(total_return,total_pred_return, error_threshold)

            # Perform trailing stops
            self.trailing_layer(portfolio, total_return, threshold, current_value,iter,signal_alignment_value)  

        # Check if the count is 2 hours
        elif(count == 2 * hour_in_seconds ):
            threshold = 0.0015

            # Get the total return for the last hour
            total_return = self.get_total_return(engine, from_curr, to_curr, hour_in_seconds)

            # Get the total return for the last hour
            total_pred_return = self.get_total_pred_return(engine, from_curr, to_curr, hour_in_seconds)

            # Calculate the signal alignment value
            signal_alignment_value = self.signal_alignment_and_error(total_return,total_pred_return, error_threshold)

            # Perform trailing stops
            self.trailing_layer(portfolio, total_return, threshold, current_value,iter,signal_alignment_value)

        # Check if the count is 3 hours
        elif(count == 3 * hour_in_seconds):
            threshold = 0.001

            # Get the total return for the last hour
            total_return = self.get_total_return(engine, from_curr, to_curr, hour_in_seconds)

            # Get the total return for the last hour
            total_pred_return = self.get_total_pred_return(engine, from_curr, to_curr, hour_in_seconds)

            # Calculate the signal alignment value
            signal_alignment_value = self.signal_alignment_and_error(total_return,total_pred_return, error_threshold)

            # Perform trailing stops
            self.trailing_layer(portfolio, total_return,threshold, current_value,iter,signal_alignment_value)

        # Check if the count is 4 hours
        elif(count!=0 and count % hour_in_seconds == 0 ):
            threshold = 0.0005  

            # Get the total return for the last hour
            total_return = self.get_total_return(engine, from_curr, to_curr, hour_in_seconds)

            # Get the total return for the last hour
            total_pred_return = self.get_total_pred_return(engine, from_curr, to_curr, hour_in_seconds)

            # Calculate the signal alignment value
            signal_alignment_value = self.signal_alignment_and_error(total_return,total_pred_return, error_threshold)

            # Perform trailing stops
            self.trailing_layer(portfolio, total_return,threshold, current_value,iter,signal_alignment_value)
   

    #**********************************************************************************************************************
        
    def acquire_data_and_write(self):

        # Number of list iterations - each one should last about 1 second
        self.count = 0
        # Code change #4 for HWK2
        # Initialize values to be used in the loop
        min_prices = [999999999] * len(self.currency_pairs) # Initialize the minimum price list
        max_prices = [0] * len(self.currency_pairs) # Initialize the maximum price list
        sum_prices = [0] * len(self.currency_pairs) # Initialize the sum price list
        total_crosses = [0] * len(self.currency_pairs) # Initialize the total crosses list
        aggregate_counters = [0] * len(self.currency_pairs) # Initialize the aggregate counters list
        keltner_bands_exist_flags = [False] * len(self.currency_pairs) # Initialize the keltner bands exist flags list
        upper_bands=[[]] * len(self.currency_pairs) # Initialize the upper bands list
        lower_bands=[[]] * len(self.currency_pairs) # Initialize the lower bands list
        keltner_header_exists = [False] * len(self.currency_pairs) # Initialize the keltner header exists list
        predicted_return_header_exists = [False] * len(self.currency_pairs)
        self.trailing_count = [0] * len(self.currency_pairs) # Initialize the trailing count list
        predicted_return = 0

        # Create an engine to connect to the database; setting echo to false should stop it from logging in std.out
        print("DB file location: sqlite+pysqlite:///{}/{}.db".format(self.db_location, self.table_name))
        engine = create_engine("sqlite+pysqlite:///{}/{}.db".format(self.db_location, self.table_name), echo=False, future=True)

        # Create the needed tables in the database
        self.initialize_aggregated_tables(engine)

        # Code change #5 for HWK2
        self.initialize_keltner_tables(engine)  # Create the keltner tables in the database
        self.initialize_prediction_return_tables(engine) 

#  Code Change #1 for HWK4 
        with open('volatility_thresholds.pkl', 'rb') as f:
            volatility_thresholds = pickle.load(f)

        prediction_models = {}
        for currency in self.currency_pairs:
            prediction_models[currency[0]+currency[1]] =  load_model('tuned_model_' + currency[0]+currency[1])


        # ********************************** Code change #4 for HWK5 **********************************************************************
        # Load the error thresholds from the pickle file
        with open('error_thresholds.pkl', 'rb') as f:
            error_thresholds = pickle.load(f)
        # ***********************************************************************************************

        # Open a RESTClient for making the api calls
        client = RESTClient(self.key)

        # Loop that runs until the total duration of the program hits 24 hours.
        while self.count < 36000:  # 36000 seconds = 10 hours
            print(self.count)

            # Only call the api every 1 second, so wait here for 0.75 seconds, because the
            # code takes about .15 seconds to run
            time.sleep(0.75)

            # Code change #6 for HWK2
            # Increment the counters
            self.count += 1
            # Count the number of seconds that have passed since the start of the program
            aggregate_counters = [x + 1 for x in aggregate_counters]

            # Loop through each currency pair
            for iter in range(len(self.currency_pairs)):
                currency = self.currency_pairs[iter]
                cross = 0
                # Set the input variables to the API
                from_ = currency[0]
                to = currency[1]

                # Code change #7 for HWK2
                # Make a check to see if 6 minutes has been reached or not
                # If it has, then calculate the keltner bands
                if aggregate_counters[iter] == self.aggregate_max+1:
                    volatility, avg_price,upper_bands[iter],lower_bands[iter] = self.calculate_factors(min_prices[iter], max_prices[iter],sum_prices[iter])
                    prev_avg_price = 0
                    return_price = 0
                    # If the keltner bands exist, then calculate the crosses
                    # If the keltner bands do not exist, then set the keltner bands exist flag to true
                    # and set the min, max and sum prices to the current price
                    # and set the aggregate counter to 0
                    # and set the total crosses to 0

                    if volatility ==0:
                        volatility=1.0
                        min_prices[iter] = 999999999
                        max_prices[iter] = 0
                        sum_prices[iter] = 0
                        aggregate_counters[iter] = 1
                        total_crosses[iter] = 0
                        keltner_bands_exist_flags[iter] = False
                        predicted_return = 0

                        # **********************************************************************************************************************
                        predicted_return_sum = 0 #-  Code Change #5 for HWK5
                        actual_return_sum = 0 #-  Code Change #5 for HWK5
                        # **********************************************************************************************************************  
                        return_price = 0 # Defining a variable to be used -   Code Change #3 for HWK3
                        prev_avg_price = 0 # Defining a variable to be used - Code Change #3 for HWK3
                        continue

                    # Calculate fd as total crosses/volatility
                    fd = total_crosses[iter] / volatility

                    if(volatility>volatility_thresholds[from_ + to].class_1_lower):
                        pred_volatility = 1
                        pred_fd = 1
                    elif(volatility<volatility_thresholds[from_ + to].class_3_higher):
                        pred_volatility = 3
                        pred_fd = 3
                    else:
                        pred_volatility = 2
                        pred_fd = 2

                    # Get the avg_price from the database of the previous 6 minutes
                    with engine.begin() as conn:
                        result = conn.execute(text("SELECT average_price FROM " + from_ + to + "_keltner ORDER BY insert_time DESC LIMIT 1"))
                        for row in result:
                            prev_avg_price = row[0]

                    # Calculate the return price only if the previous average price is not 0
                    if prev_avg_price != 0:
                        return_price = (avg_price - prev_avg_price) / prev_avg_price

                    # Code Change #2 for HWK4
                    pred_df = pd.DataFrame([[min_prices[iter], max_prices[iter],pred_fd, pred_volatility, avg_price]], columns=['min_price','max_price','fd', 'volatility', 'average_price'])
                    predictions = predict_model(prediction_models[from_+to], data=pred_df)


                    # Make vector for min,max,avg,vol,fd, return
                    keltner_vector = [min_prices[iter], max_prices[iter], avg_price, volatility, fd, return_price]
                    predicted_vector = [predicted_return,return_price,abs(predicted_return-return_price)]

                    # Updating predicted return for next iteration
                    predicted_return = predictions['prediction_label'].to_numpy()[0]

                    # print the vector
                    print("The vector for " + currency[0] + currency[1] + " is:" + str(keltner_vector) + "\n")

                    # Insert the vector into the database
                    with engine.begin() as conn:
                        conn.execute(text(
                            "INSERT INTO " + from_ + to + "_keltner(min_price, max_price, average_price, volatility,fd, return_price,insert_time) VALUES (:min_price, :max_price, :average_price, :volatility, :fd, :return_price, :insert_time)"),
                                    [{"min_price": min_prices[iter], "max_price": max_prices[iter], "average_price": avg_price, "volatility": volatility, "fd": fd, "return_price": return_price, "insert_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])

                    # ************************* Code Change #6 for HWK5 ************************************************************************************
                    # Insert the predicted vector into the database
                    with engine.begin() as conn:
                        conn.execute(text(
                            "INSERT INTO " + from_ + to + "_pred_return(predicted_return,actual_return,error, insert_time) VALUES (:predicted_return, :actual_return, :abs_diff, :insert_time)"),
                                    [{"predicted_return":  float(predicted_vector[0]), "actual_return": predicted_vector[1], "abs_diff": predicted_vector[2], "insert_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
                    # ************************************************************************************************************************************

                    # Make a csv file for the vector and append it to the csv file
                    with open('csv_files/keltner_vector_'+from_+to+'.csv', 'a', newline='') as file:
                        writer = csv.writer(file)
                        if(keltner_header_exists[iter] == False):
                            writer.writerow(["min_price", "max_price", "average_price", "volatility", "fd", "return_price"])
                            keltner_header_exists[iter] = True
                        writer.writerow(keltner_vector)

                    # Code Change #3 for HWK4 
                    with open('csv_files/pred_return_'+from_+to+'.csv', 'a', newline='') as file:
                        writer = csv.writer(file)
                        if(predicted_return_header_exists[iter] == False):
                            writer.writerow(["predicted_return","actual_return","error"])
                            predicted_return_header_exists[iter] = True
                        writer.writerow(predicted_vector)

                    # Reset the counters
                    min_prices[iter] = 999999999
                    max_prices[iter] = 0
                    sum_prices[iter] = 0
                    aggregate_counters[iter] = 1
                    total_crosses[iter] = 0
                    keltner_bands_exist_flags[iter] = True

            # Step 1: Get the data from the database
               # Call the API with the required parameters
                try:
                    resp =  client.forex_currencies_real_time_currency_conversion(from_, to, amount=100, precision=2)
                    print(resp)
                except:
                    print("Exception for " + from_ + to+" ")
                    continue

                # This gets the Last Trade object defined in the API Resource
                last_trade = resp.last
                #print(last_trade)

                # Format the timestamp from the result
                dt = self.ts_to_datetime(last_trade["timestamp"])

                # Get the current time and format it
                insert_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Calculate the price by taking the average of the bid and ask prices
                avg_price = (last_trade['bid'] + last_trade['ask']) / 2

                # Code change #8 for HWK2
                # Update the min, max and sum prices

                if avg_price < min_prices[iter]:
                    min_prices[iter] = avg_price
                if avg_price > max_prices[iter]:
                    max_prices[iter] = avg_price
                sum_prices[iter] += avg_price
                if(keltner_bands_exist_flags[iter]):
                    if avg_price > upper_bands[iter][0]:
                        cross = 1
                    elif avg_price < lower_bands[iter][0]:
                        cross = 1

                total_crosses[iter] += cross

                # Code change #4 for HWK3

                # If the count is 1, then insert the data into the database
                if(self.count == 1):
                    print("---------------Initialize trade with 100 units for "+from_+to+"-----------------")
                    currency[3].current_units = 100 # Set the current units to 100
                    currency[3].units_list.append(100) # Append the units to the units list
                    currency[3].price_list.append(avg_price) # Append the price to the price list

                # Call the trailing stop function
                self.trailing_stops(self.count,engine,from_,to,currency[3],avg_price,iter,error_thresholds[from_+to])

        # Code change #9 for HWK2
        # Print the table of vectors for all currency pairs
        for currency in self.currency_pairs:
            print("For " + currency[0] + "-"+ currency[1] +":")
            with engine.begin() as conn:
                result = conn.execute(text("SELECT min_price, max_price, average_price, volatility,fd FROM " + currency[0] + currency[1] + "_keltner;"))
                print("min_price, max_price, average_price, volatility,fd")
                for rows in result:
                    print(rows.min_price, rows.max_price, rows.average_price, rows.volatility, rows.fd)
                print("\n")


