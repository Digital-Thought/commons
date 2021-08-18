import base64
import json
import logging

from digital_thought_commons import internet
from digital_thought_commons.cache import APICache


class IPAbuseDB:
    categories = {'1': 'DNS Compromise', '3': 'Fraud Orders', '4': 'DDoS Attack', '5': 'FTP Brute-Force', '6': 'Ping of Death',
                  '7': 'Phishing', '8': 'Fraud VoIP', '9': 'Open Proxy', '10': 'Web Spam', '11': 'Email Spam',
                  '12': 'Blog Spam', '13': 'VPN IP', '14': 'Port Scan', '15': 'Hacking', '16': 'SQL Injection',
                  '17': 'Spoofing', '18': 'Brute-Force', '19': 'Bad Web Bot', '20': 'Exploited Host',
                  '21': 'Web App Attack', '22': 'SSH' , '23': 'IoT Targeted', '2': 'DNS Poisoning'}

    api_url = 'https://api.abuseipdb.com/api/v2/check'

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session(headers={'Key': self.api_key})

        self.cache = APICache('abuseipdb')

    def __lookup_ip(self, ip_address, max_age_in_days):
        try:
            logging.debug('Performing AbuseIP Database Lookup for: {}'.format(ip_address))
            url = '{}?ipAddress={}&maxAgeInDays={}&verbose=true'.format(self.api_url, ip_address, str(max_age_in_days))
            response = self.request_session.get(url)
            if response.status_code != 200:
                raise Exception('Status code {} encountered while looking up IP address.  Error: {}'
                                .format(str(response.status_code), response.content))

            resp = response.json()
            abuse_response = {}
            if 'errors' not in resp:
                abuse_response['ip_address'] = resp['data']['ipAddress']
                abuse_response['abuse_total_reports'] = resp['data']['totalReports']
                abuse_response['country_name'] = resp['data']['countryName']
                abuse_response['usage_type'] = resp['data']['usageType']
                abuse_response['isp'] = resp['data']['isp']
                abuse_response['original_encoded_response'] = base64.b64encode(json.dumps(resp).encode('UTF-8')) \
                    .decode('UTF-8')

                categories = []
                if resp['data']['totalReports'] > 0:
                    abuse_response['abuse_lastReportedAt'] = resp['data']['lastReportedAt']
                    for report in resp['data']['reports']:
                        for cat in report['categories']:
                            try:
                                if self.categories[str(cat)] not in categories:
                                    categories.append(self.categories[str(cat)])
                            except Exception as ex:
                                logging.exception(ex)
                                continue
                    abuse_response['abuse_categories'] = categories

            return abuse_response
        except Exception as ex:
            logging.exception(ex)
            return {'error': str(ex)}

    def lookup(self, ip_address, max_age_in_days=90):
        return self.cache.lookup(self.__lookup_ip, ip_address=ip_address, max_age_in_days=max_age_in_days)
