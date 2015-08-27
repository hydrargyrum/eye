
from PyQt4.QtGui import QColor

__all__ = ('QColorAlpha', 'QColor')

def QColorAlpha(*args):
	if len(args) == 1 and isinstance(args[0], (str, unicode)):
		s = args[0]
		if s.startswith('#') and len(s) == 9: #RRGGBBAA
			qc = QColor(s[:7])
			qc.setAlpha(int(s[7:], 16))
		else:
			qc = QColor(s)
		return qc
	elif len(args) == 2:
		qc = QColor(args[0])
		qc.setAlpha(args[1])
		return qc
	elif len(args) >= 3:
		return QColor(*args)
