# this project is licensed under the WTFPLv2, see COPYING.txt for details

import glob
import os
import re


__all__ = ('parseFilename', 'findAncestorContaining', 'findInAncestors',
           'getCommonPrefix', 'getConfigPath')


def parseFilename(filepath):
	row, col = None, None

	mtc = re.search(r'(:\d+)?(:\d+)?$', filepath)
	if mtc.group(1):
		row = int(mtc.group(1)[1:])
	if mtc.group(2):
		col = int(mtc.group(2)[1:])
	filepath = filepath[:mtc.start()]

	return (filepath, row, col)



def findAncestorContaining(path, patterns):
	found = findFileInAncestors(path, patterns)
	if found:
		return os.path.dirname(found)


def findInAncestors(path, patterns):
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
	r = getRelativePathIn(a, b)
	return r is None


def getRelativePathIn(a, b):
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
		return os.path.join(os.path.expanduser('~/.config/eyeditor'), *args)
