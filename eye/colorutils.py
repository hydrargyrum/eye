
from PyQt4.QtGui import QColor

__all__ = ('QColorAlpha',)

def QColorAlpha(*args):
	if len(args) == 2:
		qc = QColor(args[0])
		qc.setAlpha(args[1])
		return qc
	elif len(args) >= 3:
		return QColor(*args)
	elif isinstance(args[0], str) and args[0].startswith('#'):
		qc = QColor(args[0][:7])
		qc.setAlpha(int(args[0][7:], 16))
		return qc
