# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
from functools import wraps
import logging
from PyQt5.QtWidgets import QApplication

__all__ = ('exceptionLogging', 'ignoreExceptions')

@contextmanager
def exceptionLogging(reraise=True, logger=None, level=logging.ERROR):
	"""Context manager to log exceptions

	.. py:function:: exceptionLogging(reraise=True, logger=None, level=logging.ERROR)

	Within this context, if an exception is raised and not caught, the exception is logged, and the exception continues
	upper in the stack frames.

	:param reraise: if False, uncaught exceptions will be intercepted and not be raised to upper frames (but the code in
	            this context is still interrupted and aborted)
	:param logger: logger where to log the exceptions. If None, the root logger is used
	:param level: level with which to log the exceptions

	Example of exception interception::

		try:
			with exceptionLogging():
				raise RuntimeError('Unexpected error')
		except Exception as e:
			pass

		# is equivalent to

		with exceptionLogging(reraise=False):
			raise RuntimeError('Unexpected error')
	"""
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
				real_logger = logger
				if real_logger is None:
					real_logger = QApplication.instance().logger
				real_logger.log(level, 'an exception occured when calling %r', f, exc_info=True)
				return return_value

		return decorator

	return caller
