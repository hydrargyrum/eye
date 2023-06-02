# this project is licensed under the WTFPLv2, see COPYING.txt for details

from logging import getLogger
import os
import tempfile

from eye.utils import exception_logging

__all__ = ('write_bytes_to_file', 'read_bytes_from_file')

LOGGER = getLogger(__name__)


def write_bytes_to_file_direct(filepath: str, data: bytes) -> bool:
	with exception_logging(logger=LOGGER):
		with open(filepath, 'wb') as f:
			f.write(data)
			return True


def get_perm(path: str) -> tuple[int, int, int] | None:
	try:
		stat = os.stat(path)
	except OSError:
		LOGGER.warning('could not stat file %r', path, exc_info=True)
		return None
	return stat.st_mode, stat.st_uid, stat.st_gid


def set_perm(path: str, perm: tuple[int, int, int] | None):
	if perm is None:
		return

	os.chmod(path, perm[0])
	os.chown(path, perm[1], perm[2])


def write_bytes_to_file(filepath: str, data: bytes) -> bool:
	if os.name == 'nt':
		return write_bytes_to_file_direct(filepath, data)

	# TODO if file is created by another user, the owner info may be lost or chown may fail
	# TODO write directly in those cases?
	if os.path.exists(filepath):
		oldperm = get_perm(filepath)
	else:
		oldperm = None

	dir = os.path.dirname(filepath)
	with exception_logging(logger=LOGGER):
		fd, tmpfile = tempfile.mkstemp(dir=dir)
		os.close(fd)
		set_perm(tmpfile, oldperm)
		with open(tmpfile, 'wb') as f:
			f.write(data)
		os.rename(tmpfile, filepath)
		return True


def read_bytes_from_file(filepath: str) -> bytes:
	with exception_logging(logger=LOGGER):
		with open(filepath, 'rb') as f:
			return f.read()
