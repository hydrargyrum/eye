# this project is licensed under the WTFPLv2, see COPYING.txt for details

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
