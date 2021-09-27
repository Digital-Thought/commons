import argparse
import logging
import os
import json

from argparse import ArgumentParser
from digital_thought_commons import logging as logger
from art import *


class AbstractApp(object):

    def __init__(self, app_spec_path: str = None) -> None:
        super().__init__()
        if app_spec_path is None or not os.path.exists(app_spec_path):
            raise Exception(f"Invalid app_spec_path provided: {app_spec_path}")

        with open(app_spec_path, "r") as spec:
            self.app_spec = json.load(spec)

        for required_key in ['description', 'version', 'short_name', 'full_name']:
            if required_key not in self.app_spec:
                raise Exception(f"Missing '{required_key}' key in app_spec: {app_spec_path}")

        self.log_path = None

    def version(self) -> str:
        return self.app_spec["version"]

    def define_args(self, arg_parser: ArgumentParser):
        raise NotImplementedError

    def main(self, args):
        raise NotImplementedError

    def run(self):
        arg_parser = argparse.ArgumentParser(prog=self.app_spec["short_name"], description=self.app_spec["description"])
        self.define_args(arg_parser)

        self.log_path = logger.init(self.app_spec["short_name"])
        logging.info(f'{self.app_spec["full_name"]} ({self.app_spec["short_name"]}), Version: {self.app_spec["version"]}')
        app_art = text2art(self.app_spec["full_name"])
        if "organisation" in self.app_spec:
            print(text2art(self.app_spec["organisation"], "white_bubble"))
        print(app_art)
        print(f'Version: {self.app_spec["version"]}')
        if self.log_path is not None:
            print(f'Log Path: {self.log_path}')
        print('\n')

        args = arg_parser.parse_args()

        self.main(args)
