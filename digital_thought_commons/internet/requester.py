import logging

from requests import Response
from requests.sessions import Session
from urllib3.util import parse_url

from digital_thought_commons import internet


class RequesterSession(Session):

    def __init__(self, tor_proxy=None, internet_proxy=None) -> None:
        super().__init__()

        if tor_proxy is None:
            tor_proxy = {"http": 'socks5h://127.0.0.1:9150'}
        self.tor_proxy = tor_proxy
        self.internet_proxy = internet_proxy
        self.tor_requester = internet.retry_request_session(proxy=self.tor_proxy)
        self.internet_requester = internet.retry_request_session(proxy=self.internet_proxy)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def requester(self, url):
        try:
            parsed_url = parse_url(url)
            if parsed_url.host.lower().endswith('.onion'):
                logging.debug(f'URL: {url} required the TOR Requester')
                return self.tor_requester
            else:
                logging.debug(f'URL: {url} required the Internet Requester')
                return self.internet_requester
        except Exception as ex:
            logging.exception(str(ex))
            logging.error(f'Unable to determine requester from URL: {url}')

    def get(self, url, **kwargs) -> Response:
        return self.requester(url).get(url, **kwargs)

    def options(self, url, **kwargs) -> Response:
        return self.requester(url).options(url, **kwargs)

    def head(self, url, **kwargs) -> Response:
        return self.requester(url).head(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs) -> Response:
        return self.requester(url).post(url, data, json, **kwargs)

    def put(self, url, data=None, **kwargs) -> Response:
        return self.requester(url).put(url, data, **kwargs)

    def delete(self, url, **kwargs) -> Response:
        return self.requester(url).delete(url, **kwargs)

    def close(self) -> None:
        self.tor_requester.close()
        self.internet_requester.close()
