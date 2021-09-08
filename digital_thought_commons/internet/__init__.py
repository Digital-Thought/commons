from urllib.parse import unquote

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from digital_thought_commons import base64

from digital_thought_commons.internet import requester


class IncompleteDownload(Exception):
    pass


class MaxDownloadRetriesReached(Exception):
    pass


class DownloadNotFound(Exception):
    pass


class DownloadException(Exception):
    pass


def new_requester(tor_proxy=None, internet_proxy=None):
    if tor_proxy is None:
        tor_proxy = {"http": 'socks5h://127.0.0.1:9150'}
    return requester.RequesterSession(tor_proxy=tor_proxy, internet_proxy=internet_proxy)


def retry_request_session(retries=3, backoff_factor=0.3, status_forcelist=(400, 500, 502, 504), timeout=60,
                          user_agent='Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0', headers={},
                          proxy=None):
    base_headers = {'User-Agent': user_agent}
    base_headers.update(headers)
    request_session = requests.Session()
    request_session.timeout = timeout

    request_session.headers.update(base_headers)

    if proxy is not None:
        request_session.proxies.update(proxy)

    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )

    adapter = HTTPAdapter(max_retries=retry)
    request_session.mount('http://', adapter)
    request_session.mount('https://', adapter)

    return request_session


def source_details(requester_session, source_url):
    headers = requester_session.head(source_url, allow_redirects=True)

    if headers.status_code == 404:
        raise DownloadNotFound(f'URL {source_url} not found.  Download failed.')

    file_name = unquote(source_url.split('/')[-1])
    length = -1

    if 'content-disposition' in headers.headers.keys():
        file_name = headers.headers.get('content-disposition').split(';')[1].strip().split("=")[1].replace('"', '')

    if 'Content-Length' in headers.headers.keys():
        length = int(headers.headers.get('Content-Length'))

    return file_name, length


def check_supports_range(requester_session, source_url):
    resume_headers = {'Range': 'bytes=1-5'}
    resp = requester_session.head(source_url, headers=resume_headers, allow_redirects=True)

    if resp.status_code == 404:
        raise DownloadNotFound(f'URL {source_url} not found.  Download failed.')

    return resp.status_code == 206


def get_images_as_base64_strings(base_url, requester, *html_strings) -> List[dict]:
    images: List[dict] = []
    for html in html_strings:
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            if img.has_attr('src'):
                ref: str = img['src']
                if not ref.lower().startswith('data:'):
                    ref = urljoin(base_url, ref)
                    response = requester.get(ref)
                    if response.status_code in [200, 201] and response.headers['Content-Type'].startswith('image'):
                        images.append({'base64': base64.to_base64_string(response.content),
                                       'type': response.headers['Content-Type']})
                else:
                    images.append({'base64': ref.split(',')[1], 'type': ref.split(':')[1].split(';')[0]})

    return images
