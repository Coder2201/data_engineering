import datetime
import os
import time
from polygon import RESTClient
from sqlalchemy import create_engine
from sqlalchemy import text
from math import sqrt
from math import isnan
from math import floor

# We can buy, sell, or do nothing each time we make a decision.
# This class defies a object for keeping track of our current investments/profits for each currency pair
class portfolio(object):
    def __init__(self, from_, to):
        # Initialize the 'From' currency amont to 1
        self.amount = 1
        self.curr2 = 0
        self.from_ = from_
        self.to = to
        # We want to keep track of state, to see what our next trade should be
        self.Prev_Action_was_Buy = False

    # This defines a function to buy the 'To' currency. It will always buy the max amount, in whole number
    # increments
    def buy_curr(self, price):
        if self.amount >= 1:
            num_to_buy = floor(self.amount)
            self.amount -= num_to_buy
            self.Prev_Action_was_Buy = True
            self.curr2 += num_to_buy * price
            print(
                "Bought %d worth of the target currency (%s). Our current profits and losses in the original currency (%s) are: %f." % (
                num_to_buy, self.to, self.from_, (self.amount - 1)))
        else:
            print("There was not enough of the original currency (%s) to make another buy." % self.from_)

    # This defines a function to sell the 'To' currency. It will always sell the max amount, in a whole number
    # increments
    def sell_curr(self, price):
        if self.curr2 >= 1:
            num_to_sell = floor(self.curr2)
            self.amount += num_to_sell * (1 / price)
            self.Prev_Action_was_Buy = False
            self.curr2 -= num_to_sell
            print(
                "Sold %d worth of the target currency (%s). Our current profits and losses in the original currency (%s) are: %f." % (
                num_to_sell, self.to, self.from_, (self.amount - 1)))
        else:
            print("There was not enough of the target currency (%s) to make another sell." % self.to)


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
        self.aggregate_max = 360 # 6 minutes worth of data - Code change #1 for HWK2
        

    # Function slightly modified from polygon sample code to format the date string
    def ts_to_datetime(self, ts) -> str:
        return datetime.datetime.fromtimestamp(ts / 1000.0).strftime('%Y-%m-%d %H:%M:%S')

    # Function which clears the raw data tables once we have aggregated the data in a 6 minute interval
    def reset_raw_data_tables(self, engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(text("DROP TABLE " + curr[0] + curr[1] + "_raw;"))
                conn.execute(
                    text("CREATE TABLE " + curr[0] + curr[1] + "_raw(ticktime text, fxrate  numeric, inserttime text);"))


    # This creates a table for storing the raw, unaggregated price data for each currency pair in the SQLite database
    def initialize_raw_data_tables(self, engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(
                    text("CREATE TABLE " + curr[0] + curr[1] + "_raw(ticktime text, fxrate  numeric, inserttime text);"))


    # This creates a table for storing the (6 min interval) aggregated price data for each currency pair in the SQLite database
    def initialize_aggregated_tables(self,engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(text(
                    "CREATE TABLE " + curr[0] + curr[1] + "_agg(inserttime text, avgfxrate  numeric, stdfxrate numeric);"))

    # This creates a table for storing the (6 min interval) keltner data vectors
    # Code change #2 for HWK2
    def initialize_keltner_tables(self,engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                conn.execute(text(
                    "CREATE TABLE " + curr[0] + curr[1] + "_keltner(min_price, max_price, average_price, volatility,fd);"))


    # This function is called every 6 minutes to aggregate the data, store it in the aggregate table,
    # and then delete the raw data
    def aggregate_raw_data_tables(self, engine):
        with engine.begin() as conn:
            for curr in self.currency_pairs:
                result = conn.execute(
                    text("SELECT AVG(fxrate) as avg_price, COUNT(fxrate) as tot_count FROM " + curr[0] + curr[1] + "_raw;"))
                for row in result:
                    avg_price = row.avg_price
                    tot_count = row.tot_count
                std_res = conn.execute(text(
                    "SELECT SUM((fxrate - " + str(avg_price) + ")*(fxrate - " + str(avg_price) + "))/(" + str(
                        tot_count) + "-1) as std_price FROM " + curr[0] + curr[1] + "_raw;"))
                for row in std_res:
                    std_price = sqrt(row.std_price)
                date_res = conn.execute(text("SELECT MAX(ticktime) as last_date FROM " + curr[0] + curr[1] + "_raw;"))
                for row in date_res:
                    last_date = row.last_date
                conn.execute(text("INSERT INTO " + curr[0] + curr[
                    1] + "_agg (inserttime, avgfxrate, stdfxrate) VALUES (:inserttime, :avgfxrate, :stdfxrate);"),
                             [{"inserttime": last_date, "avgfxrate": avg_price, "stdfxrate": std_price}])

                # This calculates and stores the return values
                exec("curr[2].append(" + curr[0] + curr[1] + "_return(last_date,avg_price))")
                exec("print(\"The return for "+curr[0]+curr[1]+" is:"+str(curr[2][-1].hist_return)+" \")")

                if len(curr[2]) > 5:
                    try:
                        avg_pop_value = curr[2][-6].hist_return
                    except:
                        avg_pop_value = 0
                    if isnan(avg_pop_value) == True:
                        avg_pop_value = 0
                else:
                    avg_pop_value = 0
               # Calculate the average return value and print it/store it
                curr_avg = curr[2][-1].get_avg(avg_pop_value)
                # exec("print(\"The average return for "+curr[0]+curr[1]+" is:"+str(curr_avg)+" \")")

                # Now that we have the average return, loop through the last 5 rows in the list to start compiling the
                # data needed to calculate the standard deviation
                for row in curr[2][-5:]:
                    row.add_to_running_squared_sum(curr_avg)

                # Calculate the standard dev using the avg
                curr_std = curr[2][-1].get_std()
                # exec("print(\"The standard deviation of the return for "+curr[0]+curr[1]+" is:"+str(curr_std)+" \")")

                # Calculate the average standard dev
                if len(curr[2]) > 5:
                    try:
                        pop_value = curr[2][-6].std_return
                    except:
                        pop_value = 0
                else:
                    pop_value = 0
                curr_avg_std = curr[2][-1].get_avg_std(pop_value)
                # exec("print(\"The average standard deviation of the return for "+curr[0]+curr[1]+" is:"+str(curr_avg_std)+" \")")  
                # -------------------Investment Strategy-----------------------------------------------
                try:
                    return_value = curr[2][-1].hist_return
                except:
                    return_value = 0
                if isnan(return_value) == True:
                    return_value = 0

                try:
                    return_value_1 = curr[2][-2].hist_return
                except:
                    return_value_1 = 0
                if isnan(return_value_1) == True:
                    return_value_1 = 0

                try:
                    return_value_2 = curr[2][-3].hist_return
                except:
                    return_value_2 = 0
                if isnan(return_value_2) == True:
                    return_value_2 = 0

                try:
                    upp_band = curr[2][-1].avg_return + (1.5 * curr[2][-1].std_return)
                    if return_value >= upp_band and curr[
                        3].Prev_Action_was_Buy == True and return_value != 0:  # (return_value > 0) and (return_value_1 > 0) and
                        curr[3].sell_curr(avg_price)
                except:
                    pass

                try:
                    loww_band = curr[2][-1].avg_return - (1.5 * curr[2][-1].std_return)
                    if return_value <= loww_band and curr[
                        3].Prev_Action_was_Buy == False and return_value != 0:  # and  (return_value < 0) and (return_value_1 < 0)
                        curr[3].buy_curr(avg_price)
                except:
                    pass

# Code change #3 for HWK2
# Define a function to calculate the keltner bands
    def calculate_factors(self, min_bid, max_bid,sum_bid,): 
        volatility = (max_bid - min_bid)  # Calculate the volatility
        avg_price = sum_bid / self.aggregate_max # Calculate the average price
        upper_bands = [] # Create a list to store the upper bands
        lower_bands = [] # Create a list to store the lower bands
        for i in range(1, 101):
            upper_bands.append(avg_price + i * 0.025 * volatility) # Calculate the upper bands
            lower_bands.append(avg_price - i * 0.025 * volatility) # Calculate the lower bands
        
        return volatility, avg_price,upper_bands,lower_bands # Return the volatility, average price, upper bands and lower bands
        
    
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

        # Create an engine to connect to the database; setting echo to false should stop it from logging in std.out
        print("DB file location: sqlite+pysqlite:///{}/{}.db".format(self.db_location, self.table_name))
        engine = create_engine("sqlite+pysqlite:///{}/{}.db".format(self.db_location, self.table_name), echo=False, future=True)

        # Create the needed tables in the database
        self.initialize_raw_data_tables(engine) 
        self.initialize_aggregated_tables(engine)

        # Code change #5 for HWK2
        self.initialize_keltner_tables(engine)  # Create the keltner tables in the database

        # Open a RESTClient for making the api calls
        with RESTClient(self.key) as client:
            # Loop that runs until the total duration of the program hits 24 hours.
            while self.count < 86400:  # 86400 seconds = 24 hours
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
                    if aggregate_counters[iter] == self.aggregate_max:
                        volatility, avg_price,upper_bands[iter],lower_bands[iter] = self.calculate_factors(min_prices[iter], max_prices[iter],sum_prices[iter])
                        
                        # If the keltner bands exist, then calculate the crosses
                        # If the keltner bands do not exist, then set the keltner bands exist flag to true
                        # and set the min, max and sum prices to the current price
                        # and set the aggregate counter to 0
                        # and set the total crosses to 0
                    
                        if volatility ==0:
                            min_prices[iter] = 999999999
                            max_prices[iter] = 0
                            sum_prices[iter] = 0
                            aggregate_counters[iter] = 0
                            total_crosses[iter] = 0
                            keltner_bands_exist_flags[iter] = False
                            continue
                        
                        # Calculate fd as total crosses/volatility
                        fd = total_crosses[iter] / volatility

                        # make vector for min,max,avg,vol,fd
                        keltner_vector = [min_prices[iter], max_prices[iter], avg_price, volatility, fd]

                        # print the vector
                        print("The vector for " + currency[0] + currency[1] + " is:" + str(keltner_vector) + "\n")

                        # Insert the vector into the database
                        with engine.begin() as conn:
                            conn.execute(text(
                                "INSERT INTO " + from_ + to + "_keltner(min_price, max_price, average_price, volatility,fd) VALUES (:min_price, :max_price, :average_price, :volatility, :fd)"),
                                        [{"min_price": min_prices[iter], "max_price": max_prices[iter], "average_price": avg_price, "volatility": volatility, "fd": fd}])

                        # Reset the counters
                        min_prices[iter] = 999999999
                        max_prices[iter] = 0
                        sum_prices[iter] = 0
                        aggregate_counters[iter] = 0
                        total_crosses[iter] = 0
                        keltner_bands_exist_flags[iter] = True

                    # Call the API with the required parameters
                    try:
                        resp =  client.forex_currencies_real_time_currency_conversion(from_, to, amount=100, precision=2)
                        # print(resp)
                    except:
                        print("Exception for " + from_ + to)
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

                    # Write the data to the SQLite database, raw data tables
                    with engine.begin() as conn:
                        conn.execute(text(
                            "INSERT INTO " + from_ + to + "_raw(ticktime, fxrate, inserttime) VALUES (:ticktime, :fxrate, :inserttime)"),
                                     [{"ticktime": dt, "fxrate": avg_price, "inserttime": insert_time}])

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

        

