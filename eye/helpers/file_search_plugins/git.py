# this project is licensed under the WTFPLv2, see COPYING.txt for details

import errno
import os
import subprocess
from logging import getLogger

from .base import registerPlugin
from .grep import GrepLike


__all__ = ('GitGrep',)


LOGGER = getLogger(__name__)

@registerPlugin
class GitGrep(GrepLike):
	id = "git-grep"
	cmd_base = ['git', 'grep', '-n', '-I']

	@classmethod
	def isAvailable(cls, path):
		if os.path.isfile(path):
			path = os.path.dirname(path)

		with open(os.devnull, 'w') as nul:
			try:
				res = subprocess.call(['git', 'rev-parse'], cwd=path, stderr=nul)
			except OSError as e:
				if e.errno == errno.ENOENT:
					res = 1
		return not res

	@classmethod
	def searchRootPath(cls, path):
		path = path or '.'
		if os.path.isfile(path):
			path = os.path.dirname(path)
		cmd = ['git', 'rev-parse', '--show-toplevel']
		return subprocess.check_output(cmd, cwd=path).strip()
