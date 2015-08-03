
import os
import contextlib
import tempfile
import re

from PyQt4.QtGui import QApplication, QColor

__all__ = ('exceptionLogging', 'parseFilename', 'PropDict', 'QColorAlpha')

@contextlib.contextmanager
def exceptionLogging(reraise=True):
	try:
		yield
	except BaseException, e:
		QApplication.instance().logger.exception(e)
		if reraise:
			raise

def parseFilename(filepath):
	row, col = None, None

	mtc = re.search(r'(:\d+)?(:\d+)?$', filepath)
	if mtc.group(1):
		row = int(mtc.group(1)[1:])
	if mtc.group(2):
		col = int(mtc.group(2)[1:])
	filepath = filepath[:mtc.start()]

	return (filepath, row, col)


def QColorAlpha(*args):
	if len(args) == 2:
		qc = QColor(args[0])
		qc.setAlpha(args[1])
		return qc
	elif len(args) >= 3:
		return QColor(*args)
	elif isinstance(args[0], str) and args[0].startswith('#'):
		qc = QColor(args[0][:7])
		qc.setAlpha(int(args[0][7:], 16))
		return qc


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
