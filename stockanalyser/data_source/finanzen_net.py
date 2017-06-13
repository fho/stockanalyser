from stockanalyser.data_source import common
from datetime import datetime
import logging
import requests
import lxml

logger = logging.getLogger(__name__)


class FinanzenNetScraper(object):
    def __init__(self, url=None, isin=None):
        self.url = url
        self.termine_url = None
        self.isin = isin

    def _lookup_url(self):
        url = "http://www.finanzen.net/mmsuggest/smartsugg.asp?max_results=1&Keywords_mode=APPROX&Keywords=%(isin)s&query=%(isin)s&bias=100&target_id=0&mmFormat=json" % {'isin': self.isin}
        json_response = requests.get(url).json()
        assert len(json_response['it']) == 1
        target_url = json_response['it'][0]['il'][0]['u']
        logger.debug("Fetched target url: %s" % target_url)

        return target_url

    def _get_termine_url(self):
        element = common.url_to_etree(self.url)
        path = element.xpath('//a[@title][contains(., "Termine")]')[0].attrib['href']
        logger.debug("fetched termine path: %s" % path)

        return requests.compat.urljoin("http://www.finanzen.net/", path)

    def fetch_recent_quarterly_figures_release_date(self):
        # returns a sorted list of all "Quartalszahlen" dates
        if self.isin:
            self.url = self._lookup_url()

        if self.url is None:
            raise ValueError("Stock's finanzen.net URL is not set ")

        termine_url = self._get_termine_url()
        etree = common.url_to_etree(termine_url)
        rows = etree.xpath("//table[@class='table']//tr")
        release_dates = []
        for r in rows:
            if r.xpath("td//text()='Quartalszahlen'"):
                str_date = r.xpath("td[4]")[0].text_content()
                d = datetime.strptime(str_date, '%d.%m.%Y').date()
                release_dates.append(d)

        release_dates.sort()
        logger.debug("fetched quarterly figures release dates: %s" %
                     release_dates)
        return release_dates


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    f = FinanzenNetScraper(url="http://www.finanzen.net/aktien/Allianz-Aktie",
                           isin="DE0008404005")
    f.fetch_recent_quarterly_figures_release_date()
