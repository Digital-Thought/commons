import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class Shodan:
    api_url = 'https://api.shodan.io/{}'

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session()

        self.cache = APICache('shodan')

    def __lookup(self, query_url):
        try:
            logging.debug('Performing Shodan Lookup for: {}'.format(query_url))

            url = self.api_url.format(query_url) + 'key={}'.format(self.api_key)
            response = self.request_session.get(url)
            if response.status_code != 200:
                raise Exception('Status code {} encountered while looking up IP address.  Error: {}'
                                .format(str(response.status_code), response.content))

            try:
                return response.json()
            except Exception as ex:
                logging.exception(response.text)
                raise Exception(response.text)
        except Exception as ex:
            logging.exception(ex)
            return {'error': str(ex)}

    def lookup_ip(self, ip_address):
        query_url = 'shodan/host/{}?'.format(ip_address)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def query(self, query):
        query_url = 'shodan/host/search?query={}&'.format(query)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def api_info(self):
        query_url = 'api-info?'
        return self.cache.lookup(self.__lookup, query_url=query_url)
