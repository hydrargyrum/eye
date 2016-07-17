# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Builder processes helpers

This module adds helpers for builders, programs which process source code and build a program out of it or simply
check syntax, etc.
"""

from PyQt5.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot

import logging
import os
import re
import shlex

from ..connector import CategoryMixin
from ..procutils import LineProcess
from ..pathutils import getRelativePathIn


__all__ = ('Builder', 'registerPlugin',
           'SimpleBuilder')


LOGGER = logging.getLogger(__name__)
DATA_LOGGER = LOGGER.getChild('simplebuilder')


class Builder(QObject, CategoryMixin):
	"""Abstract builder class

	Subclasses should reimplement :any:`run` and :any:`columns`. They can reimplement :any:`interrupt` and
	should emit various signals.
	"""

	warningPrinted = Signal(dict)

	"""Signal warningPrinted(info)

	:param info: warning output by the builder
	:type info: dict

	This signal is emitted when a warning occurs.

	The dict argument contains info about the warning. The keys can be arbitrary and everything is optional,
	but the common keys are `"path"`, `"line"`, `"col"`, `"message"`.
	"""

	errorPrinted = Signal(dict)

	"""Signal errorPrinted(info)

	:param info: error output by the builder
	:type info: dict

	This signal is emitted when an error occurs.

	See :any:`warningPrinted` about the dict argument.
	"""

	started = Signal()

	"""Signal started()

	This signal is emitted when the builder starts running.
	"""

	finished = Signal(int)

	"""Signal finished(code)

	:param code: the exit code of the builder
	:type code: int

	This signal is emitted when the build finishes running, and the overall return code is the argument.
	By convention, a 0 code means successful end, while 1 and other values mean an error occured or at least
	warnings.
	"""

	progress = Signal(int)

	"""Signal progress(int)

	This signal is emitted from time to time to indicate building progress. Some builders may not emit it at all.
	The argument is a percentage of the progress.
	"""

	def __init__(self, **kwargs):
		super(Builder, self).__init__(**kwargs)
		self.addCategory('builder')

	def columns(self):
		"""Return the list of columns supported by this builder type

		The columns are the keys of the dict emitted in :any:`warningPrinted` and :any:`errorPrinted`.

		This method should be reimplemented in `Builder` subclasses.
		"""
		raise NotImplementedError()

	def interrupt(self):
		"""Stop the builder process

		The default implementation does nothing.
		"""
		pass

	def run(self, *args, **kwargs):
		"""Start the builder process

		This method should be reimplemented in `Builder` subclasses.
		"""
		raise NotImplementedError()

	def workingDirectory(self):
		pass


PLUGINS = {}


def registerPlugin(cls):
	PLUGINS[cls.id] = cls
	return cls


@registerPlugin
class SimpleBuilder(Builder):
	"""Simple builder suitable for gcc-like programs

	This builder is suitable for programs outputting lines in the format specified by `pattern` attribute.
	Lines not matching this pattern are simply discarded (but the column is optional).

	The default pattern looks like `"<path>:<line>:<col>: <message>"`.
	"""

	pattern = '^(?P<path>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)? (?P<message>.*)$'
	pattern_flags = 0

	id = 'command'

	def __init__(self, **kwargs):
		super(SimpleBuilder, self).__init__(**kwargs)
		self.reobj = re.compile(self.pattern, self.pattern_flags)

		self.proc = LineProcess()
		self.proc.stdoutLineRead.connect(self.gotLine)
		self.proc.stderrLineRead.connect(self.gotLine)
		self.proc.finished.connect(self.finished)
		self.proc.started.connect(self.started)

	def columns(self):
		return ('path', 'line', 'message')

	@Slot(str)
	def gotLine(self, line):
		DATA_LOGGER.info('%r', line)

		mtc = self.reobj.match(line)
		if not mtc:
			LOGGER.info('%r received non-matching line %r', self, line)
			return

		LOGGER.debug('%r received matching line %r', self, line)

		signal = self.warningPrinted

		obj = mtc.groupdict()
		obj['line'] = int(obj['line'])
		if obj.get('col'):
			obj['col'] = int(obj['col'])

		msg = obj.get('message')
		if msg:
			msg = msg.strip()
			if msg.startswith('warning: '):
				msg = msg.replace('warning: ', '', 1)
			elif msg.startswith('error: '):
				signal = self.errorPrinted
				msg = msg.replace('error: ', '', 1)
			elif msg.startswith('note: '):
				LOGGER.info('%r ignored note line %r', self, line)
				return
			obj['message'] = msg

		rootpath = self.proc.workingDirectory()
		# make path absolute and shortpath relative
		obj['path'] = os.path.join(rootpath, obj['path'])
		obj['shortpath'] = getRelativePathIn(obj['path'], rootpath) or obj['path']

		signal.emit(obj)

	def interrupt(self):
		self.proc.stop()

	def setWorkingDirectory(self, path):
		self.proc.setWorkingDirectory(path)

	def workingDirectory(self):
		return self.proc.workingDirectory()

	def run(self, cmd):
		"""Run `cmd` as builder command

		:type cmd: list

		This method should be called by subclasses in :any:`run`.
		"""
		self.proc.start(cmd[0], cmd[1:])

	def run_conf(self, command, dir, file):
		vars = dict(dir=dir, file=file)
		args = shlex.split(command)
		args = [arg.format(**vars) for arg in args]

		self.proc.setWorkingDirectory(dir)
		self.run(args)


class PyFlakes(SimpleBuilder):
	def run(self, path):
		super(PyFlakes, self).run(['pyflakes', path])
