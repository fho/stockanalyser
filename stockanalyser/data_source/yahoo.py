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


def stock_quote(symbol, date):
    assert date.weekday() not in (6, 7)
    logger.debug("Retrieving stock quote for '%s' on %s" % (symbol, date))
    str_date = date.strftime("%Y/%m/%d")
    params = (("q", "select * from yahoo.finance.historicaldata where "
                    "symbol = \"%s\" and startDate = \"%s\" "
                    "and endDate = \"%s\"" % (symbol, str_date, str_date)),
              ("format", "json"),
              ("env", "store://datatables.org/alltableswithkeys"),
              ("callback", ""))
    return float(get_yql_result(params)["Close"])


def get_stock_info(symbol):
    # https://developer.yahoo.com/yql/console/?q=show%20tables&env=store://datatables.org/alltableswithkeys#h=select+Currency%2CMarketCapitalization%2CPreviousClose%2CName%2CStockExchange++from+yahoo.finance.quotes+where+symbol+%3D+%22GOOG%22
    params = (("q", "select Currency,MarketCapitalization, PreviousClose,"
                    "Name, StockExchange from yahoo.finance.quotes"
                    " where symbol = \"%s\"" % symbol),
              ("format", "json"),
              ("env", "store://datatables.org/alltableswithkeys"),
              ("callback", ""))

    return get_yql_result(params)


def lookupSymbol(isin):
        lookup_url = "https://de.finance.yahoo.com/lookup?s=%s" % isin
        etree = common.url_to_etree(lookup_url)
        #TODO using the same query we can easily find out the stock exchange, where the stock is listed
        symbol = etree.xpath('.//a[@data-reactid][@title][@class=""]')[0].text_content()
        logger.debug("Looked up yahoo symbol: %s" % (symbol))
        return symbol

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    r = stock_quote("VOW.DE", (datetime.datetime.now() -
                               datetime.timedelta(days=1)).date())
    print(r)
