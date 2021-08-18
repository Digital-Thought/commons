import logging

import xmltodict

from bs4 import BeautifulSoup
from digital_thought_commons import date_utils
from digital_thought_commons.internet import requester


class RSSXMLParser(object):

    FEED_ELEMENT_READERS = {
        'title': None,
        'pubDate': '__date_parser__',
        'lastBuildDate': '__date_parser__',
        'creator': '__creator_parser__',
        'link': '__link_parser__',
        'category': '__category_parser__',
        'contributor': '__author_parser__',
        'generator': None,
        'docs': None,
        'language': None,
        'description': None,
        'image': '__image_parser__',
        'guid': '__guid_parser__',
        'content:encoded': '__content_encoded_parser__',
        'content': None,
        'copyright': None,
        'comments': None,
        'managingEditor': None,
        'webMaster': None
    }

    def __init__(self, atom_xml: str) -> None:
        super().__init__()
        rss = xmltodict.parse(atom_xml)
        if 'rss' not in rss or rss['rss']['@version'] != '2.0':
            raise Exception(f'XML content does not conform to expected rss+xml v2.0 format')

        self.feed_elements = self.process_feed_elements(rss['rss']['channel'])
        self.entries = rss['rss']['channel']['item']

    @staticmethod
    def __content_encoded_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        soup = BeautifulSoup(obj, 'html.parser')
        details[f'{prefix}content'] = soup.get_text(strip=True, separator='\n')
        details[f'{prefix}content_raw'] = obj

    @staticmethod
    def __guid_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj['#text']

    @staticmethod
    def __creator_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj

    @staticmethod
    def __date_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = date_utils.convert_string_datetime(obj)

    @staticmethod
    def __image_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj

    @staticmethod
    def __link_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj
        with requester.RequesterSession() as request:
            try:
                response = request.get(obj)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    details[f'{prefix}{key}_alternate_content'] = soup.get_text(strip=True, separator='\n')
                    details[f'{prefix}{key}_alternate_content_raw'] = response.text
            except Exception as ex:
                logging.exception(str(ex))

    @staticmethod
    def __category_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj

    def process_feed_elements(self, channel: dict) -> dict:
        feed_details = {'feed.type': 'rss+xml'}
        for key in channel:
            org_key = key
            key = key.replace('sy:', '').replace('dc:', '')
            if key in self.FEED_ELEMENT_READERS and self.FEED_ELEMENT_READERS[key]:
                setter_method = getattr(self, self.FEED_ELEMENT_READERS[key])
                setter_method(key=key, obj=channel[org_key], details=feed_details, prefix='feed')
            elif key in self.FEED_ELEMENT_READERS:
                feed_details[f'feed.{key}'] = channel[org_key]

        for key in feed_details.copy():
            if not feed_details[key]:
                feed_details.pop(key)
        return feed_details

    def read(self):
        for entry in self.entries:
            entry_dict = self.feed_elements.copy()
            for key in entry:
                org_key = key
                key = key.replace('sy:', '').replace('dc:', '')
                if key in self.FEED_ELEMENT_READERS and self.FEED_ELEMENT_READERS[key]:
                    setter_method = getattr(self, self.FEED_ELEMENT_READERS[key])
                    setter_method(key=key, obj=entry[org_key], details=entry_dict, prefix='')
                elif key in self.FEED_ELEMENT_READERS:
                    entry_dict[f'{key}'] = entry[org_key]

            for key in entry_dict.copy():
                if not entry_dict[key] or len(str(entry_dict[key]).strip()) == 0:
                    entry_dict.pop(key)

            yield entry_dict