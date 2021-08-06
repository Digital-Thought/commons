import logging
import logging.config
import os
import pathlib
from datetime import datetime

import yaml
from colorlog import ColoredFormatter

logging_resource_folder = "{}/../_resources/logging".format(str(pathlib.Path(__file__).parent.absolute()))
default_logging_configuration_file = f'{logging_resource_folder}/default_config.yaml'
logging_configuration_file = './config/loggingConfig.yaml'

DEFAULT_FORMATTER = '%(log_color)s%(asctime)s - %(levelname)-8s - %(processName)s.%(process)d - %(threadName)s.%(thread)d - %(module)s.%(funcName)s.%(lineno)-3d - %(message)s%(reset)s'
DEFAULT_ELASTIC_FORMATTER = 'ELASTIC: %(log_color)s%(asctime)s - %(levelname)-8s - %(processName)s.%(process)d - %(threadName)s.%(thread)d - %(module)s.%(funcName)s.%(lineno)-3d - %(message)s%(reset)s'


def init(app_name, configuration_file: str = None):
    if configuration_file and not os.path.exists(configuration_file):
        raise FileNotFoundError(f'Missing specified logging configuration file: {configuration_file}')

    using_default = False

    if configuration_file and os.path.exists(configuration_file):
        logging_config_file = configuration_file
    elif os.path.exists(logging_configuration_file):
        logging_config_file = logging_configuration_file
    else:
        logging_config_file = default_logging_configuration_file
        using_default = True

    with open(logging_config_file, 'r') as config_file:
        logging_config = yaml.safe_load(config_file)

    if using_default:
        log_folder = './logs/{}'.format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(log_folder, exist_ok=True)

        formatter = ColoredFormatter(DEFAULT_FORMATTER)

        console_stream = logging.StreamHandler()
        console_stream.setLevel(logging.DEBUG)
        console_stream.setFormatter(formatter)
        console_stream.name = 'console_ALL'

        logging_config['handlers']['logfile_ALL']['filename'] = '{}/info-{}'.format(log_folder, app_name)
        logging_config['handlers']['logfile_ERR']['filename'] = '{}/error-{}'.format(log_folder, app_name)
        logging_config['handlers']['logfile_ELASTIC']['filename'] = '{}/elastic-{}'.format(log_folder, app_name)
        logging.config.dictConfig(logging_config)
        logging.getLogger().addHandler(console_stream)
        logging.getLogger("defaultLogger").addHandler(console_stream)

        logging.getLogger('console').addHandler(console_stream)
        logging.getLogger('console').debug('Logging configuration read from: {}'.format(logging_config_file))

    else:
        logging.config.dictConfig(logging_config)
        logging.debug('Logging configuration read from: {}'.format(logging_config_file))
