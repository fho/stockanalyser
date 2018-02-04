import urllib.request
import urllib.parse
import logging
import json
import datetime
import time
from stockanalyser.data_source import common

logger = logging.getLogger(__name__)


class EmptyStockDataResponse(Exception):
    pass


YQL_BASE_URL = "http://query.yahooapis.com/v1/public/yql?"


def get_yql_result(params):
    params = urllib.parse.urlencode(params)
    url = YQL_BASE_URL + params

    tries = 0
    wait_sec = 2
    resp = None

    while resp is None:
        req = urllib.request.Request(url)
        try:
            logger.debug("Fetching Yahoo stock data from '%s'" % url)
            resp = urllib.request.urlopen(req).read()
            tries += 1

            logger.debug("Got Yahoo stock data response: '%s'" % resp)
            res = json.loads(resp.decode("utf-8"))
            if (int(res["query"]["count"]) == 0 or
                ("Name" in res["query"]["results"]["quote"] and
                 not res["query"]["results"]["quote"]["Name"])):
                raise EmptyStockDataResponse("Stock data from Yahoo doesn't"
                                             " contain values. Invalid Stock"
                                             " Symbol? For non US-Stocks a"
                                             " country prefix has to be added"
                                             " to the stock symbol. Received"
                                             " Response: '%s'" % res)
            return res["query"]["results"]["quote"]

        except (urllib.error.HTTPError, EmptyStockDataResponse) as e:
            resp = None
            if tries < 1:
                logger.error("Fetching yahoo YQL Stock Data failed, retrying"
                             " in %s seconds..." % wait_sec)
                time.sleep(wait_sec)
            else:
                raise e


def get_stock_info(symbol):
    # from https://stackoverflow.com/a/47148296/537958
    url = 'https://finance.yahoo.com/quote/' + symbol
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req).read()

    r=resp.decode("utf-8")
    i1=0
    i1=r.find('root.App.main', i1)
    i1=r.find('{', i1)
    i2=r.find("\n", i1)
    i2=r.rfind(';', i1, i2)
    jsonstr=r[i1:i2]

    data = json.loads(jsonstr)
    market_cap=data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['marketCap']['raw']
    prev_close=data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['previousClose']['raw']
    currency=data['context']['dispatcher']['stores']['QuoteSummaryStore']['summaryDetail']['currency']
    name=data['context']['dispatcher']['stores']['QuoteSummaryStore']['price']['shortName']


    res = {}
    res["Name"] = name
    res["PreviousClose"] = prev_close
    res["Currency"] = currency
    res["MarketCapitalization"] = int(market_cap)

    return res


def lookupSymbol(isin):
        lookup_url = "https://de.finance.yahoo.com/lookup?s=%s" % isin
        etree = common.url_to_etree(lookup_url)
        #TODO using the same query we can easily find out the stock exchange, where the stock is listed
        symbol = etree.xpath('.//a[@data-reactid][@title][@class=""]')[0].text_content()
        logger.debug("Stock symbol for ISIN %s: %s" % (isin, symbol))
        return symbol

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(get_stock_info("VOW.DE"))
