import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class VirusTotalDomain:

    def __init__(self, request_session, api_cache, api_url, lookup_method):
        self.request_session = request_session
        self.cache = api_cache
        self.api_url = api_url
        self.lookup_method = lookup_method

    def retrieve_domain_information(self, domain):
        query_url = 'domains/{}'.format(domain)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_domain_comments(self, ip_address):
        query_url = 'domains/{}/comments'.format(ip_address)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_domain_relationships(self, ip_address, relationship):
        query_url = 'domains/{}/{}'.format(ip_address, relationship)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_domain_relationship_objects(self, ip_address, relationship):
        query_url = 'domains/{}/relationships/{}'.format(ip_address, relationship)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_domain_votes(self, ip_address):
        query_url = 'domains/{}/votes?limit=10000'.format(ip_address)
        return self.cache.lookup(self.lookup_method, query_url=query_url)


class VirusTotalIPAddress:

    def __init__(self, request_session, api_cache, api_url, lookup_method):
        self.request_session = request_session
        self.cache = api_cache
        self.api_url = api_url
        self.lookup_method = lookup_method

    def retrieve_ip_information(self, ip_address):
        query_url = 'ip_addresses/{}'.format(ip_address)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_ip_comments(self, ip_address):
        query_url = 'ip_addresses/{}/comments'.format(ip_address)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_ip_relationships(self, ip_address, relationship):
        query_url = 'ip_addresses/{}/{}'.format(ip_address, relationship)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_ip_relationship_objects(self, ip_address, relationship):
        query_url = 'ip_addresses/{}/relationships/{}'.format(ip_address, relationship)
        return self.cache.lookup(self.lookup_method, query_url=query_url)

    def retrieve_ip_votes(self, ip_address):
        query_url = 'ip_addresses/{}/votes?limit=10000'.format(ip_address)
        return self.cache.lookup(self.lookup_method, query_url=query_url)


# class VirusTotalURL:
#
#     def __init__(self, request_session, api_cache, api_url, lookup_method):
#         self.request_session = request_session
#         self.cache = api_cache
#         self.api_url = api_url
#         self.lookup_method = lookup_method
#
#     def __encode_url(self, url):
#         return base64.b64encode(url.encode("UTF-8")).decode("UTF-8")
#
#     def retrieve_url_information(self, url):
#         query_url = 'urls/{}'.format(self.__encode_url(url))
#         return self.cache.lookup(self.lookup_method, query_url=query_url)
#
#     def retrieve_url_comments(self, url):
#         query_url = 'urls/{}/comments'.format(self.__encode_url(url))
#         return self.cache.lookup(self.lookup_method, query_url=query_url)
#
#     def retrieve_url_relationships(self, url, relationship):
#         query_url = 'urls/{}/{}'.format(self.__encode_url(url), relationship)
#         return self.cache.lookup(self.lookup_method, query_url=query_url)
#
#     def retrieve_url_relationship_objects(self, url, relationship):
#         query_url = 'urls/{}/relationships/{}'.format(self.__encode_url(url), relationship)
#         return self.cache.lookup(self.lookup_method, query_url=query_url)
#
#     def retrieve_url_votes(self, url):
#         query_url = 'urls/{}/votes'.format(self.__encode_url(url))
#         return self.cache.lookup(self.lookup_method, query_url=query_url)


class VirusTotal:
    api_url = 'https://www.virustotal.com/api/v3/{}'

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session(headers={'x-apikey': api_key})

        self.cache = APICache('virus_total')

    def __lookup(self, query_url):
        try:
            logging.debug('Performing VirusTotal Lookup for: {}'.format(query_url))
            url = self.api_url.format(query_url)
            response = self.request_session.get(url)
            if response.status_code != 200:
                raise Exception('Status code {} encountered while looking up IP address.  Error: {}'
                                .format(str(response.status_code), response.content))

            return response.json()
        except Exception as ex:
            logging.exception(ex)
            return {'error': str(ex)}

    def ip_lookups(self):
        return VirusTotalIPAddress(self.request_session, self.cache, self.api_url, self.__lookup)

    def domain_lookups(self):
        return VirusTotalDomain(self.request_session, self.cache, self.api_url, self.__lookup)

    # def url_lookups(self):
    #     return VirusTotalURL(self.request_session, self.cache, self.api_url, self.__lookup)

    def search(self, query):
        query_url = 'search?query={}'.format(query)
        return self.cache.lookup(self.__lookup, query_url=query_url)

    def virus_total_metadata(self):
        query_url = 'metadata'
        return self.cache.lookup(self.__lookup, query_url=query_url)
