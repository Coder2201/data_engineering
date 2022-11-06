
from polygon_data_generator import data_writer
from polygon_data_generator import portfolio

# Point of execution for the package
if __name__ == '__main__':
    currency_pairs = [["AUD", "USD", [], portfolio("AUD", "USD")]]
    data = data_writer(currency_pairs)
    data.acquire_data_and_write()

