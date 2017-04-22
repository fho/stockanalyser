import urllib.request
import lxml.etree
import logging
import lxml.html

logger = logging.getLogger(__name__)


def url_to_etree(url):
        req = urllib.request.Request(url)
        # Default User-Agent is rejected from the onvista webserver with 404
        req.add_header('User-Agent', "Bla")
        logger.debug("Fetching webpage '%s'" % url)
        resp = urllib.request.urlopen(req).read()

        return lxml.html.fromstring(resp)
