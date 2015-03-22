
import os
import app
import contextlib
import tempfile
import re

__all__ = ('exceptionLogging', 'writeBytesToFile', 'readBytesFromFile',
           'parseFilename', 'PropDict')

@contextlib.contextmanager
def exceptionLogging(reraise=True):
	try:
		yield
	except BaseException, e:
		app.qApp().logger.exception(e)
		if reraise:
			raise

def writeBytesToFileDirect(filepath, data):
	with exceptionLogging():
		with open(filepath, 'wb') as f:
			filepath.write(data)
			return True

def writeBytesToFile(filepath, data):
	if os.name == 'nt':
		return writeBytesToFileDirect(filepath, data)

	dir = os.path.dirname(filepath)
	with exceptionLogging():
		fd, tmpfile = tempfile.mkstemp(dir=dir)
		os.close(fd)
		with open(tmpfile, 'wb') as f:
			f.write(data)
		os.rename(tmpfile, filepath)
		return True

def readBytesFromFile(filepath):
	with exceptionLogging():
		with open(filepath, 'rb') as f:
			return f.read()

def parseFilename(filepath):
	row, col = None, None

	mtc = re.search(r'(:\d+)?(:\d+)?$', filepath)
	if mtc.group(1):
		row = int(mtc.group(1)[1:])
	if mtc.group(2):
		col = int(mtc.group(2)[1:])
	filepath = filepath[:mtc.start()]

	return (filepath, row, col)


class PropDict(dict):
	def __getattr__(self, k):
		try:
			return self[k]
		except KeyError:
			# raised so getattr with a default value works
			raise AttributeError('object has no attribute %r' % k)

	def __setattr__(self, k, v):
		self[k] = v

	def __delattr__(self, k):
		del self[k]
