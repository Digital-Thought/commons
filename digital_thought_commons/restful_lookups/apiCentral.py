import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class APICentral:

    def __init__(self, base_url, api_key):
        self.api_key = api_key
        self.base_url = base_url
        self.request_session = internet.retry_request_session(headers={'x-api-key': self.api_key})

        self.cache = APICache('api-central')

    def __lookup_ip(self, ip_address, advanced):
        try:
            logging.debug('Performing API Central Lookup for: {}'.format(ip_address))
            url = '{}/enrichment/ip-address/{}'.format(self.base_url, ip_address)
            if advanced:
                url = url + '?advanced=1'
            response = self.request_session.get(url, verify=False)
            if response.status_code != 200:
                raise Exception('Status code {} encountered while looking up IP address.  Error: {}'
                                .format(str(response.status_code), response.content))

            return response.json()
        except Exception as ex:
            logging.exception(ex)
            return {'error': str(ex)}

    def lookup(self, ip_address, advanced=False):
        return self.cache.lookup(self.__lookup_ip, ip_address=ip_address, advanced=advanced)
