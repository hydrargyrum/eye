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


DOTSLASH_GENERIC = 0
DOTSLASH_NO_SLASH = 1
DOTSLASH_NO_SLASH_AND_HIDDEN = 2

def glob2re(globstr, can_escape=False, dotslash=DOTSLASH_NO_SLASH_AND_HIDDEN,
            exact=False, double_star=False):
	# fnmatch.translate uses python-specific syntax

	if dotslash == 0:
		dot = first_dot = '.'
	elif dotslash == 1:
		dot = first_dot = '[^/]'
	elif dotslash == 2:
		dot = '[^/]'
		first_dot = '[^/.]'

	def is_first_component(mtc):
		return (mtc.start() == 0
		     or mtc.string[mtc.start() - 1] == '/')

	def replace(mtc):
		s = mtc.group(0)
		if s == '?':
			return first_dot if is_first_component(mtc) else dot
		elif s == '*':
			if is_first_component(mtc) and dotslash == 2:
				return '(?:%s%s*)?' % (first_dot, dot)
			else:
				return dot + '*'
		elif s.startswith('[') and s.endswith(']'):
			if s == '[]':
				return '(?:$FAIL^)' # can never match
			elif s == '[!]':
				return dot
			elif s[1] == '!':
				mid = s[2:-1]
				return '[^%s]' % mid
			else:
				return s
		elif can_escape and s == '\\\\':
			return s
		elif can_escape and s.startswith('\\'):
			return s
		elif '**' in s:
			assert double_star
			if s == '**':
				return '.*'
			elif s == '/**/':
				return '/(?:.*/)?'
			elif s == '/**':
				return '(?:/.*)?'
			elif s == '**/':
				return '(?:.*/)?'
			else:
				assert False
		elif s in '()[]{}.^$+\\':
			return r'\%s' % s
		else:
			return s

	reparts = []
	if can_escape:
		reparts.append(r'\\\\|\\.') # warning: headaches
	if double_star:
		reparts.append(r'(?:^|/)\*\*(?:/|$)')

	reparts.append(r'\?|\*|\[[^]]*\]|.')
	r = re.sub('|'.join(reparts), replace, globstr)
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
		return glob2re(s, dotslash=DOTSLASH_GENERIC)
	elif qre.patternSyntax() == qre.WildcardUnix:
		return glob2re(s, dotslash=DOTSLASH_NO_SLASH_AND_HIDDEN,
		               can_escape=True)
	raise NotImplementedError()
