# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os
import tempfile
from logging import getLogger

from .utils import exceptionLogging


__all__ = ('writeBytesToFile', 'readBytesFromFile')

LOGGER = getLogger(__name__)


def writeBytesToFileDirect(filepath, data):
	with exceptionLogging(logger=LOGGER):
		with open(filepath, 'wb') as f:
			f.write(data)
			return True


def writeBytesToFile(filepath, data):
	if os.name == 'nt':
		return writeBytesToFileDirect(filepath, data)

	dir = os.path.dirname(filepath)
	with exceptionLogging(logger=LOGGER):
		fd, tmpfile = tempfile.mkstemp(dir=dir)
		os.close(fd)
		with open(tmpfile, 'wb') as f:
			f.write(data)
		os.rename(tmpfile, filepath)
		return True


def readBytesFromFile(filepath):
	with exceptionLogging(logger=LOGGER):
		with open(filepath, 'rb') as f:
			return f.read()
