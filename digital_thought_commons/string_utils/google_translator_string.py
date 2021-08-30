import json
import locale

from google.cloud import translate_v2 as translate
import os


def __set_auth_file(auth_file: str):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = auth_file


def __translate_string__(text: str, target_local: str) -> str:
    if target_local.startswith('en_'):
        target_local = target_local.split("_")[0].strip()
    translate_client = translate.Client()
    return translate_client.translate(text, target_language=target_local)


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
