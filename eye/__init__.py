import os
import re

__all__ = ()

BUILDING_DOCS = os.environ.get('BUILDING_DOCS') == 'True'


def _addDoc(func, text):
	"""Append `text` to `func` __doc__"""

	if func.__doc__ is None:
		func.__doc__ = text
	else:
		# use the same indent for `text` as for the rest of __doc__
		# (except first line which is generally not indented)
		lines = func.__doc__.split('\n')[1:]
		indent = ''
		for line in lines:
			if line:
				indent = re.match(r'\s*', line).group(0)
				break

		text = '\n'.join(indent + line for line in text.split('\n'))
		func.__doc__ += '\n\n' + text

	return func

