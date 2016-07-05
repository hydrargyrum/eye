# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Regular expression utilities
"""

from PyQt5.QtCore import Qt
import re
import unittest


__all__ = ('csToQtEnum', 'qtEnumToCs', 'qreToPattern', 'glob2re')


def csToQtEnum(cs):
	"""Return a `Qt.CaseSensitivity` flag for bool `cs`"""
	if cs:
		return Qt.CaseSensitive
	else:
		return Qt.CaseInsensitive

def qtEnumToCs(enum):
	"""Return True if `enum` value equals `Qt.CaseSensitive`"""
	return enum == Qt.CaseSensitive


DOTSLASH_GENERIC = 0
DOTSLASH_NO_SLASH = 1
DOTSLASH_NO_SLASH_AND_HIDDEN = 2

def glob2re(globstr, can_escape=False, dotslash=DOTSLASH_NO_SLASH_AND_HIDDEN,
            exact=False, double_star=False, sets=False):
	"""Convert a globbing pattern to a Python regex pattern

	:param globstr: the glob pattern to convert
	:param exact:  if True, the pattern will match the start and end of string (``^`` and ``$`` are added)
	:param double_star: if True, "**" is interpreted to match a indefinite number of path components
	:param sets: if True, "{foo,bar}" will match "foo" or "bar"
	:param can_escape: if True, backslashes can be used to escape other metacharacters,
	                   else it will be literal
	"""
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
		elif sets and s.startswith('{') and s.endswith('}'):
			parts = [re.escape(p) for p in s[1:-1].split(',')]
			return '(?:%s)' % '|'.join(parts)
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
	if sets:
		reparts.append(r'\{[^}]*\}')

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


class ReTests(unittest.TestCase):
	def check_pattern(self, glob, matches, non_matches, **options):
		pattern = glob2re(glob, exact=True, **options)
		r = re.compile(pattern)
		for i in matches:
			msg = '%s should match %s (%s) %r' % (glob, i, pattern, options)
			self.assertIsNotNone(r.match(i), msg)
		for i in non_matches:
			msg = '%s should not match %s (%s) %r' % (glob, i, pattern, options)
			self.assertIsNone(r.match(i), msg)

	def test_glob2re_generic(self):
		options = dict(dotslash=0)
		self.check_pattern(
			'*',
			'foo .foo foo/bar foo.bar [] *'.split(),
			[],
			**options)
		self.check_pattern(
			'*/*',
			'foo/bar foo/.bar foo/foo/bar foo/bar.baz foo/*'.split(),
			'foo.bar foo'.split(),
			**options)
		self.check_pattern(
			'foo*',
			'foo foobar foo.bar foo/bar foobar/'.split(),
			'bar barfoo .foo '.split(),
			**options)
		self.check_pattern(
			'*bar',
			'bar .bar foobar foo.bar foo/bar .foobar'.split(),
			'barfoo'.split(),
			**options)
		self.check_pattern(
			'*bar*',
			'bar .bar foobar foo/bar barbaz foobarbaz foo.bar bar.baz'.split(),
			[],
			**options)
		self.check_pattern(
			'???',
			'foo .fo fo/ f/o /fo'.split(),
			'foobar'.split(),
			**options)
		self.check_pattern(
			'?/?',
			'f/b f/. ./b'.split(),
			'foo'.split(),
			**options)

	def test_glob2re_filename(self):
		self.check_pattern(
			'*',
			'foo foo.bar [] *'.split(),
			'.foo foo/bar'.split())
		self.check_pattern(
			'*/*',
			'foo/bar foo/bar.baz foo/*'.split(),
			'foo/.bar foo.bar foo/foo/bar foo'.split())
		self.check_pattern(
			'foo*',
			'foo foobar foo.bar'.split(),
			'bar barfoo .foo foo/bar foobar/'.split())
		self.check_pattern(
			'*bar',
			'bar foobar foo.bar'.split(),
			'barfoo .bar .foobar foo/bar'.split())
		self.check_pattern(
			'*bar*',
			'bar foobar barbaz foobarbaz foo.bar bar.baz'.split(),
			'.bar foo/bar'.split())
		self.check_pattern(
			'???',
			'foo'.split(),
			'.fo fo/ f/o /fo foobar'.split())
		self.check_pattern(
			'?/?',
			'f/b'.split(),
			'foo f/. ./b'.split())

	def test_glob2re_recursive(self):
		options = dict(double_star=True)
		self.check_pattern(
			'**/*',
			'foo foo/foo foo/foo/bar'.split(),
			'.foo foo/.foo'.split(),
			**options)
		self.check_pattern(
			'**/foo',
			'foo foo/foo'.split(),
			'.foo foo/.foo foo/foo/bar bar'.split(),
			**options)
		self.check_pattern(
			'foo/**/bar',
			'foo/bar foo/baz/bar foo/baz/baz/bar'.split(),
			'.foo foo/.bar bar baz/bar foo/baz'.split(),
			**options)
		self.check_pattern(
			'foo/**',
			'foo foo/bar foo/baz/bar foo/.bar'.split(),
			'.foo bar baz/bar'.split(),
			**options)

	def test_glob2re_escapable(self):
		options = dict(can_escape=True)
		self.check_pattern(
			r'\*',
			r'\*'.split(),
			r'foo *'.split())
		self.check_pattern(
			r'\*',
			r'*'.split(),
			r'\* foo ?'.split(),
			**options)

		self.check_pattern(
			r'\?',
			'?'.split(),
			r'* f \?'.split(),
			**options)
		self.check_pattern(
			r'\[a\]',
			'[a]'.split(),
			'a [] ['.split(),
			**options)

		self.check_pattern(
			r'foo\\bar',
			r'foo\\bar'.split(),
			r'foobar foo\bar'.split())
		self.check_pattern(
			r'foo\\bar',
			r'foo\bar'.split(),
			r'foo\\bar foobar'.split(),
			**options)

		self.check_pattern(
			'\{foo\}',
			'{foo}'.split(),
			'foo'.split(),
			sets=True, **options)

	def test_glob2re_charset(self):
		options = dict()
		self.check_pattern(
			'[ac]b[d-l]',
			'abd cbl abe cbh'.split(),
			'dbd bbd cbt abdx a'.split())
		self.check_pattern(
			'[ac-eh-k]',
			'a c d e h i j k'.split(),
			'* b f g l o z [ [ac-eh-k] aa'.split(),
			**options)
		self.check_pattern(
			'[!a-et]',
			'f x *'.split(),
			'a e c t xx'.split(),
			**options)
		self.check_pattern(
			'[a-m]*',
			'a bn m moooooo'.split(),
			'x xa *'.split(),
			**options)
		self.check_pattern(
			'[',
			'['.split(),
			'x xa * ]'.split(),
			**options)
		self.check_pattern(
			']',
			']'.split(),
			'x xa * ['.split(),
			**options)
		self.check_pattern(
			'[]',
			[],
			'x xa *'.split(),
			**options)
		self.check_pattern(
			'[!]',
			'x ] ! [ *'.split(),
			'xa [!]'.split(),
			**options)

	def test_glob2re_sets(self):
		options = dict(sets=True)
		self.check_pattern(
			'{foo}',
			'{foo}'.split(),
			'foo bar {bar}'.split())
		self.check_pattern(
			'{foo}',
			'foo'.split(),
			'{foo} bar {bar}'.split(),
			**options)
		self.check_pattern(
			'{foo,bar}',
			'foo bar'.split(),
			'{foo} {bar}'.split(),
			**options)
		self.check_pattern(
			'{f{oo,bar}',
			'f{oo bar'.split(),
			'{foo} {bar} {f{oo,bar} foo'.split(),
			**options)
		self.check_pattern(
			'{{foo}}', # ({foo)}
			'{foo}'.split(),
			'foo {foo foo} {bar}'.split(),
			**options)


if __name__ == '__main__':
	unittest.main()
