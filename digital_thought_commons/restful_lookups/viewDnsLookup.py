import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class ViewDNS:
    api_url = 'https://api.viewdns.info/{}'

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session()

        self.cache = APICache('view_dns')

    def __lookup(self, query_url):
        try:
            logging.debug('Performing ViewDNS Lookup for: {}'.format(query_url))

            url = self.api_url.format(query_url) + '&apikey={}&output=json'.format(self.api_key)
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

    def reverseip(self, ip_address):
        query_url = 'reverseip/?host={}'.format(ip_address)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def whois(self, value):
        query_url = 'whois/?domain={}'.format(value)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def dnsrecord(self, domain, record_type):
        query_url = 'dnsrecord/?domain={}&recordtype={}'.format(domain, record_type)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def maclookup(self, mac_address):
        query_url = 'maclookup/?mac={}'.format(mac_address)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def reversedns(self, ip_address):
        query_url = 'reversedns/?ip={}'.format(ip_address)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def reversemx(self, mail_server):
        query_url = 'reversemx/?mx={}'.format(mail_server)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def reversens(self, name_server):
        query_url = 'reversens/?ns={}'.format(name_server)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def reversewhois(self, query):
        query_url = 'reversewhois/?q={}'.format(query)
        return self.cache.lookup(self.__lookup, query_url=query_url)
