from .__dbc__ import SocketClient
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from digital_thought_commons.digests import Digest

import os
import logging

Cache_Base = declarative_base()
cache_path = f"{os.getenv('DATA_PATH', './data')}/deathbycaptcha_cache.db"
engine = create_engine(f'sqlite:///{cache_path}')
call_count = 0


class SolvedCaptcha(Cache_Base):
    __tablename__ = 'solved_captcha'

    id = Column(String(100), primary_key=True)
    text = Column(String(100))
    captcha = Column(String(100))
    status = Column(Integer)
    is_correct = Column(Boolean)

    client: "Client" = None
    from_cache: bool = False

    def mark_invalid(self):
        self.client.failed(self)


Cache_Base.metadata.create_all(engine)


class Client(object):

    def __init__(self, username: str = None, password: str = None, auth_token: str = None) -> None:
        super().__init__()
        global cache_path, Cache_Base
        self.username = os.getenv('DBC_USERNAME', username)
        self.password = os.getenv('DBC_PASSWORD', password)
        self.auth_token = os.getenv('DBC_AUTH_TOKEN', auth_token)

        if self.username is None or self.password is None or self.auth_token is None:
            raise EnvironmentError("Missing one or more of [username, password, auth_token].  Either as passed parameters or environment settings.")

        self.dbc_client = SocketClient(self.username, self.password, self.auth_token)
        self.engine = create_engine(f'sqlite:///{cache_path}')
        Cache_Base.metadata.bind = self.engine
        self.DBSession = sessionmaker(bind=engine)
        self.session = self.DBSession()
        self.log_details()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.log_details()
        self.dbc_client.close()
        self.session.close()

    def log_details(self):
        user = self.dbc_client.get_user()

        message = f'DeathByCaptcha >> Calls made: {call_count}, User: {user["user"]}, Banned: {user["is_banned"]}, Balance: {user["balance"]}, Rate: {user["rate"]}'
        if user["is_banned"]:
            logging.error('DeathByCaptcha >> User is Banned!')
            logging.error(message)
        elif user["balance"] <= 10:
            logging.warning('DeathByCaptcha >> Balance is LOW!')
            logging.warning(message)
        else:
            logging.info(message)

    def solve(self, img_bytes: bytes) -> SolvedCaptcha:
        digest = Digest()
        digest.update_from_bytes(img_bytes)

        solved_captcha: SolvedCaptcha = self.session.query(SolvedCaptcha).get(digest.sha256)

        if solved_captcha:
            logging.debug(f'Recovered solved captcha {digest.sha256} from local cache.')
            solved_captcha.client = self
            solved_captcha.from_cache = True
            return solved_captcha

        captcha = self.dbc_client.decode(img_bytes)
        solved_captcha = None
        if captcha:
            solved_captcha = SolvedCaptcha()
            solved_captcha.id = digest.sha256
            solved_captcha.captcha = captcha['captcha']
            solved_captcha.text = captcha['text']
            solved_captcha.is_correct = captcha['is_correct']
            if 'status' in captcha:
                solved_captcha.status = captcha['status']
            solved_captcha.client = self
            self.session.add(solved_captcha)
            self.session.commit()

            global call_count
            call_count += 1
            if call_count % 10 == 0:
                self.log_details()

        return solved_captcha

    def failed(self, solved_captcha: SolvedCaptcha):
        logging.warning(f'Marking Captcha {solved_captcha.captcha} as incorrect.')

        cached_entry = self.session.query(SolvedCaptcha).get(solved_captcha.id)
        if cached_entry:
            self.session.delete(cached_entry)
            self.session.commit()

        self.dbc_client.report(solved_captcha.captcha)
