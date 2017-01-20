import urllib.request
import lxml.etree
import lxml.html
import re
from decimal import Decimal
from stockanalyser.mymoney import Money
import logging


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
        req = urllib.request.Request(self.url)
        # Default User-Agent is rejected from the onvista webserver with 404
        req.add_header('User-Agent', "Bla")
        logger.debug("Fetching webpage '%s'" % self.url)
        resp = urllib.request.urlopen(req).read()

        self.etree = lxml.html.fromstring(resp)

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

    def eps(self):
        res = self.etree.findall('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                                 'article/article/div/table[1]/thead/tr/')

        theader = self._get_table_header(res)
        if theader[0] != "gewinn":
            raise ParsingError("Unexpected table header: '%s'" % theader[0])

        res = self.etree.findall('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                                 'article/article/div/table[1]/tbody/tr[1]/')
        eps_row = []
        for r in res:
            v = self._normalize_number(r.text)
            if v is not None and not len(v):
                continue
            if is_number(v):
                v = Money(Decimal(v), "EUR")
            eps_row.append(v)

        if eps_row[0] != "gewinn pro aktie in eur":
            raise ParsingError("Unexpected 1. eps row header: '%s'" %
                               eps_row[0])

        if len(theader) != len(eps_row):
            raise ParsingError("Parsing error, table header contains more"
                               " elements than rows:"
                               "'%s' vs '%s'" % (theader, eps_row))

        eps = {}
        for i in range(len(eps_row)):
            if theader[i] == "gewinn":
                continue
            eps[theader[i]] = eps_row[i]
        logger.debug("Extracted EPS data %s" % eps)

        return eps

    def ebit_margin(self):
        res = self.etree.findall('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                                 'article/article/div/table[8]/thead/tr/')
        theader = self._get_table_header(res)

        if theader[0] != "rentabilität":
            raise ParsingError("Unexpected table header: '%s'" % theader[0])

        res = self.etree.findall('.//*[@id="ONVISTA"]/div[1]/div[1]/div[1]/'
                                 'article/article/div/table[8]/tbody/tr[2]/')
        ebit_margin_row = []
        for r in res:
            v = self._normalize_number(r.text)
            if v is not None and not len(v):
                continue
            if is_number(v):
                v = float(v)
            ebit_margin_row.append(v)

        if ebit_margin_row[0] != "ebit-marge":
            raise ParsingError("Unexpected 1. ebit-margin row header: '%s'" %
                               ebit_margin_row[0])

        if len(theader) != len(ebit_margin_row):
            raise ParsingError("Parsing error, table header contains more"
                               " elements than rows:"
                               "'%s' vs '%s'" % (theader, ebit_margin_row))

        ebit_margin = {}
        for i in range(len(ebit_margin_row)):
            if theader[i] == "rentabilität":
                continue
            print(theader[i])
            ebit_margin[theader[i]] = ebit_margin_row[i]
        logger.debug("Extracted EBIT-Margin data %s" % ebit_margin)

        return ebit_margin

if __name__ == "__main__":
    o = OnvistaFundamentalScraper("http://www.onvista.de/aktien/"
                                  "fundamental/Bayer-Aktie-DE000BAY0017")
    print(o.eps())
    print(o.ebit_margin())
