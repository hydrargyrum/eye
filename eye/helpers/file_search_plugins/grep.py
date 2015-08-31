
import errno
import os
import subprocess
from logging import getLogger

from .base import registerPlugin, SearchPlugin
from ...procutils import findCommand


__all__ = ('AckGrep', 'AgGrep', 'BasicGrep')


LOGGER = getLogger(__name__)

class GrepLike(SearchPlugin):
	cmd_base = None

	def isAvailable(self, path):
		return findCommand(self.cmd_base[0]) is not None

	def searchRootPath(self, path):
		path = path or '.'
		if os.path.isfile(path):
			path = os.path.dirname(path)
		return path

	def search(self, path, expr, caseSensitive=True):
		path = path or '.'
		cmd = self.cmd_base + [expr]
		if not caseSensitive:
			cmd.insert(-1, '-i')

		#~ proc = subprocess.Popen(cmd, cwd=path, stdout=subprocess.PIPE)
		#~ out, err = proc.communicate()
		out = subprocess.check_output(cmd, cwd=path)
		for line in out.split('\n'):
			if not line:
				continue
			try:
				f, line, snippet = line.split(':', 2)
			except ValueError, e:
				LOGGER.exception(e)
				continue

			snippet = snippet.strip()
			yield (f, line, snippet)


@registerPlugin
class AckGrep(GrepLike):
	id = 'ack'
	cmd_base = ['ack-grep']


@registerPlugin
class AgGrep(GrepLike):
	id = 'ag'
	cmd_base = ['ag']


@registerPlugin
class BasicGrep(GrepLike):
	id = 'rgrep'
	cmd_base = ['grep', '-n', '-R']
