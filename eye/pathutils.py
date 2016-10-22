# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Path manipulation utilities
"""

import glob
import os
import re


__all__ = ('parseFilename', 'findAncestorContaining', 'findInAncestors',
           'getCommonPrefix', 'getRelativePathIn', 'isIn',
           'getConfigPath', 'getConfigFilePath', 'dataPath')


def parseFilename(filepath):
	"""Parse a `filename:line:col` string

	Parse a string containing a file path, a line number and column number, in
	the format `filepath:line:col`. Line and column are optional. If only one
	is present, it's taken as the line number. Returns a tuple

	This function can be useful for command-line arguments.

		>>> parseFilename('/foo/bar:1')
		('/foo/bar', 1, None)
	"""
	row, col = None, None

	mtc = re.search(r'(:\d+)?(:\d+)?$', filepath)
	if mtc.group(1):
		row = int(mtc.group(1)[1:])
	if mtc.group(2):
		col = int(mtc.group(2)[1:])
	filepath = filepath[:mtc.start()]

	return (filepath, row, col)


def findAncestorContaining(path, patterns):
	"""Find an ancestor containing any of `patterns`

	Like :any:`findInAncestors`, but returns the directory containing the
	matched file.
	"""
	found = findInAncestors(path, patterns)
	if found:
		return os.path.dirname(found)


def findInAncestors(path, patterns):
	"""Find file matching any of `patterns` in ancestors of `path`

	`patterns` should be a list of globbing patterns (see standard `glob`
	module).
	Returns the absolute path of the first matching file. Patterns are
	searched in order given. `path` is searched first, then its parent, then
	ancestors in ascending order.
	"""
	path = os.path.abspath(path)

	while True:
		for pattern in patterns:
			matches = glob.glob(os.path.join(path, pattern))
			if matches:
				return matches[0]

		if path == '/':
			return
		path = os.path.dirname(path)


def getCommonPrefix(a, b):
	"""Return common path prefix between path `a` and path `b`

	Paths are normalized with `os.path.normpath`. Will not cut in the middle
	of a path component.

		>>> getCommonPrefix('/foo/bar', '/foo/baz')
		'/foo'
	"""
	a, b = map(os.path.normpath, (a, b))
	aparts = a.split(os.path.sep)
	bparts = b.split(os.path.sep)

	n = 0
	for aelem, belem in zip(aparts, bparts):
		if aelem != belem:
			break
		n += 1
	return os.path.sep.join(aparts[:n]) or os.path.sep


def isIn(a, b):
	"""Return True if path `a` is contained path `b`

	Does not check existence of paths. Paths are normalized with
	`os.path.normpath`.

		>>> isIn('/foo, '/bar')
		False
		>>> isIn('/bar/foo', '/bar')
		True
	"""
	r = getRelativePathIn(a, b)
	return r is not None


def getRelativePathIn(a, b):
	"""Return the relative path of `a` inside `b`

	If `a` is not contained inside `b`, returns `None`.

	Paths are normalized with `os.path.normpath`. Does not check existence
	of paths.

		>>> getRelativePathIn('/bar/foo/qux', '/bar')
		'foo/qux'
		>>> getRelativePathIn('/foo', '/bar') is None
		True
	"""
	a, b = map(os.path.normpath, (a, b))
	aparts = a.split(os.path.sep)
	bparts = b.split(os.path.sep)

	if len(aparts) < len(bparts):
		return
	for n, bpart in enumerate(bparts):
		if aparts[n] != bpart:
			return
	return '/'.join(aparts[n + 1:])


def getConfigPath(*args):
	try:
		import xdg.BaseDirectory
		return xdg.BaseDirectory.save_config_path('eyeditor', *args)
	except ImportError:
		path = os.path.join(os.path.expanduser('~/.config/eyeditor'), *args)
		os.makedirs(os.path.normpath(path))
		return path


def getConfigFilePath(*args):
	subpath = os.path.join(*args)
	dir = getConfigPath(os.path.dirname(subpath))
	file = os.path.basename(subpath)
	return os.path.join(dir, file)


def dataPath(*args):
	dest = os.path.join(os.path.dirname(__file__), '..', 'data', *args)
	if os.path.exists(dest):
		return os.path.abspath(dest)

	try:
		import xdg.BaseDirectory
		for path in xdg.BaseDirectory.load_data_paths(*args):
			return path
	except ImportError:
		pass
	return os.path.join('/usr/share', *args)
