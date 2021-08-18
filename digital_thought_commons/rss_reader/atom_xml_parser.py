import xmltodict

from bs4 import BeautifulSoup
from digital_thought_commons import date_utils
from digital_thought_commons.internet import requester


class AtomXMLParser(object):

    FEED_ELEMENT_READERS = {
        'id': None,
        'title': '__content_parser__',
        'updated': '__date_parser__',
        'author': '__author_parser__',
        'link': '__link_parser__',
        'category': '__category_parser__',
        'contributor': '__author_parser__',
        'generator': '__generator_parser__',
        'content': '__content_parser__',
        'icon': None,
        'logo': None,
        'subtitle': None,
        'summary': '__content_parser__',
        'rights': '__content_parser__'
    }

    def __init__(self, atom_xml: str) -> None:
        super().__init__()
        atom = xmltodict.parse(atom_xml)
        if 'feed' not in atom or atom['feed']['@xmlns'] != 'http://www.w3.org/2005/Atom':
            raise Exception(f'XML content does not conform to expected atom+xml')

        self.feed_elements = self.process_feed_elements(atom['feed'])
        self.entries = atom['feed']['entry']

    @staticmethod
    def __date_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = date_utils.convert_string_datetime(obj)

    @staticmethod
    def __author_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}_name'] = obj['name']
        details[f'{prefix}{key}_uri'] = obj.get('uri', None)
        details[f'{prefix}{key}_email'] = obj.get('email', None)

    @staticmethod
    def __generator_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj['#text']
        details[f'{prefix}{key}_uri'] = obj.get('@uri', None)
        details[f'{prefix}{key}_version'] = obj.get('@version', None)

    @staticmethod
    def __category_parser__(key, obj, details, prefix=''):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        details[f'{prefix}{key}'] = obj['@term']

    @staticmethod
    def __content_parser__(key, obj, details, prefix=''):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        if isinstance(obj, dict):
            type = obj.get('@type', None)
            src = obj.get('@src', None)
            if type and type == 'html':
                details[f'{prefix}{key}_raw'] = obj.get('#text', '')
                soup = BeautifulSoup(details[f'{prefix}{key}_raw'], 'html.parser')
                details[f'{prefix}{key}'] = soup.get_text(strip=True, separator='\n')
            if src:
                with requester.RequesterSession() as request:
                    response = request.get(src)
                    if response.status_code == 200:
                        details[f'{prefix}{key}_raw'] = response.text
                        soup = BeautifulSoup(response.text, 'html.parser')
                        details[f'{prefix}{key}'] = soup.get_text(strip=True, separator='\n')
        else:
            details[f'{prefix}{key}'] = obj

    @staticmethod
    def __link_parser__(key, obj, details, prefix=None):
        if prefix:
            prefix = f'{prefix}.'
        else:
            prefix = str()
        if isinstance(obj, dict):
            obj = [obj]
        link = []
        for oj in obj:
            lnk = {f'href': oj['@href']}
            rel = oj.get('@rel', 'alternate')
            lnk[f'rel'] = rel
            if rel == 'alternate':
                with requester.RequesterSession() as request:
                    response = request.get(oj['@href'])
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        lnk[f'alternate_content'] = soup.get_text(strip=True, separator='\n')
                        lnk[f'alternate_content_raw'] = response.text
            lnk[f'type'] = oj.get('@type', None)
            lnk[f'hreflang'] = oj.get('@hreflang', None)
            lnk[f'title'] = oj.get('@title', None)
            lnk[f'length'] = oj.get('@length', None)
            link.append(lnk)
        details[f'{prefix}{key}'] = link

    def process_feed_elements(self, atom: dict) -> dict:
        feed_details = {'feed.type': 'atom+xml'}
        for key in atom:
            if key in self.FEED_ELEMENT_READERS and self.FEED_ELEMENT_READERS[key]:
                setter_method = getattr(self, self.FEED_ELEMENT_READERS[key])
                setter_method(key=key, obj=atom[key], details=feed_details, prefix='feed')
            elif key in self.FEED_ELEMENT_READERS:
                feed_details[f'feed.{key}'] = atom[key]

        for key in feed_details.copy():
            if not feed_details[key]:
                feed_details.pop(key)
        return feed_details

    def read(self):
        for entry in self.entries:
            entry_dict = self.feed_elements.copy()
            for key in entry:
                if key in self.FEED_ELEMENT_READERS and self.FEED_ELEMENT_READERS[key]:
                    setter_method = getattr(self, self.FEED_ELEMENT_READERS[key])
                    setter_method(key=key, obj=entry[key], details=entry_dict, prefix='')
                elif key in self.FEED_ELEMENT_READERS:
                    entry_dict[f'{key}'] = entry[key]

            for key in entry_dict.copy():
                if not entry_dict[key] or len(str(entry_dict[key]).strip()) == 0:
                    entry_dict.pop(key)

            yield entry_dict
