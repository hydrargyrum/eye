# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for use with Qt"""

from PyQt5.QtCore import pyqtSlot

import inspect
import os
import re


__all__ = ('Slot',)


SLOT_RE = re.compile(r'@(?:\w\.)*Slot(\(.*\))')


def Slot(*args, **kwargs):
	def decorator(func):
		if os.environ.get('READTHEDOCS') != 'True':
			func = pyqtSlot(*args, **kwargs)(func)

		signatures = []

		for srcline in inspect.getsourcelines(func)[0]:
			srcline = srcline.strip()

			mtc = SLOT_RE.match(srcline)
			if mtc:
				signatures.append('@Slot%s' % mtc.group(1))
			elif srcline.startswith('def '):
				break

		text = '\n\n'.join(signatures)

		if func.__doc__ is None:
			func.__doc__ = text
		else:
			func.__doc__ += '\n\n' + text

		return func

	return decorator
