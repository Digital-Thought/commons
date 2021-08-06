import logging
import socket

from IPy import IP

from digital_thought_commons.restful_lookups.ianaPortLookup import IanaPortServiceNames
from digital_thought_commons.restful_lookups.ipabusedbLookup import IPAbuseDB
from digital_thought_commons.restful_lookups.ipstackLookup import IPStack
from digital_thought_commons.restful_lookups.maxmindLookup import MaxMind
from digital_thought_commons.restful_lookups.viewDnsLookup import ViewDNS
from digital_thought_commons.restful_lookups.virusTotalLookup import VirusTotal


class IPAddressDomainInfo:

    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.ipabusedb = None
        self.ipstack = None
        self.viewdns = None
        self.maxmind = None
        self.virustotal = None
        self.ianaPortService = IanaPortServiceNames()

        if 'ipabusedb' in self.api_keys:
            logging.info("Initialised IPAbuseDB")
            self.ipabusedb = IPAbuseDB(api_key=self.api_keys['ipabusedb'])
        if 'ipstack' in self.api_keys:
            logging.info("Initialised IPStack")
            self.ipstack = IPStack(api_key=self.api_keys['ipstack'])
        if 'viewdns' in self.api_keys:
            logging.info("Initialised ViewDNS")
            self.viewdns = ViewDNS(api_key=self.api_keys['viewdns'])
        if 'maxmind' in self.api_keys:
            logging.info("Initialised ViewDNS")
            self.maxmind = MaxMind(api_key=self.api_keys['maxmind'])
        if 'virustotal' in self.api_keys:
            logging.info("Initialised VirusTotal")
            self.virustotal = VirusTotal(api_key=self.api_keys['virustotal'])

    def __lookup_ip_stack_info(self, ip_address, details):
        logging.debug("Looking up IPStack info for IP Address: {}".format(ip_address))
        ip_stack_info = self.ipstack.lookup(ip_address)
        if 'error' in ip_stack_info:
            logging.error(ip_stack_info['error'])
            return {}
        location = {'continent_code': ip_stack_info['continent_code'],
                    'continent_name': ip_stack_info['continent_name'], 'country_code': ip_stack_info['country_code'],
                    'country_name': ip_stack_info['country_name'], 'region_code': ip_stack_info['region_code'],
                    'region_name': ip_stack_info['region_name'],
                    'city': ip_stack_info['city'], 'zip': ip_stack_info['zip'],
                    'coordinates': {'lat': ip_stack_info['latitude'], 'lon': ip_stack_info['longitude']}}

        security = {'is_proxy': ip_stack_info['security']['is_proxy'],
                    'proxy_type': ip_stack_info['security']['proxy_type'],
                    'is_crawler': ip_stack_info['security']['is_crawler'],
                    'crawler_name': ip_stack_info['security']['crawler_name'],
                    'crawler_type': ip_stack_info['security']['crawler_type'],
                    'is_tor': ip_stack_info['security']['is_tor'],
                    'threat_level': ip_stack_info['security']['threat_level'],
                    'threat_types': ip_stack_info['security']['threat_types']}

        details.update({'location': location, 'security': security})

        if ip_stack_info['connection']['asn'] is not None:
            details['isp_details'] = {'asn': ip_stack_info['connection']['asn'],
                                      'isp': ip_stack_info['connection']['isp']}

    def __lookup_virus_total_info(self, ip_address, details):
        logging.debug("Looking up VirusTotal info for IP Address: {}".format(ip_address))
        virustotal_info = self.virustotal.ip_lookups().retrieve_ip_information(ip_address)
        if 'data' in virustotal_info and 'attributes' in virustotal_info['data']:
            if 'last_analysis_results' in virustotal_info['data']['attributes']:
                details['malicious_analysis'] = {}
                details['malicious_analysis']['details'] = []
                for key in virustotal_info['data']['attributes']['last_analysis_results']:
                    details['malicious_analysis']['details'].append(
                        virustotal_info['data']['attributes']['last_analysis_results'][key])
                details['malicious_analysis']['summary'] = virustotal_info['data']['attributes']['last_analysis_stats']
            if 'total_votes' in virustotal_info['data']['attributes']:
                details['malicious_analysis']['votes'] = virustotal_info['data']['attributes']['total_votes']
            if 'reputation' in virustotal_info['data']['attributes']:
                details['malicious_analysis']['reputation'] = virustotal_info['data']['attributes']['reputation']

            details['whois'] = {}
            if 'regional_internet_registry' in virustotal_info['data']['attributes']:
                details['whois']['regional_internet_registry'] = virustotal_info['data']['attributes'][
                    'regional_internet_registry']
            if 'whois' in virustotal_info['data']['attributes']:
                details['whois']['detail'] = virustotal_info['data']['attributes']['whois']
            if 'whois_date' in virustotal_info['data']['attributes']:
                details['whois']['date'] = virustotal_info['data']['attributes']['whois_date']

            if 'network' in virustotal_info['data']['attributes']:
                details['network'] = virustotal_info['data']['attributes']['network']

            # asns = []
            # for net in details['isp_details']:
            #     asns.append(net['asn'])
            # if 'asn' in virustotal_info['data']['attributes'] and virustotal_info['data']['attributes'][
            #     'asn'] not in asns:
            #     details['isp_details'].append({'asn': virustotal_info['data']['attributes']['asn'],
            #                                    'isp': virustotal_info['data']['attributes']['as_owner']})

    def __lookup_ip_abuse_db_info(self, ip_address, details):
        logging.debug("Looking up IPAbuseDB info for IP Address: {}".format(ip_address))
        ipabusedb_info = self.ipabusedb.lookup(ip_address)
        if 'usage_type' in ipabusedb_info:
            details['usage_type'] = ipabusedb_info['usage_type']

        if 'malicious_analysis' not in details:
            details['malicious_analysis'] = {'abuse_total_reports': 0,
                                             'abuse_last_reported': '-',
                                             'abuse_categories': ''}

        if 'abuse_total_reports' in ipabusedb_info and ipabusedb_info['abuse_total_reports'] > 0:
            if 'malicious_analysis' not in details:
                details['malicious_analysis'] = {}
            details['malicious_analysis']['abuse_activity'] = {
                'abuse_total_reports': ipabusedb_info['abuse_total_reports'],
                'abuse_last_reported': ipabusedb_info['abuse_lastReportedAt'],
                'abuse_categories': ipabusedb_info['abuse_categories']}

    def __lookup_asn_info(self, ip_address, details):
        logging.debug("Looking up ASN info for IP Address: {}".format(ip_address))
        isp = details['isp_details']
        isp['cidr_ranges'] = []
        for asn in self.maxmind.lookup_asn(isp['asn']):
            isp['cidr_ranges'].append(asn['network'])

    def lookup_ip_address(self, ip_address, advanced=False):
        logging.debug("Enriching IP Address: {}".format(ip_address))
        port = None
        if ":" in ip_address and "." in ip_address:
            logging.debug("IPV4 with Port Found")
            port = ip_address.split(':')[1]
            ip_address = ip_address.split(':')[0]
        elif ':' in ip_address and len(ip_address.split(':')) == 9:
            port = ip_address.split(':')[8]
            ip_address = ip_address[:len(ip_address) - len(':{}'.format(port))]

        ip = None
        try:
            ip = IP(ip_address)
        except Exception as ex:
            logging.exception('Invalid IP Address {} provided'.format(ip_address))
            return {'error': 'Invalid IP Address {} provided'.format(ip_address)}

        base_details = {'ip_address': ip_address, 'netmask': str(ip.netmask()), 'version': ip.version(),
                        'type': ip.iptype(), 'reverse_dns': ip.reverseNames()}

        if port is not None:
            base_details['port_details'] = self.ianaPortService.lookup_port(port)

        if ip.iptype() == 'PUBLIC':
            try:
                for entry in socket.gethostbyaddr(ip_address):
                    entry = str(entry).replace('[', '').replace(']', '').replace("'", '')
                    if entry not in base_details['reverse_dns']:
                        base_details['reverse_dns'].append(entry)
            except Exception as ex:
                logging.error('Error encountered while performing host by address lookup: {}'.format(str(ex)))

        if self.ipstack is not None:
            self.__lookup_ip_stack_info(ip_address, base_details)

        if self.virustotal is not None and advanced:
            self.__lookup_virus_total_info(ip_address, base_details)

        if self.ipabusedb is not None:
            self.__lookup_ip_abuse_db_info(ip_address, base_details)

        if self.maxmind is not None and advanced and len(base_details['isp_details']) > 0:
            self.__lookup_asn_info(ip_address, base_details)

        return base_details
