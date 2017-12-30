# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for use with Qt"""

import inspect
import os
import re

from PyQt5.QtCore import pyqtSlot, pyqtSignal

from . import _addDoc


__all__ = ('Slot', 'Signal')


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
				signatures.append(mtc.group(1))
			elif srcline.startswith('def '):
				break

		text = '\n\n'.join('This slot has signature ``%s%s``.' % (func.__name__, sig)
		                   for sig in signatures)
		_addDoc(func, text)

		return func

	return decorator


class SignalDoc(object):
	def __init__(self, *types):
		self.types = types

	def _typeString(self, t):
		if isinstance(t, type):
			return t.__name__
		return repr(t)

	def __repr__(self):
		if not self.types or isinstance(self.types[0], type):
			return 'Signal(%s)' % ', '.join(self._typeString(t) for t in self.types)
		return ' '.join(repr(SignalDoc(*arg)) for arg in self.types)

	def connect(self, *args, **kwargs):
		pass


def Signal(*args, **kwargs):
	if os.environ.get('READTHEDOCS') != 'True':
		return pyqtSignal(*args, **kwargs)
	return SignalDoc(*args, **kwargs)
