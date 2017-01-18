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

    val = input.query_input("Analyst Recommendation Rating (from"
                            " https://finance.yahoo.com/quote/<SYMBOL>/analysts?p=<SYMBOL>)",
                            input.QueryType.YAHOO_ANALYST_RATING)
    stock.analyst_recommendation_rating = val

    val = input.query_input("Ebit-margin for year %s" % last_year,
                            input.QueryType.PERCENT)
    stock.set_ebit_margin(last_year, val)

    val = input.query_input("Equity Ratio for year %s" % last_year,
                            input.QueryType.PERCENT)
    stock.set_equity_ratio(last_year, val)

    val = input.query_input("RoE for year %s" % last_year,
                            input.QueryType.PERCENT)
    stock.set_roe(last_year, val)

    val = input.query_input("Date of last quarterly figures release",
                            input.QueryType.DATE)
    stock.last_quarterly_figures_date = val

    for year in [cur_year + 1, cur_year, cur_year - 1, cur_year - 2,
                 cur_year - 3]:
        val = input.query_input("EPS for year %s" % year,
                                input.QueryType.CURRENCY)
        stock.set_eps(year, val)


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
