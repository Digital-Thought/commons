from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import json
import yaml
import logging
import os
import shutil

from typing import Union

Base = declarative_base()


class Setting(Base):
    """
    The Base Settings Model
    """
    __tablename__ = 'persistent_settings'

    id = Column(Integer, primary_key=True)
    value_name = Column(String(100))
    value = Column(String(1024))
    type = Column(String(24))


class PersistentSettingStore(object):
    """
    A helper class to persist settings to SQL List database at the defined path.
    """

    def __init__(self, path: str) -> None:
        """
        Initialise the persistent settings store.
        SQLite DB will be created at the provided path.
        Will open the existing database if already exists.
        :param path: The path to the SQLite database
        :type path: str
        """
        engine = create_engine(f'sqlite:///{path}?check_same_thread=False')
        Base.metadata.create_all(engine)
        self.DBSession = sessionmaker(bind=engine)
        super().__init__()

    def store(self, key: str, value: Union[str, int, float, dict, bool]) -> Union[str, int, float, dict, bool]:
        """

        :param key:
        :type key:
        :param value:
        :type value:
        :return:
        :rtype:
        """

        if self.get(key=key):
            self.__delete__(key=key)

        session = self.DBSession()
        setting = Setting()
        setting.value_name = key

        if isinstance(value, str):
            setting.type = 'str'
            setting.value = value
        elif isinstance(value, bool):
            setting.type = 'bool'
            setting.value = str(value)
        elif isinstance(value, int):
            setting.type = 'int'
            setting.value = str(value)
        elif isinstance(value, float):
            setting.type = 'float'
            setting.value = str(value)
        elif isinstance(value, dict):
            setting.type = 'dict'
            setting.value = json.dumps(value)
        else:
            raise Exception('Unsupported value type')

        session.add(setting)
        session.commit()
        return value

    def __delete__(self, key: str):
        session = self.DBSession()
        session.query(Setting).filter(Setting.value_name == key).delete()
        session.commit()

    def delete(self, key) -> Union[str, int, float, dict, bool, None]:
        """

        :param key:
        :type key:
        :return:
        :rtype:
        """
        setting = self.get(key)
        if setting is not None:
            self.__delete__(key)
            return setting
        return None

    def get(self, key: str, default: Union[str, int, float, dict, bool, None] = None) -> Union[
        str, int, float, dict, bool, None]:
        """

        :param key:
        :type key:
        :param default:
        :type default:
        :return:
        :rtype:
        """
        session = self.DBSession()
        setting = session.query(Setting).filter(Setting.value_name == key).first()
        if not setting:
            return default

        if setting.type == 'str':
            return setting.value
        elif setting.type == 'int':
            return int(setting.value)
        elif setting.type == 'float':
            return float(setting.value)
        elif setting.type == 'bool':
            return setting.value == 'True'
        elif setting.type == 'dict':
            return json.loads(setting.value)
        else:
            raise Exception('Unsupported value type')


DEFAULT_CONFIG_LOCATION = './config/app_config.yaml'


class Configuration(dict):
    """
    Configuration Dictionary for OSINT Platform.
    Configuration can be defined in the YAML file.
    Default YAML file path is: './config/osint_config.yaml'
    """

    def __init__(self, path: str) -> None:
        """
        Initialises the configuration settings dictionary.
        :param path: The path to the YAML file to load configuration from
        :type path: str
        """
        self.config_file = path
        self.persistent_settings_store = None
        super().__init__()
        self.load_yaml_file(self.config_file)

        if os.path.exists(os.path.abspath(self.get('settings.temp_directory', './temp'))):
            logging.warning(
                f"Deleting old Temp directory: {os.path.abspath(self.get('settings.temp_directory', './temp'))}")
            shutil.rmtree(os.path.abspath(self.get('settings.temp_directory', './temp')))

        self.persistent_settings_store = PersistentSettingStore(path=f'{self.get_data_directory()}/persistent.settings')

        logging.info(f'Data Path: {self.get_data_directory()}')
        logging.info(f'Temp Path: {self.get_temp_directory()}')
        logging.info(f'Loaded configuration from: {self.config_file}')

    def load_yaml_file(self, path: Union[str, None] = None) -> 'Configuration':
        """
        Loads the specified YAML file into the configuration.
        If a path is not provided, it will use the file path specific when the 'Configuration' was initialised.
        :param path: The path to the YAML file to load, or None if to load from early defined path
        :type path: Union[str, None]
        :return: Newly loaded configuration
        :rtype: 'Configuration'
        """
        self.config_file = path if path else self.config_file
        with open(self.config_file, 'r', encoding='UTF-8') as file:
            self.clear()
            self.update(yaml.safe_load(file))
        return self

    def reload_yaml(self) -> 'Configuration':
        """
        Reloads the configuration from the previously defined YAML file path.
        Note: this will clear all current settings before re-loading.
        :return: Re-loaded configuration
        :rtype: 'Configuration'
        """
        logging.info(f'Re-loading configuration from: {self.config_file}')
        self.load_yaml_file(self.config_file)
        return self

    def get_requests_tor_proxy(self) -> dict:
        """
        Gets TOR Proxy configuration in a format compatible with Requests
        :return: Dictionary of HTTP and HTTPS configuration for TOR Proxy.
        :rtype: dict
        """
        proxy = self.get('settings.proxies.tor_proxy', '127.0.0.1:9150')
        return {"http": 'socks5h://' + proxy,
                "https": 'socks5h://' + proxy}

    def get_selenium_tor_proxy(self) -> str:
        """
        Gets TOR Proxy configuration in a format compatible with Selenium
        :return: String value for proxy configuration.
        :rtype: str
        """
        proxy = self.get('settings.proxies.tor_proxy', '127.0.0.1:9150')
        return '--proxy-server=socks5://' + proxy

    def get_data_directory(self) -> str:
        """
        Get the absolute path for the Data directory.
        It will create it if it does not exist.
        :return: The absolute path to the data directory
        :rtype: str
        """
        absolute_path = os.path.abspath(self.get('settings.data_directory', './data'))
        os.makedirs(absolute_path, exist_ok=True)
        return absolute_path

    def get_temp_directory(self) -> str:
        """
        Get the absolute path for the Temp directory.
        It will create it if it does not exist.
        :return: The absolute path to the Temp directory
        :rtype: str
        """
        absolute_path = os.path.abspath(self.get('settings.temp_directory', './temp'))
        os.makedirs(absolute_path, exist_ok=True)
        return absolute_path

    def __setitem__(self, key, value):
        # if the value of a setting is changed or new setting added,
        # then it will add it to the persistent store and will override any settings in the config YAML.
        return self.persistent_settings_store.store(key=key, value=value)

    def get(self, key, default=None):
        try:
            value = self.__getitem__(key)
            if isinstance(value, str) and str(value).startswith('ENV/'):
                return os.getenv(str(value).replace('ENV/', '').strip(), value)
            if not value:
                return default
            return value
        except KeyError:
            return default

    def __getattr__(self, key):
        try:
            return self.__getitem__(key)
        except KeyError:
            raise AttributeError("object has no attribute '%s'" % key)

    def __getitem__(self, key):
        if self.persistent_settings_store:
            persistent_value = self.persistent_settings_store.get(key)
            if persistent_value is not None:
                return persistent_value
        keys = key.split('.')
        if len(keys) == 1:
            return dict.__getitem__(self, key)
        else:
            data = self.copy()
            for key in keys:
                if key in data:
                    data = data[key]
                else:
                    return None
            return data


config: Union[Configuration, None] = None
"""
The loaded Configuration.  This will be None until load(path) is called.
"""


def load(path: str = DEFAULT_CONFIG_LOCATION) -> Configuration:
    """
    Loads the configuration from the YAML file.
    If the YAML file is not specified in 'path' the default location is used: './config/osint_config.yaml'
    :param path: Path to the YAML file with the configuration.  If not provided, the default DEFAULT_CONFIG_LOCATION used
    :type path: str
    :return: The loaded configuration
    :rtype: Configuration
    """
    global config
    config = Configuration(path=path)
    return config
