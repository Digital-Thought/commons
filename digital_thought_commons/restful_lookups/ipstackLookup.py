import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class IPStack:
    api_url = 'http://api.ipstack.com/{}?access_key={}&hostname=1&security=1'

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session(headers={'Key': self.api_key})

        self.cache = APICache('ipstack')

    def __lookup_ip(self, ip_address):
        try:
            logging.debug('Performing IPStack Lookup for: {}'.format(ip_address))
            url = self.api_url.format(ip_address, self.api_key)
            response = self.request_session.get(url)
            if response.status_code != 200:
                raise Exception('Status code {} encountered while looking up IP address.  Error: {}'
                                .format(str(response.status_code), response.content))

            return response.json()

        except Exception as ex:
            logging.exception(ex)
            return {'error': str(ex)}

    def lookup(self, ip_address):
        return self.cache.lookup(self.__lookup_ip, ip_address=ip_address)
