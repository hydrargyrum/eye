# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Python 2 and Python 3 compatibility

This module exports `bytes`, `str`. In Python 3, they map to the normal `bytes` and `str`, but in Python 2, the
module exports them as aliases to `str` and `unicode` respectively.

Through all the EYE documentation, `bytes` and `str` will refer to the Python 3 names. EYE uses this module to keep
compatibility with both versions of Python. The `six <https://pythonhosted.org/six/>`_ third-party module is also used in EYE.
"""

import sys

__all__ = ('bytes', 'str', 'execfile')


if sys.version_info.major < 3:
	bytes, str = str, unicode

	execfile = execfile
else:
	bytes, str = bytes, str

	# cheap but ad-hoc replacement
	def execfile(path, globals):
		with open(path) as fd:
			src = fd.read()
		code = compile(src, path, 'exec')
		exec(code, globals)
