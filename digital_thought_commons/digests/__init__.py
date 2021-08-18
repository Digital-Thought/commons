import hashlib
import functools

from typing import Any


class Digest(dict):

    MAPPINGS = {
        'name': {},
        'sha512': {
            'hashlib': hashlib.sha512()
        },
        'sha256': {
            'hashlib': hashlib.sha256()
        },
        'sha1': {
            'hashlib': hashlib.sha1()
        },
        'md5': {
            'hashlib': hashlib.md5()
        }
    }

    __values_only__ = False

    def __init__(self) -> None:
        super().__init__()

        for key in self.MAPPINGS:
            self[key]: str = str()

    def update_from_string(self, string: str) -> 'Digest':
        return self.update_from_bytes(string.encode(encoding='utf-8'))

    def update_from_bytes(self, data: bytes) -> 'Digest':
        if not self.__values_only__:
            for key in self.MAPPINGS:
                if key != 'name':
                    self.MAPPINGS[key]['hashlib'].update(data)
                    self[key] = self.MAPPINGS[key]['hashlib'].hexdigest()
            return self
        else:
            raise AttributeError('Digest values are read only and can not be updated')

    def get(self, key, default=None):
        try:
            value = self.__getitem__(key)
            if not value:
                return default
            return value
        except KeyError:
            return default

    def __getter__(self, getter_call: str) -> dict:
        """
        A getter method to handle the dynamic call to get a top level dictionary (e.g. get_md5())
        :param getter_call: the name of the getter call (e.g. get_md5)
        :type getter_call: str
        :return: the top level dictionary (e.g. md5)
        :rtype: dict
        """
        return self[getter_call.replace('get_', '')]

    def __getattr__(self, key):
        try:
            if key.startswith('get_'):
                return functools.partial(self.__getter__, key)
            if key in self.MAPPINGS:
                return super().__getitem__(key)
            raise AttributeError("object has no attribute '%s'" % key)
        except KeyError:
            raise AttributeError("object has no attribute '%s'" % key)

    def __setitem__(self, key, value):
        if key in self.MAPPINGS:
            super().__setitem__(key, value)
        else:
            raise AttributeError("attribute '%s' is not supported" % key)

    def __setattr__(self, name: str, value: Any) -> None:
        self.__setitem__(name, value)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Digest):
            return False
        return o.name == self.name and o.md5 == self.md5 and o.sha256 == self.sha256


def calc_bytes_digest(data: bytes) -> Digest:
    """
    Calculate a Digest from bytes.

    :param data: The bytes to calculate Digest from
    :type data: bytes
    :return: The Digest
    :rtype: Digest
    """
    return Digest().update_from_bytes(data)


def calc_string_digest(string: str) -> Digest:
    """
    Calculate a Digest from a string.

    :param string: The string to calculate Digest from
    :type string: str
    :return: The Digest
    :rtype: Digest
    """
    return calc_bytes_digest(string.encode(encoding='utf-8'))


def calc_file_digest(filename: str) -> Digest:
    """
    Calculate a Digest from a file source.
    Handled large files.

    :param filename: The path to the file to process.
    :type filename: str
    :return: The Digest
    :rtype: Digest
    """
    digest = Digest()
    with open(filename, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            digest.update_from_bytes(byte_block)
    return digest
