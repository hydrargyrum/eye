# this project is licensed under the WTFPLv2, see COPYING.txt for details

import errno
from logging import getLogger
import os
import subprocess

from eye.helpers.file_search_plugins.base import registerPlugin
from eye.helpers.file_search_plugins.grep import GrepLike

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
		return subprocess.check_output(cmd, cwd=path, encoding="utf-8").strip()
