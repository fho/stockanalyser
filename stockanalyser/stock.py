from stockanalyser import input
import os
import pickle
import logging
import datetime
from stockanalyser.data_source import yahoo
from stockanalyser.mymoney import Money
from stockanalyser.exceptions import InvalidValueError
from stockanalyser.config import *
from stockanalyser import fileutils
from stockanalyser.data_source.onvista import OnvistaFundamentalScraper

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class UnknownIndexError(Exception):
    pass


class MissingDataError(Exception):
    pass


class EPS(object):
    def __init__(self, value, date):
        self.value = value
        self.update_date = date


def stock_pickle_path(symbol, dir=DATA_PATH):
    filename = fileutils.to_pickle_filename(symbol)
    path = os.path.join(dir, filename)
    return path


def unpickle_stock(symbol, dir=DATA_PATH):
        path = stock_pickle_path(symbol)
        return pickle.load(open(path, "rb"))


class Stock(object):
    def __init__(self, symbol):
        self.symbol = symbol

        self.name = None
        self.market_cap = None
        self.roe = {}
        self.ebit_margin = {}
        self.equity_ratio = {}
        self.eps = {}
        self.last_quarterly_figures_date = None
        self._analyst_recommendation_rating = None
        self.onvista_fundamental_url = None

        self.update_stock_info()

    def fetch_onvista_data(self):
        if not self.onvista_fundamental_url:
            raise MissingDataError("onvista_fundamental_url isn't set")

        scr = OnvistaFundamentalScraper(self.onvista_fundamental_url)
        eps = scr.eps()
        for k, v in eps.items():
            if v is not None:
                self.set_eps(k, v)

        ebit_margin = scr.ebit_margin()
        for k, v in ebit_margin.items():
            if v is not None:
                self.set_ebit_margin(k, v)

        equity_ratio = scr.equity_ratio()
        for k, v in equity_ratio.items():
            if v is not None:
                self.set_equity_ratio(k, v)

        roe = scr.roe()
        for k, v in roe.items():
            if v is not None:
                self.set_roe(k, v)

    @property
    def analyst_recommendation_rating(self):
        return self._analyst_recommendation_rating

    @analyst_recommendation_rating.setter
    def analyst_recommendation_rating(self, val):
        if val < 1 or val > 5:
            raise InvalidValueError("Analyst Rating value has to be >=1,<=5."
                                    " Get the \"Recommended Rating\" Value"
                                    " from "
                                    "https://finance.yahoo.com/quote/SYMBOL>/analysts?p=<SYMBOL>")
        self._analyst_recommendation_rating = val

    def update_stock_info(self):
        data = yahoo.get_stock_info(self.symbol)
        self.name = data["Name"]
        self.quote = Money(float(data["PreviousClose"]), data["Currency"])
        if data["MarketCapitalization"][-1] == "B":
            self.market_cap = float(data["MarketCapitalization"][:-1]) * 10**9
        else:
            raise InvalidValueError("Unknown Suffix in MarketCap value from"
                                    " yahoo: '%s'" %
                                    data["MarketCapitalization"])

    def set_eps(self, year, val):
        if not isinstance(val, Money):
            raise input.InvalidValueError("Expected value to be from type"
                                          " Money not %s" % type(val))
        eps = EPS(val, datetime.date.today())

        if year in self.eps:
            self.eps[year].append(eps)
        else:
            self.eps[year] = [eps]

    def set_equity_ratio(self, year, val):
        self.equity_ratio[year] = val

    def set_ebit_margin(self, year, val):
        self.ebit_margin[year] = val

    def set_roe(self, year, val):
        input.validate_percent_value(val)
        self.roe[year] = val

    def save(self, dir=DATA_PATH):
        path = stock_pickle_path(self.symbol)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def get_price_earnings_ratio(self):
        cur_year = datetime.date.today().year

        return self.quote / self.eps[cur_year][-1].value

    def get_5years_price_earnings_ratio(self):
        cur_year = datetime.date.today().year
        avg_per = (self.eps[cur_year + 1][-1].value +
                   self.eps[cur_year][-1].value +
                   self.eps[cur_year-1][-1].value +
                   self.eps[cur_year-2][-1].value +
                   self.eps[cur_year-3][-1].value) / 5

        return self.quote / avg_per

    def __str__(self):
        s = "{:<35} {:<25}\n".format("Name:", self.name)
        s += "{:<35} {:<25}\n".format("Symbol:", self.symbol)
        s += "{:<35} {:<25}\n".format("Market Cap.:", self.market_cap)
        s += "{:<35} {:<25}\n".format("Quote:", "%g %s" %
                                      (self.quote.amount, self.quote.currency))
        return s


if __name__ == "__main__":
    from pprint import pprint
    logging.basicConfig(level=logging.DEBUG)
    s = Stock("VOW.DE")
    pprint(s.market_cap)
