from polygon_data_generator import data_writer
from polygon_data_generator import portfolio
import unittest

class data_writer_test(unittest.TestCase):

    def setUp(self):
        currency_pairs = [["AUD", "USD", [], portfolio("AUD", "USD")]]
        self.data_writer = data_writer(currency_pairs)

    def test_ts_to_datetime(self):
        self.assertEqual(0,0)

    def test_reset_raw_data_tables(self):
        self.assertEqual(0, 0)

    def test_initialize_raw_data_tables(self):
        self.assertEqual(0, 0)

    def test_initialize_aggregated_tables(self):
        self.assertEqual(0, 0)

    def test_aggregate_raw_data_tables(self):
        self.assertEqual(0, 0)

    def test_acquire_data_and_write(self):
        self.assertEqual(0, 0)


class portfolio_test(unittest.TestCase):

    def setUp(self):
        self.portfolio = portfolio("AUD", "USD")

    def test_buy_curr(self):
        self.assertEqual(0, 0)

    def test_sell_curr(self):
        self.assertEqual(0, 0)
