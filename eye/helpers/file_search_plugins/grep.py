# this project is licensed under the WTFPLv2, see COPYING.txt for details

from logging import getLogger
import os

from eye.helpers.build import SimpleBuilder
from eye.helpers.file_search_plugins.base import register_plugin, SearchPlugin
from eye.procutils import find_command
from eye.qt import Slot

__all__ = ('AckGrep', 'AgGrep', 'BasicGrep')


LOGGER = getLogger(__name__)


class GrepProcess(SimpleBuilder):
	pattern = r'^(?P<path>.+):(?P<line>\d+):(?P<snippet>.*)$'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.remove_category('builder')


class GrepLike(SearchPlugin):
	cmd_base = None

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.runner = GrepProcess()
		self.runner.started.connect(self.started)
		self.runner.warning_printed.connect(self._got_result)
		self.runner.finished.connect(self.finished)

	def __del__(self):
		self.interrupt()

	@classmethod
	def is_available(cls, path):
		return find_command(cls.cmd_base[0]) is not None

	@classmethod
	def search_root_path(cls, path):
		path = path or '.'
		if os.path.isfile(path):
			path = os.path.dirname(path)
		return path

	@Slot(dict)
	def _got_result(self, d):
		self.found.emit(d)

	def interrupt(self):
		self.runner.interrupt()

	def search(self, path, pattern, case_sensitive=True):
		path = path or '.'
		cmd = list(self.cmd_base)
		if not case_sensitive:
			cmd.append('-i')

		cmd.append(pattern)
		cmd.append(path)
		self.runner.rootpath = path
		self.runner.set_working_directory(path)
		self.runner.run(cmd)


@register_plugin
class AckGrep(GrepLike):
	id = 'ack'
	# ack insists on using stdin despite being given filepaths
	cmd_base = ['ack-grep', '--nofilter']


@register_plugin
class AgGrep(GrepLike):
	id = 'ag'
	cmd_base = ['ag']


@register_plugin
class BasicGrep(GrepLike):
	id = 'rgrep'
	cmd_base = ['grep', '-n', '-R']


@register_plugin
class RipGrep(GrepLike):
	id = 'rg'
	cmd_base = ['rg', '-n']
