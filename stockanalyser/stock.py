from stockanalyser import input
import os
import pickle
import logging
import datetime
import requests
import json
from stockanalyser.data_source import yahoo
from stockanalyser.mymoney import Money
from stockanalyser.exceptions import InvalidValueError
from stockanalyser.config import *
from stockanalyser import fileutils
from stockanalyser.data_source.onvista import OnvistaScraper
from stockanalyser.data_source.finanzen_net import FinanzenNetScraper
from enum import Enum, unique

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

    def __str__(self):
        return str(self.value)


def stock_pickle_path(symbol, dir=DATA_PATH):
    filename = fileutils.to_pickle_filename(symbol)
    path = os.path.join(dir, filename)
    return path


def unpickle_stock(symbol, dir=DATA_PATH):
        path = stock_pickle_path(symbol)
        return pickle.load(open(path, "rb"))


@unique
class Cap(Enum):
    SMALL = 1
    MID = 2
    LARGE = 3


class Stock(object):
    def __init__(self, symbol=None, onvista_fundamental_url=None, finanzen_net_url=None, isin=None):
        if symbol == None:
            symbol = yahoo.lookupSymbol(isin)

        self.symbol = symbol
        self.name = None
        self.market_cap = None
        self.cap_type = None
        self.roe = {}
        self.ebit_margin = {}
        self.equity_ratio = {}
        self.eps = {}
        self.quarterly_figure_dates = []
        self.analyst_ratings = None
        self.onvista_fundamental_url = onvista_fundamental_url
        self.finanzen_net_url = finanzen_net_url
        self.isin = isin


    def _fetch_finanzen_net_data(self):
        scrp = FinanzenNetScraper(self.finanzen_net_url, isin=self.isin)
        self.quarterly_figure_dates = [scrp.fetch_recent_quarterly_figures_release_date()]

    def _lookupFundamentalUrl(self):
        lookup_url = "http://www.onvista.de/onvista/boxes/assetSearch.json?doSubmit=Suchen&portfolioName=&searchValue=%s" % self.isin
        json_response = requests.get(lookup_url).json()
        assets = json_response['onvista']['results']['asset']
        assert len(assets) == 1
        target_url = assets[0]['snapshotlink']
        logging.debug("fundamental url found: %s" % target_url)
        return target_url

    def _fetch_onvista_data(self):
        if self.isin:
            self.onvista_fundamental_url = self._lookupFundamentalUrl()

        if not self.onvista_fundamental_url:
            raise MissingDataError("onvista_fundamental_url isn't set")

        scr = OnvistaScraper(self.onvista_fundamental_url)
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

        self.analyst_ratings = scr.analyst_ratings()

    def last_quarterly_figures_release_date(self):
        self.quarterly_figure_dates.sort()
        today = datetime.date.today()
        for d in reversed(self.quarterly_figure_dates):
            if d <= today:
                return d


    def is_quarterly_figures_release_date_outdated(self):
        self.quarterly_figure_dates.sort()
        if (self.quarterly_figure_dates[-1] <= (datetime.date.today() -
            datetime.timedelta(days=60))):
                return True
        return False



    def update_stock_info(self):

        data = yahoo.get_stock_info(self.symbol)
        self.name = data["Name"]
        self.quote = Money(float(data["PreviousClose"]), data["Currency"])
        if data["MarketCapitalization"][-1] == "B":
            self.market_cap = float(data["MarketCapitalization"][:-1]) * 10**9
        elif data["MarketCapitalization"][-1] == "M":
            self.market_cap = float(data["MarketCapitalization"][:-1]) * 10**6
        else:
            raise InvalidValueError("Unknown Suffix in MarketCap value from"
                                    " yahoo: '%s'" %
                                    data["MarketCapitalization"])

        if self.market_cap >= (5 * 10**9):
            self.cap_type = Cap.LARGE
        elif self.market_cap >= (2 * 10**9):
            self.cap_type = Cap.MID
        else:
            self.cap_type = Cap.SMALL

        self._fetch_onvista_data()
        self._fetch_finanzen_net_data()

    def set_eps(self, year, val):
        if not isinstance(val, Money):
            raise input.InvalidValueError("Expected value to be from type"
                                          " Money not %s" % type(val))
        eps = EPS(val, datetime.date.today())

        if year in self.eps:
            for e in self.eps[year]:
                # If we already have a EPS value for that year, only store it
                # the value differs or the other one is older than 6 months
                if (e.value == val and
                    (e.update_date > datetime.date.today() -
                     datetime.timedelta(days=6*30))):
                    return

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

    def price_earnings_ratio(self):
        cur_year = datetime.date.today().year

        return self.quote / self.eps[cur_year][-1].value

    def price_earnings_ratio_5year(self):
        cur_year = datetime.date.today().year
        avg_per = (self.eps[cur_year + 1][-1].value +
                   self.eps[cur_year][-1].value +
                   self.eps[cur_year-1][-1].value +
                   self.eps[cur_year-2][-1].value +
                   self.eps[cur_year-3][-1].value) / 5
        logger.debug("Calculating PER 5 Years: "
                     "%s / (%s + %s + %s %s + %s) / 5" %
                     (self.quote, self.eps[cur_year + 1][-1],
                      self.eps[cur_year][-1], self.eps[cur_year-1][-1],
                      self.eps[cur_year - 2][-1], self.eps[cur_year - 3][-1]))

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
    s.onvista_fundamental_url = "http://www.onvista.de/aktien/Volkswagen-ST-Aktie-DE0007664005"
    s.finanzen_net_url = "http://www.finanzen.net/termine/Volkswagen"
    s.update_stock_info()
    """
    s2 = Stock("MUV2.DE")
    s2.onvista_fundamental_url = "http://www.onvista.de/aktien/Muenchener-Rueck-Aktie-DE0008430026"
    s2.update_stock_info()
    """
