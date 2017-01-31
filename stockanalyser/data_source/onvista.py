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


class OnvistaFundamentalScraper(object):
    def __init__(self, url):
        self.url = url
        self.etree = None

        self.fetch_website()

    def fetch_website(self):
        self.etree = common.url_to_etree(self.url)

    def _get_table_header(self, header):
        theader = []
        for r in header:
            v = r.text.lower().strip()
            if not len(v):
                continue
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
        res = self.etree.findall(table_xpath)
        theader = self._get_table_header(res)
        if theader[0] != table_header:
            raise ParsingError("Unexpected table header: '%s'" % theader[0])

        res = self.etree.findall(row_xpath)
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
    o = OnvistaFundamentalScraper("http://www.onvista.de/aktien/"
                                  "fundamental/Bayer-Aktie-DE000BAY0017")
    print("ROE: %s" % o.roe())
    print("EPS: %s" % o.eps())
    print("EBIT-MARGIN: %s" % o.ebit_margin())
    print("EQUITY RATIO: %s" % o.equity_ratio())
