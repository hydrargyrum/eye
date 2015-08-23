
from contextlib import contextmanager
from PyQt4.QtGui import QApplication

__all__ = ('exceptionLogging',)

@contextmanager
def exceptionLogging(reraise=True):
	try:
		yield
	except BaseException, e:
		QApplication.instance().logger.exception(e)
		if reraise:
			raise
