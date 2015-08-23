
import glob
import os
import re


__all__ = ('parseFilename', 'getParentContaining')


def parseFilename(filepath):
	row, col = None, None

	mtc = re.search(r'(:\d+)?(:\d+)?$', filepath)
	if mtc.group(1):
		row = int(mtc.group(1)[1:])
	if mtc.group(2):
		col = int(mtc.group(2)[1:])
	filepath = filepath[:mtc.start()]

	return (filepath, row, col)


def getParentContaining(path, patterns):
	path = os.path.abspath(path)

	while True:
		for pattern in patterns:
			matches = glob.glob(os.path.join(path, pattern))
			if matches:
				return path

		if path == '/':
			return
		path = os.path.dirname(path)
