# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot

import logging
import os
import re

from ..connector import CategoryMixin
from ..procutils import LineProcess
from ..pathutils import getRelativePathIn


__all__ = ('Builder', 'SimpleBuilder')


LOGGER = logging.getLogger(__name__)


class Builder(QObject, CategoryMixin):
	errorPrinted = Signal(dict)
	warningPrinted = Signal(dict)
	finished = Signal(int)
	progress = Signal(int)

	def columns(self):
		raise NotImplementedError()

	def run(self, *args, **kwargs):
		raise NotImplementedError()


class SimpleBuilder(Builder):
	reobj = re.compile('^(?P<path>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)? (?P<message>.*)$')

	def __init__(self, **kwargs):
		super(SimpleBuilder, self).__init__(**kwargs)
		self.rootpath = ''
		self.proc = LineProcess()
		self.proc.stdoutLineRead.connect(self.gotLine)
		self.proc.finished.connect(self.finished)

	def columns(self):
		return ('path', 'line', 'message')

	@Slot(str)
	def gotLine(self, line):
		mtc = self.reobj.match(line)
		if not mtc:
			LOGGER.info('%r received non-matching line %r', self, line)
			return

		LOGGER.debug('%r received matching line %r', self, line)

		obj = mtc.groupdict()
		obj['line'] = int(obj['line'])
		if obj.get('col'):
			obj['col'] = int(obj['col'])
		if self.rootpath:
			# make path absolute and shortpath relative
			obj['path'] = os.path.join(self.rootpath, obj['path'])
			obj['shortpath'] = getRelativePathIn(obj['path'], self.rootpath) or obj['path']
		self.warningPrinted.emit(obj)

	def setWorkingDirectory(self, path):
		self.proc.setWorkingDirectory(path)

	def run_cmd(self, cmd):
		self.proc.start(cmd[0], cmd[1:])


class PyFlakes(SimpleBuilder):
	def run(self, path):
		if os.path.isdir(path):
			self.rootpath = path
		else:
			self.rootpath = os.path.dirname(path)
		self.run_cmd(['pyflakes', path])

