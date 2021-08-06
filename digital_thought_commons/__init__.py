from . import *
import pathlib

with open("{}/version".format(str(pathlib.Path(__file__).parent.absolute())), "r") as fh:
    version_info = fh.read()

__version__ = version_info
