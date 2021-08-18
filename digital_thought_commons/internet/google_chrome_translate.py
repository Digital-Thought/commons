import time

from selenium import webdriver as wd
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.common.keys import Keys
from urllib3.util import parse_url
from typing import List
import logging
import tempfile


class GoogleChromeTranslate(object):

    def __init__(self, chromium_driver="./chromedriver") -> None:
        super().__init__()
        self.chromium_driver = chromium_driver
        self.chrome: webdriver.WebDriver = self.__initialise_scrapper()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.chrome.close()

    def __initialise_scrapper(self) -> webdriver.WebDriver:
        prefs = {
            "translate_whitelists": {"ru": "en", "th": "en"},
            "translate": {"enabled": "true"}
        }
        options = wd.ChromeOptions()
        options.add_experimental_option('prefs', prefs)
        return wd.Chrome(executable_path=self.chromium_driver, options=options)

    def translate(self, html_content: str):
        resp = {"original": html_content, "translated": "", "error": False}
        temp = tempfile.NamedTemporaryFile(suffix='.html')
        try:
            temp.write(html_content.encode("utf-8"))
            temp.seek(0)
            self.chrome.get(f'file://{temp.name}')
            for i in range(5):
                self.chrome.find_element_by_css_selector('body').send_keys(Keys.PAGE_DOWN)
                time.sleep(1)
            resp["translated"] = self.chrome.page_source
        except Exception as ex:
            logging.exception(str(ex))
            resp["error"] = True
            resp["translated"] = str(ex)
        finally:
            temp.close()
        return resp
