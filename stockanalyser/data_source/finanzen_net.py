from stockanalyser.data_source import common
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FinanzenNetScraper(object):
    def __init__(self, url):
        self.url = url

    def fetch_recent_quarterly_figures_release_date(self):
        etree = common.url_to_etree(self.url)
        previous = etree.xpath("//table[@class='table']")[1]
        release_date = previous.xpath("tr/td")[2].text_content()
        logger.debug("Finanzen.net release date: %s" % release_date)
        return datetime.strptime(release_date, '%d.%m.%Y').date()
