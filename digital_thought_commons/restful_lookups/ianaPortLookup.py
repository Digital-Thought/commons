import _sqlite3
import csv
import logging
import os
from datetime import datetime

from digital_thought_commons import date_utils, internet
from digital_thought_commons.cache import APICache


class IanaPortServiceNames:
    api_url = 'https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv'
    refresh_period = 86400000  # 24 hours

    def __init__(self):
        self.request_session = internet.retry_request_session()
        self.local_db_directory = "./iana"
        self.local_db = "./iana/iana_service_names_port_numbers.sqlite"
        self.cache = APICache('iana_service_names_port_numbers')
        self.iana_csv = '{}/{}'.format(self.local_db_directory, 'service-names-port-numbers.csv')
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
            create_cache_table = """ CREATE TABLE IF NOT EXISTS iana (
                                                                    id integer PRIMARY KEY,
                                                                    service text,
                                                                    port text,
                                                                    protocol text,
                                                                    description text,
                                                                    assignee text,
                                                                    contact text,
                                                                    registration_date text,
                                                                    modification_date text,
                                                                    reference text,
                                                                    service_code text,
                                                                    unauthorized_user_reported text,
                                                                    notes text
                                                                ); """
            self.data.execute(create_cache_table)

            with open(self.iana_csv, 'r') as db_file:
                for line in csv.DictReader(db_file):
                    cursor = self.data.cursor()
                    cursor.execute("INSERT INTO iana(service, port, protocol, description, assignee, contact, registration_date, modification_date, reference, service_code, "
                                   "unauthorized_user_reported, notes)"
                                   " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (line['Service Name'], line['Port Number'], line['Transport Protocol'], line['Description'], line['Assignee'], line['Contact'],
                                    line['Registration Date'], line['Modification Date'], line['Reference'], line['Service Code'], line['Unauthorized Use Reported'],
                                    line['Assignment Notes']))
            self.data.commit()



    def __check_for_updates(self):
        logging.info('Checking for iana updates')
        if self.last_lookup == 0 or (date_utils.convert_to_epoch_mills(datetime.now()) - self.last_lookup) >= self.refresh_period:
            with open(self.iana_csv, 'wb') as iana_csv:
                resp = self.request_session.get(self.api_url)
                iana_csv.write(resp.content)

            logging.info('Applying iana updates')
            self.__load_data(new_data=True)
            self.last_lookup = date_utils.convert_to_epoch_mills(datetime.now())

    def __build_from_row(self, row):
        return {'service': row[0], 'port': row[1], 'protocol': row[2], 'description': row[3], 'assignee': row[4], 'contact': row[5], 'registration_date': row[6],
                'modification_date': row[7], 'reference': row[8], 'service_code': row[9], 'unauthorized_use_reported': row[10], 'notes': row[11]}

    def __lookup_port(self, port):
        logging.debug('Performing iana Lookup for: {}'.format(port))
        self.__check_for_updates()
        cursor = self.data.cursor()
        cursor.execute("SELECT service, port, protocol, description, assignee, contact, registration_date, modification_date, reference, service_code, "
                                   "unauthorized_user_reported, notes FROM iana WHERE port=" + port)

        response = []
        for row in cursor.fetchall():
            response.append(self.__build_from_row(row))
        return response

    def lookup_port(self, port):
        port = str(port)
        return self.cache.lookup(self.__lookup_port, port=port)

    def __lookup_service(self, service):
        logging.debug('Performing iana Lookup for: {}'.format(service))
        self.__check_for_updates()
        cursor = self.data.cursor()
        cursor.execute("SELECT service, port, protocol, description, assignee, contact, registration_date, modification_date, reference, service_code, "
                                   "unauthorized_user_reported, notes FROM iana WHERE service=" + "'" + service + "'")

        response = []
        for row in cursor.fetchall():
            response.append(self.__build_from_row(row))
        return response

    def lookup_service(self, service):
        return self.cache.lookup(self.__lookup_service, service=service)

    def __lookup_protocol(self, protocol):
        logging.debug('Performing iana Lookup for: {}'.format(protocol))
        self.__check_for_updates()
        cursor = self.data.cursor()
        cursor.execute("SELECT service, port, protocol, description, assignee, contact, registration_date, modification_date, reference, service_code, "
                                   "unauthorized_user_reported, notes FROM iana WHERE protocol=" + "'" + protocol + "'")

        response = []
        for row in cursor.fetchall():
            response.append(self.__build_from_row(row))
        return response

    def lookup_protocol(self, protocol):
        return self.cache.lookup(self.__lookup_protocol, protocol=protocol)

    def __lookup_unauthorised_use(self):
        logging.debug('Performing iana Lookup for: {}'.format('unauthorised_use'))
        self.__check_for_updates()
        cursor = self.data.cursor()
        cursor.execute("SELECT service, port, protocol, description, assignee, contact, registration_date, modification_date, reference, service_code, "
                                   "unauthorized_user_reported, notes FROM iana WHERE unauthorized_user_reported IS NOT ''")

        response = []
        for row in cursor.fetchall():
            response.append(self.__build_from_row(row))
        return response

    def lookup_unauthorised_use(self):
        return self.cache.lookup(self.__lookup_unauthorised_use)