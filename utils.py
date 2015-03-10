
import os
import app
import contextlib
import tempfile
import re

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
