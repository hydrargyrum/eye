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


def getPerm(path):
	try:
		stat = os.stat(path)
	except OSError as e:
		LOGGER.warning('could not stat file %r', path, exc_info=True)
		return
	return stat.st_mode, stat.st_uid, stat.st_gid


def setPerm(path, perm):
	if perm is None:
		return

	os.chmod(path, perm[0])
	os.chown(path, perm[1], perm[2])


def writeBytesToFile(filepath, data):
	if os.name == 'nt':
		return writeBytesToFileDirect(filepath, data)

	# TODO if file is created by another user, the owner info may be lost or chown may fail
	# TODO write directly in those cases?
	if os.path.exists(filepath):
		oldperm = getPerm(filepath)
	else:
		oldperm = None

	dir = os.path.dirname(filepath)
	with exceptionLogging(logger=LOGGER):
		fd, tmpfile = tempfile.mkstemp(dir=dir)
		os.close(fd)
		setPerm(tmpfile, oldperm)
		with open(tmpfile, 'wb') as f:
			f.write(data)
		os.rename(tmpfile, filepath)
		return True


def readBytesFromFile(filepath):
	with exceptionLogging(logger=LOGGER):
		with open(filepath, 'rb') as f:
			return f.read()
