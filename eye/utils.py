# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
import logging
from PyQt4.QtGui import QApplication

__all__ = ('exceptionLogging',)

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
