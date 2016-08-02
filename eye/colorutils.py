# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Utils for colors"""

from __future__ import unicode_literals

import unittest

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from .three import bytes, str

__all__ = ('QColorAlpha', 'QColor')

def QColorAlpha(*args):
	"""Build a QColor with alpha in one call

	This function allows to create a `QColor` and set its alpha channel value in a single call.

	If one argument is provided and it is a string parsable as hex, it is parsed as `#RRGGBBAA`.
	Else, the single argument is passed to QColor and thus alpha is 255.
	Examples::

		QColorAlpha(Qt.red) # equivalent to QColor(Qt.red)
		QColorAlpha('#ff0000') # same as previous
		QColorAlpha('#ff00007f') # semi-transparent red

	If two arguments are passed, the first is passed to QColor and the second is the alpha channel (`int` from 0 to 255)::

		QColorAlpha(Qt.red, 127) # semi-transparent red

	If there are more arguments, they are passed to `QColor`::

		QColorAlpha(255, 0, 0) # opaque red
		QColorAlpha(255, 0, 0, 127) # semi-transparent red
	"""
	if len(args) == 1:
		if isinstance(args[0], (bytes, str)):
			s = args[0]
			if s.startswith('#') and len(s) == 9: #RRGGBBAA
				qc = QColor(s[:7])
				qc.setAlpha(int(s[7:], 16))
				return qc
			else: # #RRGGBB, "red"
				return QColor(s)
		return QColor(args[0]) # Qt.red
	elif len(args) == 2: # (Qt.red, alpha)
		qc = QColor(args[0])
		qc.setAlpha(args[1])
		return qc
	elif len(args) >= 3: # (r, g, b)
		return QColor(*args)


QColor.__repr__ = lambda self: '<QColor %r>' % self.name(QColor.HexArgb)


class ColorTests(unittest.TestCase):
	def test_normal(self):
		self.assertEqual(QColorAlpha(Qt.red), QColor(Qt.red))
		self.assertEqual(QColorAlpha('#123456'), QColor('#123456'))
		self.assertEqual(QColorAlpha(1, 2, 3), QColor(1, 2, 3))

	def test_alpha(self):
		c = QColor(Qt.red)
		c.setAlpha(128)
		self.assertEqual(QColorAlpha(Qt.red, 128), c)
		self.assertEqual(QColorAlpha('#ff0000', 128), c)
		self.assertEqual(QColorAlpha('#ff000080'), c)
		self.assertEqual(QColorAlpha(255, 0, 0, 128), c)


if __name__ == '__main__':
	unittest.main()
