import _sqlite3
import csv
import glob
import ipaddress
import logging
import os
import shutil
import zipfile
from datetime import datetime
from shutil import copyfile

from digital_thought_commons import date_utils, internet
from digital_thought_commons.cache import APICache


class MaxMind:
    api_url = 'https://download.maxmind.com/app/geoip_download?'
    refresh_period = 86400000  # 24 hours

    def __init__(self, api_key):
        self.api_key = api_key
        self.request_session = internet.retry_request_session()
        self.local_db_directory = "./maxmind"
        self.local_db = "./maxmind/GeoLite2-ASN-Blocks.sqlite"
        self.cache = APICache('max_mind')
        self.asn_ipv4_db = '{}/{}'.format(self.local_db_directory, 'GeoLite2-ASN-Blocks-IPv4.csv')
        self.asn_ipv6_db = '{}/{}'.format(self.local_db_directory, 'GeoLite2-ASN-Blocks-IPv6.csv')
        self.asn_db_gzip = '{}/{}'.format(self.local_db_directory, 'GeoLite2-ASN.zip')
        self.asn_db_sha256 = '{}/{}'.format(self.local_db_directory, 'GeoLite2-ASN.sha256')
        self.last_lookup = 0
        self.data = None

        if not os.path.exists(self.local_db_directory):
            os.mkdir(self.local_db_directory)

        self.__check_for_updates()

    def __load_data(self, new_data=False):
        if self.data is not None:
            self.data.close()

        if os.path.exists(self.local_db) and new_data:
            os.remove(self.local_db)
        self.data = _sqlite3.connect(self.local_db, check_same_thread=False)

        if new_data:
            create_cache_table = """ CREATE TABLE IF NOT EXISTS GeoLite2ASN (
                                                            id integer PRIMARY KEY,
                                                            network text,
                                                            autonomous_system_number text ,
                                                            autonomous_system_organization text,
                                                            version integer 
                                                        ); """
            self.data.execute(create_cache_table)

            with open(self.asn_ipv4_db, 'r') as db_file:
                for line in csv.DictReader(db_file):
                    cursor = self.data.cursor()
                    cursor.execute("INSERT INTO GeoLite2ASN(network, autonomous_system_number, autonomous_system_organization, version)"
                                   " VALUES(?,?,?,?)",
                                   (line['network'], line['autonomous_system_number'], line['autonomous_system_organization'], 4))

            with open(self.asn_ipv6_db, 'r') as db_file:
                for line in csv.DictReader(db_file):
                    cursor = self.data.cursor()
                    cursor.execute("INSERT INTO GeoLite2ASN(network, autonomous_system_number, autonomous_system_organization, version)"
                                   " VALUES(?,?,?,?)",
                                   (line['network'], line['autonomous_system_number'], line['autonomous_system_organization'], 6))

            self.data.commit()


    def __check_for_updates(self):
        if self.last_lookup == 0 or (date_utils.convert_to_epoch_mills(datetime.now()) - self.last_lookup) >= self.refresh_period:
            logging.info('Checking for maxmind updates')
            resp = self.request_session.get(self.api_url + 'edition_id=GeoLite2-ASN-CSV&license_key={}&suffix=zip.sha256'.format(self.api_key))
            sha256 = ""
            if os.path.exists(self.asn_db_sha256):
                with open(self.asn_db_sha256, 'r') as sha256_file:
                    sha256 = sha256_file.readline()

            if sha256 != resp.text:
                logging.info('Applying maxmind updates')
                with open(self.asn_db_sha256, 'w') as sha256_file:
                    sha256_file.write(resp.text)
                with open(self.asn_db_gzip, 'wb') as asn_db_gzip:
                    resp = self.request_session.get(self.api_url + 'edition_id=GeoLite2-ASN-CSV&license_key={}&suffix=zip'.format(self.api_key))
                    asn_db_gzip.write(resp.content)

                with zipfile.ZipFile(self.asn_db_gzip) as zip_obj:
                    zip_obj.extractall(self.local_db_directory + '/temp')

                for template_file in glob.glob(self.local_db_directory + '/temp/**/*.csv'):
                    if "GeoLite2-ASN-Blocks-IPv4" in template_file:
                        if os.path.exists(self.asn_ipv4_db):
                            os.remove(self.asn_ipv4_db)
                        copyfile(template_file, self.asn_ipv4_db)
                    if "GeoLite2-ASN-Blocks-IPv6" in template_file:
                        if os.path.exists(self.asn_ipv6_db):
                            os.remove(self.asn_ipv6_db)
                        copyfile(template_file, self.asn_ipv6_db)

                shutil.rmtree(self.local_db_directory + '/temp')
                os.remove(self.asn_db_gzip)
                self.__load_data(new_data=True)
                self.last_lookup = date_utils.convert_to_epoch_mills(datetime.now())

            if self.data is None:
                self.__load_data()

    def __lookup_asn(self, asn):
        logging.debug('Performing maxmind Lookup for: {}'.format(asn))
        self.__check_for_updates()
        cursor = self.data.cursor()
        cursor.execute("SELECT network, autonomous_system_number, autonomous_system_organization, version FROM GeoLite2ASN WHERE autonomous_system_number=" + str(asn))

        response = []
        for row in cursor.fetchall():
            response.append({'network': row[0], 'autonomous_system_number': row[1], 'autonomous_system_organization': row[2], 'version': row[3]})
        return response

    def lookup_asn(self, asn):
        return self.cache.lookup(self.__lookup_asn, asn=asn)

    def __lookup_org(self, org):
        logging.debug('Performing maxmind Lookup for: {}'.format(org))
        self.__check_for_updates()

        cursor = self.data.cursor()
        cursor.execute("SELECT network, autonomous_system_number, autonomous_system_organization, version FROM GeoLite2ASN WHERE autonomous_system_organization=" + "'" + org + "'")

        response = []
        for row in cursor.fetchall():
            response.append({'network': row[0], 'autonomous_system_number': row[1], 'autonomous_system_organization': row[2], 'version': row[3]})
        return response

    def lookup_org(self, org):
        return self.cache.lookup(self.__lookup_org, org=org)

    def __lookup_ip(self, ip_address):
        logging.debug('Performing maxmind Lookup for: {}'.format(ip_address))
        self.__check_for_updates()

        cursor = self.data.cursor()
        cursor.execute("SELECT network, autonomous_system_number, autonomous_system_organization, version FROM GeoLite2ASN")

        for row in cursor.fetchall():
            if ipaddress.ip_address(ip_address) in ipaddress.ip_network(row[0]):
                return {'network': row[0], 'autonomous_system_number': row[1], 'autonomous_system_organization': row[2], 'version': row[3]}

        return None

    def lookup_ip(self, ip_address):
        return self.cache.lookup(self.__lookup_ip, ip_address=ip_address)