# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSlot as Slot

from logging import getLogger
import os
import re

from .base import registerPlugin, SearchPlugin
from ...procutils import findCommand
from ..build import SimpleBuilder


__all__ = ('AckGrep', 'AgGrep', 'BasicGrep')


LOGGER = getLogger(__name__)


class GrepProcess(SimpleBuilder):
	pattern = '^(?P<path>.+):(?P<line>\d+):(?P<snippet>.*)$'

	def __init__(self, **kwargs):
		super(GrepProcess, self).__init__(**kwargs)
		self.removeCategory('builder')


class GrepLike(SearchPlugin):
	cmd_base = None

	def __init__(self, **kwargs):
		super(GrepLike, self).__init__(**kwargs)
		self.runner = GrepProcess()
		self.runner.started.connect(self.started)
		self.runner.warningPrinted.connect(self._gotResult)
		self.runner.finished.connect(self.finished)

	def __del__(self):
		self.interrupt()

	@classmethod
	def isAvailable(cls, path):
		return findCommand(cls.cmd_base[0]) is not None

	@classmethod
	def searchRootPath(cls, path):
		path = path or '.'
		if os.path.isfile(path):
			path = os.path.dirname(path)
		return path

	@Slot(dict)
	def _gotResult(self, d):
		self.found.emit(d)

	def interrupt(self):
		self.runner.interrupt()

	def search(self, path, pattern, caseSensitive=True):
		path = path or '.'
		cmd = list(self.cmd_base)
		if not caseSensitive:
			cmd.append('-i')

		cmd.append(pattern)
		cmd.append(path)
		self.runner.rootpath = path
		self.runner.setWorkingDirectory(path)
		self.runner.run(cmd)


@registerPlugin
class AckGrep(GrepLike):
	id = 'ack'
	# ack insists on using stdin despite being given filepaths
	cmd_base = ['ack-grep', '--nofilter']


@registerPlugin
class AgGrep(GrepLike):
	id = 'ag'
	cmd_base = ['ag']


@registerPlugin
class BasicGrep(GrepLike):
	id = 'rgrep'
	cmd_base = ['grep', '-n', '-R']
