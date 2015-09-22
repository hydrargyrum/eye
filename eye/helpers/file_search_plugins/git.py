# this project is licensed under the WTFPLv2, see COPYING.txt for details

import errno
import os
import subprocess
from logging import getLogger

from .base import registerPlugin, SearchPlugin


__all__ = ('GitGrep',)


LOGGER = getLogger(__name__)

@registerPlugin
class GitGrep(SearchPlugin):
	id = "git-grep"

	def isAvailable(self, path):
		if os.path.isfile(path):
			path = os.path.dirname(path)

		with open(os.devnull, 'w') as nul:
			try:
				res = subprocess.call(['git', 'rev-parse'], cwd=path, stderr=nul)
			except OSError, e:
				if e.errno == errno.ENOENT:
					res = 1
		return not res

	def searchRootPath(self, path):
		path = path or '.'
		if os.path.isfile(path):
			path = os.path.dirname(path)
		cmd = ['git', 'rev-parse', '--show-toplevel']
		return subprocess.check_output(cmd, cwd=path).strip()

	def search(self, path, expr, caseSensitive=True):
		path = path or '.'
		cmd = ['git', 'grep', '-n', '-I', '-z', expr]
		if not caseSensitive:
			cmd.insert(-1, '-i')

		out = subprocess.check_output(cmd, cwd=path)

		for line in out.split('\n'):
			if not line:
				continue
			try:
				f, line, snippet = line.split('\x00')
			except ValueError:
				LOGGER.warning('cannot parse output line %r when searching %r', line, expr, exc_info=True)
				continue

			snippet = snippet.strip()
			yield (f, line, snippet)
