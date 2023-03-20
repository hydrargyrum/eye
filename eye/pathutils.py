# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Path manipulation utilities
"""

import glob
import os
import re

__all__ = (
	'vim_filename_arg', 'parse_filename',
	'find_ancestor_containing', 'find_in_ancestors',
	'get_common_prefix', 'get_relative_path_in', 'is_in',
	'get_config_path', 'get_config_file_path', 'data_path',
)


_VIM_JUMP = re.compile(r"\+\d+")


def vim_filename_arg(args):
	"""Parse `+line filename` args

	Vim and other editors are sometimes called with a filename and a line argument.
	Returns (filename, lineno)
	"""

	if len(args) != 2 or not _VIM_JUMP.fullmatch(args[0]):
		return

	path = args[1]
	try:
		row = int(args[0][1:])
	except ValueError:
		return
	return path, row


def parse_filename(filepath):
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


def find_ancestor_containing(path, patterns):
	"""Find an ancestor containing any of `patterns`

	Like :any:`find_in_ancestors`, but returns the directory containing the
	matched file.
	"""
	found = find_in_ancestors(path, patterns)
	if found:
		return os.path.dirname(found)


def find_in_ancestors(path, patterns):
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


def get_common_prefix(a, b):
	"""Return common path prefix between path `a` and path `b`

	Paths are normalized with `os.path.normpath`. Will not cut in the middle
	of a path component.

		>>> get_common_prefix('/foo/bar', '/foo/baz')
		'/foo'
	"""
	aparts, bparts = (os.path.normpath(x).split(os.path.sep) for x in (a, b))

	n = 0
	for aelem, belem in zip(aparts, bparts):
		if aelem != belem:
			break
		n += 1
	return os.path.sep.join(aparts[:n]) or os.path.sep


def is_in(a, b):
	"""Return True if path `a` is contained path `b`

	Does not check existence of paths. Paths are normalized with
	`os.path.normpath`.

		>>> is_in('/foo, '/bar')
		False
		>>> is_in('/bar/foo', '/bar')
		True
	"""
	r = get_relative_path_in(a, b)
	return r is not None


def get_relative_path_in(a, b):
	"""Return the relative path of `a` inside `b`

	If `a` is not contained inside `b`, returns `None`.

	Paths are normalized with `os.path.normpath`. Does not check existence
	of paths.

		>>> get_relative_path_in('/bar/foo/qux', '/bar')
		'foo/qux'
		>>> get_relative_path_in('/foo', '/bar') is None
		True
	"""
	aparts, bparts = (os.path.normpath(x).split(os.path.sep) for x in (a, b))

	if len(aparts) < len(bparts):
		return
	for n, bpart in enumerate(bparts):
		if aparts[n] != bpart:
			return
	return '/'.join(aparts[n + 1:])


def get_config_path(*args):
	try:
		import xdg.BaseDirectory
		return xdg.BaseDirectory.save_config_path('eyeditor', *args)
	except ImportError:
		path = os.path.join(os.path.expanduser('~/.config/eyeditor'), *args)
		if not os.path.isdir(path):
			os.makedirs(os.path.normpath(path))
		return path


def get_config_file_path(*args):
	subpath = os.path.join(*args)
	dir = get_config_path(os.path.dirname(subpath))
	file = os.path.basename(subpath)
	return os.path.join(dir, file)


def data_path(*args):
	dest = os.path.join(os.path.dirname(__file__), '..', 'data', *args)
	if os.path.exists(dest):
		return os.path.abspath(dest)

	try:
		import xdg.BaseDirectory
		for path in xdg.BaseDirectory.load_data_paths('eye', *args):
			return path
	except ImportError:
		pass
	return os.path.join('/usr/share/eye', *args)
