
from contextlib import contextmanager
from PyQt4.QtGui import QApplication

__all__ = ('exceptionLogging',)

@contextmanager
def exceptionLogging(reraise=True, logger=None):
	try:
		yield
	except BaseException, e:
		# could guess logger by inspecting traceback
		if logger is None:
			logger = QApplication.instance().logger
		logger.exception(e)
		if reraise:
			raise
