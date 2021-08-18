import urllib.parse as urlparse
from urllib.parse import parse_qs

from user_agents import parse

from digital_thought_commons.enrichers import suspicious_url_analyser


class Parsers:
    def __init__(self, elastic_server=None, elastic_port=None, elastic_api_key=None,
                 no_elastic=False):
        self.urlAnalyser = None
        if not no_elastic:
            self.urlAnalyser = suspicious_url_analyser.UrlAnalyser(
                elastic_server, elastic_port, elastic_api_key)
            self.urlAnalyser.learn()

    def parse_user_agent(self, user_agent):
        entry = {}
        if user_agent is not None and len(user_agent) > 10:
            ua = parse(user_agent)
            entry['user_agent'] = user_agent
            entry['friendly'] = str(ua)
            entry['browser_family'] = ua.browser.family
            entry['browser_version'] = ua.browser.version
            entry['browser_version_string'] = ua.browser.version_string

            entry['os_family'] = ua.os.family
            entry['os_version'] = ua.os.version
            entry['os_version_string'] = ua.os.version_string

            entry['device_family'] = ua.device.family
            entry['device_brand'] = ua.device.brand
            entry['device_model'] = ua.device.model

            entry['is_mobile'] = ua.is_mobile
            entry['is_tablet'] = ua.is_tablet
            entry['is_pc'] = ua.is_pc
            entry['is_touch_capable'] = ua.is_touch_capable
            entry['is_bot'] = ua.is_bot

        return entry

    def parse_url(self, url):
        temp_url = url
        if not url.startswith("http"):
            temp_url = "http://{}".format(url)

        parsed = urlparse.urlparse(temp_url)
        details = {'url': url, 'url_domain': parsed.netloc, 'parameters': []}

        for key, value in parse_qs(parsed.query).items():
            details['parameters'].append({'name': key, 'value': value})

        if self.urlAnalyser is not None:
            details['is_suspicious'] = self.urlAnalyser.is_suspicious(
                url.lower().replace("https://", "").replace("http://", ""))

        return details
