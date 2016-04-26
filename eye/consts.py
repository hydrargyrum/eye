# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt

__all__ = ('registerRole',)


LAST_ROLE = Qt.UserRole

def registerRole():
	global LAST_ROLE

	LAST_ROLE += 1
	return LAST_ROLE


UP, DOWN, LEFT, RIGHT = range(4)

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
