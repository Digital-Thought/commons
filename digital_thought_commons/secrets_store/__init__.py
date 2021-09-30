import os
import pathlib
import logging
import digital_thought_commons.logging as logger
import argparse
import random
import string

from shutil import copyfile
from pykeepass import PyKeePass


class SecretsStoreException(Exception):
    pass


DEFAULT_PASSWORD = 'password'
SECRETS_STORE_DIRECTORY = f"{os.getenv('DATA_PATH', './data')}"
SECRETS_STORE_PATH = f"{SECRETS_STORE_DIRECTORY}/secrets.store.kdbx"
SECRETS_TEMPLATE = str(pathlib.Path(__file__).parent.absolute()) + '/../_resources/secrets_store/secrets.store.kdbx'
SECRETS_STORE_GROUP = "Secrets_Store"
SECRETS_ENV_TAG = "ENV"

os.makedirs(SECRETS_STORE_DIRECTORY, exist_ok=True)


class SecretsStore(object):

    def __init__(self, password: str = os.getenv('SECRETS_STORE_PASSWORD', None)) -> None:
        super().__init__()
        if not os.path.exists(SECRETS_STORE_PATH):
            raise SecretsStoreException(f'A Secrets Store does not exists at: {SECRETS_STORE_PATH}.')

        if password is None:
            raise SecretsStoreException('No password was provided for Secrets Store.  '
                                        'Password must be provided or environment variable SECRETS_STORE_PASSWORD set.')

        try:
            self.keepass_instance = PyKeePass(SECRETS_STORE_PATH, password)
            self.__set_environment_variables__()
        except Exception as ex:
            raise SecretsStoreException(f'Failed to open Secrets Store: {str(ex)}')

        logging.info(f'Successfully opened Secrets Store: {SECRETS_STORE_PATH}')

    def __store_group__(self):
        return self.keepass_instance.find_groups(name=SECRETS_STORE_GROUP, first=True)

    def __set_environment_variables__(self):
        for entry in self.__store_group__().entries:
            if entry.username == SECRETS_ENV_TAG:
                os.environ[entry.title] = entry.password

    def add_secret(self, name: str, secret: str, init_env: bool = False):
        if self.get_entry(name):
            self.delete_entry(name)

        if init_env:
            self.keepass_instance.add_entry(self.__store_group__(), name, SECRETS_ENV_TAG, secret)
        else:
            self.keepass_instance.add_entry(self.__store_group__(), name, '-', secret)

        self.save()

    def create_secret(self, name: str, init_env: bool = False, length: int = 10) -> str:
        lower = string.ascii_lowercase
        upper = string.ascii_uppercase
        numbers = string.digits
        symbols = string.punctuation

        secret = random.sample(lower + upper + numbers + symbols, length)
        secret = "".join(secret)

        self.add_secret(name=name, secret=secret, init_env=init_env)
        return secret

    def delete_entry(self, name):
        entry = self.keepass_instance.find_entries(title=name, group=self.__store_group__(), first=True)
        entry.delete()
        self.save()

    def get_entry(self, name: str):
        entry = self.keepass_instance.find_entries(title=name, group=self.__store_group__(), first=True)
        return entry

    def get_secret(self, name: str) -> str:
        entry = self.get_entry(name)
        if entry is None:
            raise SecretsStoreException(f'Secret {name} does not exists in store.')

        return entry.password

    def save(self):
        self.keepass_instance.save()

    def close(self):
        self.save()


secret_store: SecretsStore = None


def get_secret_store(password=None):
    global secret_store

    if secret_store is None:
        if password is None:
            secret_store = SecretsStore()
        else:
            secret_store = SecretsStore(password)

    return secret_store


def initialise_new_secrets_store(password: str = os.getenv('SECRETS_STORE_PASSWORD', None)):
    if password is None:
        raise SecretsStoreException('No password was provided for new Secrets Store.  '
                                    'Password must be provided or environment variable SECRETS_STORE_PASSWORD set.')

    if os.path.exists(SECRETS_STORE_PATH):
        raise SecretsStoreException(f'A Secrets Store already exists at: {SECRETS_STORE_PATH}.')

    try:
        logging.info(f'Creating Secrets Store at: {SECRETS_STORE_PATH}')
        copyfile(SECRETS_TEMPLATE, SECRETS_STORE_PATH)

        keepass_instance = PyKeePass(SECRETS_STORE_PATH, DEFAULT_PASSWORD)
        keepass_instance.password = password
        keepass_instance.add_group(keepass_instance.root_group, SECRETS_STORE_GROUP)
        keepass_instance.save()
        logging.info(f'Successfully created Secrets Store.')
    except Exception as ex:
        logging.error(f'Failed to create Secrets Store.  Error: {str(ex)}')
        raise ex


# -----------------------------------------------------------------------------
# Main entry points
# -----------------------------------------------------------------------------

def main_init_secrets_store():
    logger.init(app_name='digital-thought-secrets-store')
    with open("{}/../version".format(str(pathlib.Path(__file__).parent.absolute())), "r") as fh:
        version_info = fh.read()

    arg_parser = argparse.ArgumentParser(prog='init_store',
                                         description='Initialise new Secrets Store')
    arg_parser.add_argument('--password', action='store', type=str, required=False,
                            help="Password to assign to Secrets Store")

    args = arg_parser.parse_args()
    logging.info(f"Secrets Store, version: {version_info}")

    if args.password:
        initialise_new_secrets_store(password=args.password)
    else:
        initialise_new_secrets_store()

    print(f'Successfully initialised new Secrets Store.')


def main_add_secret():
    logger.init(app_name='digital-thought-secrets-store')
    with open("{}/../version".format(str(pathlib.Path(__file__).parent.absolute())), "r") as fh:
        version_info = fh.read()

    arg_parser = argparse.ArgumentParser(prog='add_secret',
                                         description='Add entry to Secrets Store')
    arg_parser.add_argument('--password', action='store', type=str, required=False,
                            help="Secrets Store password")
    arg_parser.add_argument('--name', action='store', type=str, required=True, help="Secret Name")
    arg_parser.add_argument('--value', action='store', type=str, required=True, help="Secret Value")
    arg_parser.add_argument('--env', action='store_true',
                            help="Load secret as environment variable on Secrets Store initialisation")
    arg_parser.set_defaults(env=False)

    args = arg_parser.parse_args()
    logging.info(f"Secrets Store, version: {version_info}")

    try:
        if args.password:
            store = get_secret_store(password=args.password)
        else:
            store = get_secret_store()

        store.add_secret(args.name, args.value, args.env)
        store.close()
    except Exception as ex:
        logging.error(f'Error occurred while adding secret {args.name}.  Error: {str(ex)}')
        raise ex

    logging.info(f'Successfully added secret {args.name}')
    print(f'Successfully added secret {args.name}')
