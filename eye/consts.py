# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for various constants"""

import os

from PyQt5.QtCore import Qt

__all__ = ('register_role',
           'UP', 'DOWN', 'LEFT', 'RIGHT')


if os.environ.get('READTHEDOCS') == 'True':
	LAST_ROLE = 256
else:
	LAST_ROLE = Qt.UserRole


def register_role():
	"""Register and return a new Qt data role

	The value starts at `Qt.UserRole` and is incremented at each call.
	"""

	global LAST_ROLE

	LAST_ROLE += 1
	return LAST_ROLE


UP = 0

"""Up direction"""

DOWN = 1

"""Down direction"""

LEFT = 2

"""Left direction"""

RIGHT = 3

"""Right direction"""

ORIENTATIONS = {
	UP: Qt.Vertical,
	DOWN: Qt.Vertical,
	LEFT: Qt.Horizontal,
	RIGHT: Qt.Horizontal
}

MOVES = {
	UP: -1,
	DOWN: 1,
	LEFT: -1,
	RIGHT: 1
}


AbsolutePathRole = register_role()

"""Role for absolute path data.

Used in location lists, file choosers, etc.
"""
