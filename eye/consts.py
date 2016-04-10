
from PyQt5.QtCore import Qt

__all__ = ('registerRole',)

LAST_ROLE = Qt.UserRole

def registerRole():
	global LAST_ROLE

	LAST_ROLE += 1
	return LAST_ROLE

