from selenium import webdriver as wd
from selenium.webdriver.chrome import webdriver
from urllib3.util import parse_url
from typing import List
import logging


class Scrapper():

    def __init__(self, tor_proxy=None, internet_proxy=None, headless=True, chromium_driver="chromedriver") -> None:
        super().__init__()

        if tor_proxy is None:
            tor_proxy = '--proxy-server=socks5://127.0.0.1:9150'
        self.tor_proxy = tor_proxy
        self.internet_proxy = internet_proxy
        self.headless = headless
        self.chromium_driver = chromium_driver

        self.tor_scrapper = None
        self.internet_scrapper = None

    def __initialise_scrapper(self, proxy) -> webdriver.WebDriver:
        prefs = {
            "translate_whitelists": {"ru": "en"},
            "translate": {"enabled": "true"}
        }
        options = wd.ChromeOptions()
        options.add_experimental_option('prefs', prefs)
        if self.headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.headless = True
        if proxy:
            options.add_argument(proxy)
        return wd.Chrome(executable_path=self.chromium_driver, options=options)

    def get_tor_scrapper(self):
        return self.tor_scrapper

    def get_internet_scrapper(self):
        return self.internet_scrapper

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.tor_scrapper:
            self.tor_scrapper.close()
        if self.internet_scrapper:
            self.internet_scrapper.close()

    def __scrapper(self, url, force_tor=False) -> webdriver.WebDriver:
        try:
            parsed_url = parse_url(url)
            if parsed_url.host.lower().endswith('.onion') or force_tor:
                logging.debug(f'URL: {url} required the TOR Requester')
                if not self.tor_scrapper:
                    self.tor_scrapper = self.__initialise_scrapper(proxy=self.tor_proxy)
                return self.tor_scrapper
            else:
                logging.debug(f'URL: {url} required the Internet Requester')
                if not self.internet_scrapper:
                    self.internet_scrapper = self.__initialise_scrapper(proxy=self.internet_proxy)
                return self.internet_scrapper
        except Exception as ex:
            logging.exception(str(ex))
            logging.error(f'Unable to determine requester from URL: {url}')

    def get(self, url: str, force_tor=False) -> webdriver.WebDriver:
        chosen_scrapper = self.__scrapper(url, force_tor)
        chosen_scrapper.get(url=url)
        return chosen_scrapper


persistent_scrappers = {}


def get_persistent_scrapper(name: str, tor_proxy=None, internet_proxy=None, headless=True, chromium_driver="chromedriver") -> Scrapper:
    if name not in persistent_scrappers:
        persistent_scrappers[name] = Scrapper(tor_proxy, internet_proxy, headless, chromium_driver)
    return persistent_scrappers[name]


def close_persistent_scrapper(name: str):
    if name in persistent_scrappers:
        persistent_scrappers[name].close()
