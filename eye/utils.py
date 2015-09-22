# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
from functools import wraps
import logging
from PyQt4.QtGui import QApplication

__all__ = ('exceptionLogging', 'ignoreExceptions')

@contextmanager
def exceptionLogging(reraise=True, logger=None, level=logging.ERROR):
	try:
		yield
	except Exception:
		# could guess logger by inspecting traceback
		if logger is None:
			logger = QApplication.instance().logger
		logger.log(level, 'an exception occured', exc_info=True)
		if reraise:
			raise


def ignoreExceptions(return_value, logger=None, level=logging.ERROR):
	def caller(f):
		@wraps(f)
		def decorator(*a, **kw):
			try:
				return f(*a, **kw)
			except Exception:
				if logger is None:
					logger = QApplication.instance().logger
				logger.log(level, 'an exception occured when calling %r', f, exc_info=True)
				return return_value

		return decorator

	return caller
