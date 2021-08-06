import _sqlite3
import base64
import getpass
import hashlib
import json
import logging
import os
import pathlib
import time
from _sqlite3 import Error

import yaml

from digital_thought_commons import elasticsearch

cache_resource_folder = "{}/../_resources/cache".format(str(pathlib.Path(__file__).parent.absolute()))
default_cache_configuration_file = f'{cache_resource_folder}/default_cache_config.yaml'
system_cache_configuration_file = './config/loggingConfig.yaml'


class QueueCache:

    def __init__(self, size, name):
        self.size = size
        self.name = name
        self.queue_keys = []
        self.queue = {}

    def put(self, key, obj):
        if len(self.queue_keys) >= self.size:
            last_index = self.queue_keys[0]
            try:
                self.queue.pop(last_index)
                self.queue_keys.remove(last_index)
                logging.debug("Queue Full. Removing key {} from QueueCache: {}".format(key, self.name))
            except:
                logging.debug("Error Removing Key  {} from QueueCache: {}".format(key, self.name))

        self.queue_keys.append(key)
        self.queue[key] = obj

    def lookup(self, key):
        obj = None
        if key in self.queue_keys:
            try:
                obj = self.queue[key]
                self.queue.pop(key)
                self.queue_keys.remove(key)
                logging.debug("Retrieved key {} from QueueCache: {}".format(key, self.name))
            except:
                logging.debug("Error Retrieving Key  {} from QueueCache: {}".format(key, self.name))

        return obj

    def items(self):
        return self.queue

    def keys(self):
        return self.queue_keys


class APICache:

    def __init__(self, cache_name, custom_config_file: str = None):
        if custom_config_file and os.path.exists(custom_config_file):
            self.configuration_file = custom_config_file
        elif custom_config_file and not os.path.exists(custom_config_file):
            raise FileNotFoundError(f'Specified configuration file not found: {custom_config_file}')
        elif os.path.exists(system_cache_configuration_file):
            self.configuration_file = system_cache_configuration_file
        else:
            self.configuration_file = default_cache_configuration_file

        with open(self.configuration_file, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        self.cache_name = cache_name
        self.memory_cache = QueueCache(self.config['memory_cache_size'], self.cache_name)
        if self.config['cache_type'] == 'file':
            self.__configure_file_cache()
        elif self.config['cache_type'] == 'elastic':
            self.__configure_elastic_cache()
        else:
            raise Exception("Unknown Cache Type: {}".format(self.config['cache_type']))

        self.max_age = self.config['default_max_age']

        if self.cache_name.replace(' ', '_') + '_max_age' in self.config:
            self.max_age = self.config[self.cache_name.replace(' ', '_') + '_max_age']

    def __configure_elastic_cache(self):
        self.elastic_connection = elasticsearch.ElasticsearchConnection(api_key=self.config['elastic']['api_key'],
                                                                        server=self.config['elastic']['server'],
                                                                        port=self.config['elastic']['port'])

    def __configure_file_cache(self):
        self.cache_location = r'.\cache'
        if 'cache_location' in self.config['file']:
            self.cache_location = self.config['file']['cache_location']

        if not os.path.exists(self.cache_location):
            os.mkdir(self.cache_location)

        self.cache_file = self.cache_location + '/' + self.cache_name.replace(' ', '_') + '.cache'

        try:
            self.connection = _sqlite3.connect(self.cache_file, check_same_thread=False)
            self.__create_table()
            logging.info('Initialised cache for {} located at {}'.format(self.cache_name, self.cache_file))
        except Error as er:
            logging.exception('Error occurred while initialising cache file {}'.format(self.cache_file), er)
            raise er

    def __create_table(self):
        create_cache_table = """ CREATE TABLE IF NOT EXISTS cache (
                                                id integer PRIMARY KEY,
                                                signature_hash text,
                                                lookup_timestamp integer,
                                                encoded_response text,
                                                username text,
                                                cache_name text
                                            ); """
        self.connection.execute(create_cache_table)

    def __generate_hash(self, args):
        signature_string = self.cache_name
        for key, value in args.items():
            signature_string += '{}={}'.format(key, value)

        return hashlib.sha256(bytes(signature_string, 'utf-8')).hexdigest()

    def __lookup_file_cache(self, signature_hash, current_timestamp):
        encoded_value = None
        try:
            logging.debug('Looking up signature {} in cache that is not older than {}'.
                          format(signature_hash, str(current_timestamp - self.max_age)))
            cursor = self.connection.cursor()
            cursor.execute("SELECT lookup_timestamp, encoded_response FROM cache WHERE signature_hash=? "
                           "AND lookup_timestamp>=?", (signature_hash, current_timestamp - self.max_age))

            recent_timestamp = 0
            for row in cursor.fetchall():
                if row[0] > recent_timestamp:
                    encoded_value = base64.b64decode(row[1]).decode("UTF-8")
                    recent_timestamp = row[0]

        except Exception as ex:
            logging.exception("Error encountered while looking up cache signature: {}".format(signature_hash), ex)

        return encoded_value

    def __lookup_elastic_cache(self, signature_hash, current_timestamp):
        encoded_value = None
        try:
            logging.debug('Looking up signature {} in cache that is not older than {}'.
                          format(signature_hash, str(current_timestamp - self.max_age)))
            query = {"size": 100, "query": {"bool": {"must": [{"term": {"signature_hash": signature_hash}},
                                                              {"range": {"lookup_timestamp": {
                                                                  "gte": current_timestamp - self.max_age}
                                                              }}]}}}

            recent_timestamp = 0
            scroll_query = self.elastic_connection.get_scroller()
            for entry in scroll_query.query("api-cache", query):
                if entry['_source']['lookup_timestamp'] > recent_timestamp:
                    encoded_value = base64.b64decode(entry['_source']['encoded_response']).decode("UTF-8")
                    recent_timestamp = entry['_source']['lookup_timestamp']
            scroll_query.clear()
        except Exception as ex:
            logging.exception("Error encountered while looking up cache signature: {}".format(signature_hash), ex)

        return encoded_value

    def __lookup_cache(self, signature_hash, current_timestamp):
        if self.config['cache_type'] == 'file':
            return self.__lookup_file_cache(signature_hash=signature_hash, current_timestamp=current_timestamp)
        elif self.config['cache_type'] == 'elastic':
            return self.__lookup_elastic_cache(signature_hash=signature_hash, current_timestamp=current_timestamp)

    def __store_to_file_cache(self, signature_hash, current_timestamp, encoded_response, username):
        try:
            logging.debug('Storing signature {} in cache'.
                          format(signature_hash))

            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO cache(signature_hash, lookup_timestamp, encoded_response, cache_name, username)"
                           " VALUES(?,?,?,?,?)",
                           (signature_hash, current_timestamp, encoded_response, self.cache_name, username))
            self.connection.commit()
        except Exception as ex:
            logging.exception("Error encountered while storing to cache signature: {}".format(signature_hash), ex)

    def __store_to_elastic_cache(self, signature_hash, current_timestamp, encoded_response, username):
        try:
            doc = {'signature_hash': signature_hash, 'encoded_response': encoded_response,
                   'cache_name': self.cache_name, 'lookup_timestamp': current_timestamp,
                   'username': username}

            resp = self.elastic_connection.index_document(index='api-cache', document=doc)

            if resp['status_code'] != 201:
                raise Exception('Failed to store item to Elastic cache: {}'.format(str(resp)))

        except Exception as ex:
            logging.exception("Error encountered while storing to cache signature: {}".format(signature_hash), ex)

    def __store_to_cache(self, signature_hash, current_timestamp, response):
        username = getpass.getuser()
        encoded_response = base64.b64encode(response.encode("UTF-8")).decode("UTF-8")
        if self.config['cache_type'] == 'file':
            self.__store_to_file_cache(signature_hash, current_timestamp, encoded_response, username)
        elif self.config['cache_type'] == 'elastic':
            self.__store_to_elastic_cache(signature_hash, current_timestamp, encoded_response, username)

    def lookup(self, lookup_method, **kwargs):
        signature_hash = self.__generate_hash(kwargs)
        current_timestamp = int(round(time.time() * 1000))

        response = self.memory_cache.lookup(signature_hash)

        if response is None:
            response = self.__lookup_cache(signature_hash, current_timestamp)

        if response is None:
            logging.debug('Looking up signature {} from live source'.
                          format(signature_hash))
            json_resp = lookup_method(**kwargs)
            response = json.dumps(json_resp)

            if self.config['cache_error_responses'] or 'error' not in json_resp:
                self.__store_to_cache(signature_hash, current_timestamp, response)

        self.memory_cache.put(signature_hash, response)
        return json.loads(response)
