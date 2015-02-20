
import os
import app
import contextlib
import tempfile

@contextlib.contextmanager
def exceptionLogging():
	try:
		yield
	except BaseException, e:
		app.qApp().logger.exception(e)
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
