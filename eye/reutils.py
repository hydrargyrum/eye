
from PyQt4.QtCore import QRegExp, Qt
import re


__all__ = ('csToQtEnum', 'qtEnumToCs', 'qreToPattern')


def csToQtEnum(cs):
	if cs:
		return Qt.CaseSensitive
	else:
		return Qt.CaseInsensitive

def qtEnumToCs(enum):
	return enum == Qt.CaseSensitive


def qreToPattern(qre):
	if qre.patternSyntax() == qre.FixedString:
		return qre.escape(qre.pattern())
	if qre.patternSyntax() in (qre.RegExp, qre.RegExp2):
		return qre.pattern()
	raise NotImplementedError()
	# TODO handle wildcard
	#~ if qre.patternSyntax() == qre.WildcardUnix:
