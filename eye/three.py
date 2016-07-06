# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Python 2 and Python 3 compatibility

This module exports `bytes`, `str`. In Python 3, they map to the normal `bytes` and `str`, but in
Python 2, the module exports them as aliases to `str` and `unicode`, respectively.

Through all the EYE documentation, `bytes` and `str` will refer to the Python 3 types. EYE uses
this module to keep compatibility with both versions of Python. The
`six <https://pythonhosted.org/six/>`_ third-party module is also used in EYE.

`range` is also exported, mapping to `xrange` on Python 2. A drop-in implementation of `execfile`
for Python 3 is exported too.
"""

import sys

# pylint: disable=redefined-builtin

if sys.version_info.major < 3:
	from __builtin__ import str as bytes, unicode as str
	from __builtin__ import execfile, xrange as range
else:
	from builtins import bytes, str, range

	# cheap but ad-hoc replacement
	def execfile(path, globals):
		"""Exec Python `file` with `globals` as in Python 2"""
		with open(path) as fd:
			src = fd.read()
		code = compile(src, path, 'exec')
		exec(code, globals)  # pylint: disable=exec-used


__all__ = ('bytes', 'str', 'execfile', 'range')
