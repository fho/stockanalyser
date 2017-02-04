#!/usr/bin/env python3

from stockanalyser.stock import Stock, unpickle_stock
import stockanalyser.analysis
import importlib
import logging
from stockanalyser.stock import Stock, stock_pickle_path
from stockanalyser.analysis.levermann import (Levermann, unpickle_levermann)
import datetime
import os
from stockanalyser import config, input

logger = logging.getLogger(__name__)


def set_leverman_values(stock):
    cur_year = datetime.date.today().year
    last_year = cur_year - 1

    url = input.query_input("URL of onvista.de stock page",
                            input.QueryType.URL)
    stock.onvista_fundamental_url = url
    stock.fetch_onvista_data()

    val = input.query_input("Date of last quarterly figures release",
                            input.QueryType.DATE)
    stock.last_quarterly_figures_date = val


def load_levermann():
    l = unpickle_levermann("VOW.DE")
    print("%s" % l)


def eval_levermann_from_pickled_stock():
    stock = unpickle_stock("VOW.DE")
    l = Levermann(stock)
    l.evaluate()
    l.save()
    print(l)


def create_data_dir():
    if not os.path.exists(config.DATA_PATH):
        os.makedirs(config.DATA_PATH)
        logger.debug("Created directory %s" % config.DATA_PATH)


def main():
    logging.basicConfig(level=logging.DEBUG)

    create_data_dir()

    sym = input.query_input("Stock Symbol", input.QueryType.STOCK_SYMBOL)
    try:
        l = unpickle_levermann(sym)
    except FileNotFoundError:
        s = Stock(sym)
        l = Levermann(s)
        set_leverman_values(s)
        l.evaluate()
        l.save()
    print(l)

if __name__ == "__main__":
    main()
