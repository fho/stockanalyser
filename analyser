#!/usr/bin/env python3

from stockanalyser.stock import Stock, unpickle_stock
import stockanalyser.analysis
import importlib
import logging
from stockanalyser.stock import Stock, stock_pickle_path

from stockanalyser.analysis import levermann
from stockanalyser.analysis.levermann import (Levermann, unpickle_levermann,
                                              unpickle_levermann_sym)
import datetime
import os
import sys
import pickle
from stockanalyser import config, input
import argparse

logger = logging.getLogger(__name__)


def configure_argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action='store_true')
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("-s", "--show", action='store_true')
    parser.add_argument("-a", "--add", action='store_true')

    args = parser.parse_args()

    configure_logger(args.debug)

    logger.debug("Argparse arguments: %s" % args)
    if args.add:
        add_stock()
    elif args.show:
        show(args.verbose)
    else:
        parser.print_help()
        sys.exit(0)


def configure_logger(debug):
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level)


def unpickle_levermann_objs():
    levermann_objs = []
    for f in os.listdir(config.DATA_PATH):
        path = os.path.join(config.DATA_PATH, f)
        if not path:
            continue
        if "levermann" in f:
            l = unpickle_levermann(path)
            levermann_objs.append(l)

    return levermann_objs


def show(verbose):
    levermann_objs = unpickle_levermann_objs()
    for l in levermann_objs:
        if verbose:
            print(l)
        else:
            print("Levermann Score: %s" % l.evaluation_results[-1].score)
        print("-" * 80)


def add_stock():
    create_data_dir()
    sym = input.query_input("Stock Symbol", input.QueryType.STOCK_SYMBOL)
    try:
        path = levermann.levermann_pickle_path(sym)
        if os.path.isfile(path):
            print("Stock %s data file already exists.\n"
                  "Delete the file '%s' to remove it." % (sym, path))
            sys.exit(0)
    except FileNotFoundError:
        pass

    s = Stock(sym)
    l = Levermann(s)
    set_leverman_values(s)
    l.evaluate()
    l.save()
    print(l)


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
    l = unpickle_levermann_sym("VOW.DE")
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

    create_data_dir()

    sym = input.query_input("Stock Symbol", input.QueryType.STOCK_SYMBOL)
    try:
        l = unpickle_levermann_sym(sym)
        l.evaluate()
    except FileNotFoundError:
        s = Stock(sym)
        l = Levermann(s)
        set_leverman_values(s)
        l.evaluate()
        l.save()
    print(l)


if __name__ == "__main__":
    configure_argparse()
