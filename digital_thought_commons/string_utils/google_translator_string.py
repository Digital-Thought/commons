import json
import locale
import logging

from langdetect import detect
from google.cloud import translate_v2 as translate
import os


def set_auth_file(auth_file: str):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = auth_file


def __translate_string__(text: str, target_local: str):
    if target_local.startswith('en_'):
        target_local = target_local.split("_")[0].strip()

    if detect(text) == target_local:
        logging.info(f'Source text is already {target_local}.  Not performing translation.')
        return {'translatedText': text, 'detectedSourceLanguage': target_local, 'input': text}

    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') is None:
        logging.warning('No GOOGLE_APPLICATION_CREDENTIALS defined. No translation performed.')
        return {'translatedText': text, 'detectedSourceLanguage': 'UNKNOWN - NO LICENCE',
                'input': text, 'error': 'No GOOGLE_APPLICATION_CREDENTIALS defined'}

    try:
        translate_client = translate.Client()
        return translate_client.translate(text, target_language=target_local)
    except Exception as ex:
        logging.exception(str(ex))
        return {'translatedText': text, 'detectedSourceLanguage': 'UNKNOWN - EXCEPTION',
                'input': text, 'error': str(ex)}


class GoogleTranslateString(object):

    def __init__(self, string: str) -> None:
        super().__init__()
        self.__cached_translations__ = {}
        self.original_string = string

    def __str__(self) -> str:
        return self.get_locale_string()

    def __translate(self, locale: str):
        if locale not in self.__cached_translations__:
            self.__cached_translations__[locale] = __translate_string__(self.original_string, locale)

        return self.__cached_translations__[locale]

    def get_locale_string(self) -> str:
        return self.__translate(locale=locale.getdefaultlocale()[0])['translatedText']

    def get_as_locale(self, locale: str) -> str:
        return self.__translate(locale=locale)['translatedText']

    def get_original(self) -> str:
        return self.original_string

    def get_original_locale(self) -> str:
        return self.__translate(locale=locale.getdefaultlocale()[0])['detectedSourceLanguage']
