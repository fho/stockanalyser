import lxml.html
import re
from decimal import Decimal
from stockanalyser.mymoney import Money
import logging
from stockanalyser.data_source import common


logger = logging.getLogger(__name__)


class ParsingError(Exception):
    pass


def is_number(txt):
    try:
        float(txt)
        return True
    except (ValueError, TypeError):
        return False


class OnvistaScraper(object):
    def __init__(self, url):
        self.overview_url = url
        self.fundamental_url = self._build_fundamental_url(url)
        self.fundamental_etree = None

        self.fetch_fundamental_webpage()
        self.fetch_overview_webpage()

    def _build_fundamental_url(self, url):
        spl = url.split("/")
        spl.insert(4, "fundamental")
        return "/".join(spl)

    def fetch_fundamental_webpage(self):
        self.fundamental_etree = common.url_to_etree(self.fundamental_url)

    def fetch_overview_webpage(self):
        self.overview_etree = common.url_to_etree(self.overview_url)

    def _get_analyst_rating(self, xpath):
        res = self.overview_etree.xpath(xpath)
        v = int(res[0].strip())
        return v

    def analyst_ratings(self):
        buy_xpath = ('.//*[@id="AggregatedAnalysesTabAction"]/div/article/'
                     'div/table/tbody/tr[1]/td[2]/text()')
        hold_xpath = ('.//*[@id="AggregatedAnalysesTabAction"]/div/article/'
                      'div/table/tbody/tr[2]/td[2]/text()')
        sell_xpath = ('.//*[@id="AggregatedAnalysesTabAction"]/div/article/'
                      'div/table/tbody/tr[3]/td[2]/text()')

        buy = self._get_analyst_rating(buy_xpath)
        hold = self._get_analyst_rating(hold_xpath)
        sell = self._get_analyst_rating(sell_xpath)

        return (buy, hold, sell)

    def _get_table_header(self, header):
        # onvista uses 2 different presentation for the year:
        # "18/19e   17/18e  16/17e  15/16" and
        # "2019e    2018e   2017e   2016e"
        theader = []
        for r in header:
            v = r.text.lower().strip()
            if not len(v):
                continue

            # handle presentation of years as
            # "18/19e   17/18e  16/17e  15/16", convert them to the
            # YYYY (eg 2018) format
            if "/" in v:
                v = "20" + v.split("/")[1]

            # remove the "e" for estimated from year endings
            if re.match("\d+e", v):
                v = int(v[:-1])
            elif is_number(v):
                v = int(v)
            theader.append(v)
        return theader

    def _normalize_number(self, string):
        v = string.lower().strip()
        if v == "-":
            return None

        # replace german decimal seperator "," with "."
        v = v.replace(",", ".")
        v = v.replace("%", "")
        return v

    def _extract_from_table(self, table_xpath, table_header, row_xpath,
                            row_header, is_money=False):
        res = self.fundamental_etree.findall(table_xpath)
        theader = self._get_table_header(res)
        if theader[0] != table_header:
            raise ParsingError("Unexpected table header: '%s'" % theader[0])

        res = self.fundamental_etree.findall(row_xpath)
        rows = []
        for r in res:
            v = self._normalize_number(r.text)
            if v is not None and not len(v):
                continue
            elif is_number(v):
                if is_money:
                    v = Money(Decimal(v), "EUR")
                else:
                    v = float(v)
            rows.append(v)

        if rows[0] != row_header:
            raise ParsingError("Unexpected 1. row header: '%s' != '%s'" %
                               (rows[0], row_header))

        if len(theader) != len(rows):
            raise ParsingError("Parsing error, table header contains more"
                               " elements than rows:"
                               "'%s' vs '%s'" % (theader, rows))

        result = {}
        for i in range(len(rows)):
            if theader[i] == table_header:
                continue
            result[theader[i]] = rows[i]
        logger.debug("Extracted '%s' from onvista: %s" % (row_header, result))

        return result

    def eps(self):
        table_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                       'article/article/div/table[1]/thead/tr/')
        row_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                     'article/article/div/table[1]/tbody/tr[1]/')

        return self._extract_from_table(table_xpath, "gewinn", row_xpath,
                                        "gewinn pro aktie in eur", True)

    def ebit_margin(self):
        table_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                       'article/article/div/table[8]/thead/tr/')
        row_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                     'article/article/div/table[8]/tbody/tr[2]/')

        return self._extract_from_table(table_xpath, "rentabilität", row_xpath,
                                        "ebit-marge")

    def equity_ratio(self):
        table_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                       'article/article/div/table[6]/thead/tr/')
        row_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                     'article/article/div/table[6]/tbody/tr[2]/')

        return self._extract_from_table(table_xpath, "bilanz", row_xpath,
                                        "eigenkapitalquote")

    def roe(self):
        table_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                       'article/article/div/table[8]/thead/tr/')
        row_xpath = ('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                     'article/article/div/table[8]/tbody/tr[4]/')

        return self._extract_from_table(table_xpath, "rentabilität", row_xpath,
                                        "eigenkapitalrendite")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    o = OnvistaScraper("http://www.onvista.de/aktien/Bayer-Aktie-DE000BAY0017")
    print(o.analyst_ratings())
    print("ROE: %s" % o.roe())
    print("EPS: %s" % o.eps())
    print("EBIT-MARGIN: %s" % o.ebit_margin())
    print("EQUITY RATIO: %s" % o.equity_ratio())
