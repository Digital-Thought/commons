from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from typing import Union
from sqlalchemy.orm import sessionmaker

import json

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
        engine = create_engine(f'sqlite:///{path}')
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

    def get(self, key: str, default: Union[str, int, float, dict, bool, None] = None) -> Union[str, int, float, dict, bool, None]:
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