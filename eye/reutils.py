# this project is licensed under the WTFPLv2, see COPYING.txt for details

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


def glob2re(globstr, can_escape=False, explicit_slash=True, explicit_dot=True,
            exact=False):
	# fnmatch.translate uses python-specific syntax
	dot = '[^/]' if explicit_slash else '.'
	first_dot = '[^/.]' if explicit_slash else '[^.]'

	def is_first_component(mtc):
		return (mtc.start() == 0
		     or mtc.string[mtc.start() - 1] == '/')

	def replace(mtc):
		s = mtc.group(0)
		if s == '?':
			return first_dot if is_first_component(mtc) else dot
		elif s == '*':
			p = first_dot if is_first_component(mtc) else dot
			return p + '*'
		elif s.startswith('['):
			return s
		elif can_escape and s == '\\\\':
			return s
		elif can_escape and s.startswith('\\'):
			return s
		elif s in '()[]{}.^$+\\':
			return r'\%s' % s
		else:
			return s

	if can_escape:
		r = re.sub(r'\?|\*|\[[^]]*\]|\\\\|\\.|.', replace, globstr)
	else:
		r = re.sub(r'\?|\*|\[[^]]*\]|.', replace, globstr)
	if exact:
		r = '^%s$' % r
	return r


def qreToPattern(qre):
	s = qre.pattern()

	if qre.patternSyntax() == qre.FixedString:
		return qre.escape(s)
	elif qre.patternSyntax() in (qre.RegExp, qre.RegExp2):
		return s
	elif qre.patternSyntax() == qre.Wildcard:
		return glob2re(s)
	elif qre.patternSyntax() == qre.WildcardUnix:
		return glob2re(can_escape=True)
	raise NotImplementedError()
