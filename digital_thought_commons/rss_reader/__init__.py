from digital_thought_commons.internet import requester
from typing import List, Any
from atom_xml_parser import AtomXMLParser
from rss_xml_parser import RSSXMLParser

import digital_thought_commons
import logging


class FeedEntry(dict):
    KEY_MAPPINGS = {
        "id": ['id', 'guid'],
        "title": ["title"],
        "date": ["updated", "pubDate", "lastBuildDate"],
        "author": ["author", "creator"],
        "link": ["link"],
        "tags": ["category"],
        "contributor": ["contributor"],
        "generator": ["generator"],
        "content": ["content"],
        "content_raw": ["content_raw"],
        "icon": ["icon", "logo"],
        "subtitle": ["subtitle"],
        "summary": ["summary", "description"],
        "rights": ["rights", "copyright"],
        "docs": ["docs"],
        "language": ["language"],
        "media": ["image"],
        "comments": ["comments"],
        "editor": ["managingEditor"],
        "master": ["webMaster"]
    }

    def __init__(self, feed: dict) -> None:
        super().__init__()
        super().__setitem__('feed', {})
        super().__setitem__('_raw', feed)
        for key in feed:
            self[key] = feed[key]

    def __setitem__(self, key, value):
        if len(key.split('.')) > 1:
            for mapped_key in self.KEY_MAPPINGS:
                if key.split('.')[1] in self.KEY_MAPPINGS[mapped_key]:
                    super().get('feed')[mapped_key] = value
        else:
            for mapped_key in self.KEY_MAPPINGS:
                if key in self.KEY_MAPPINGS[mapped_key]:
                    super().__setitem__(mapped_key, value)

    def __setattr__(self, name: str, value: Any) -> None:
        self.__setitem__(name, value)

    def get(self, key, default=None):
        try:
            value = self.__getitem__(key)
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
        if key in self.KEY_MAPPINGS:
            return super().__getitem__(key)
        else:
            return None


def read(rss_url: str, tor_proxy=None, internet_proxy=None) -> List[FeedEntry]:
    with requester.RequesterSession(tor_proxy=tor_proxy, internet_proxy=internet_proxy) as request:
        try:
            user_agent = f'Digital-Thought;RSS-Reader / {digital_thought_commons.__version__}'
            logging.info(f'RSS Reader Call to: {rss_url}')
            response = request.get(url=rss_url, headers={'User-agent': user_agent})
            if response.status_code != 200:
                raise Exception(f'Request returned a status code of {response.status_code}. Content: {response.text}')

            if 'Content-Type' in response.headers and 'application/atom+xml' in response.headers['Content-Type']:
                atom_parser = AtomXMLParser(response.text)
                for entry in atom_parser.read():
                    yield FeedEntry(entry)
            elif 'Content-Type' in response.headers and 'application/rss+xml' in response.headers['Content-Type']:
                rss_xml_parser = RSSXMLParser(response.text)
                for entry in rss_xml_parser.read():
                    yield FeedEntry(entry)
            else:
                rss_xml_parser = RSSXMLParser(response.text)
                for entry in rss_xml_parser.read():
                    yield FeedEntry(entry)

        except Exception as ex:
            logging.exception(str(ex))

            raise ex
