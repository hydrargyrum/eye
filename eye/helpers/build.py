# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Builder processes helpers

This module adds helpers for builders, programs which process source code and build a program out of it or simply
check syntax, etc.
"""

import logging
import os
import re
import shlex

from PyQt5.QtCore import QObject

from eye.connector import CategoryMixin
from eye.pathutils import get_relative_path_in
from eye.procutils import LineProcess
from eye.qt import Signal, Slot

__all__ = (
	'Builder', 'register_plugin', 'SimpleBuilder',
	'JobHolder',
)


LOGGER = logging.getLogger(__name__)
DATA_LOGGER = LOGGER.getChild('simplebuilder')


class Builder(QObject, CategoryMixin):
	"""Abstract builder class

	Subclasses should reimplement :any:`run` and :any:`columns`. They can reimplement :any:`interrupt` and
	should emit various signals.
	"""

	warning_printed = Signal(dict)

	"""Signal warning_printed(info)

	:param info: warning output by the builder
	:type info: dict

	This signal is emitted when a warning occurs.

	The dict argument contains info about the warning. The keys can be arbitrary and everything is optional,
	but the common keys are `"path"`, `"line"`, `"col"`, `"message"`.
	"""

	error_printed = Signal(dict)

	"""Signal error_printed(info)

	:param info: error output by the builder
	:type info: dict

	This signal is emitted when an error occurs.

	See :any:`warning_printed` about the dict argument.
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
		"""
		:param parent: if not given, a default parent is used (a default :any:`JobHolder` instance)
		"""
		super().__init__(**kwargs)
		if 'parent' not in kwargs:
			DEFAULT_HOLDER.add_job(self)
		self.add_category('builder')

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

	def working_directory(self):
		pass


PLUGINS = {}


def register_plugin(cls):
	PLUGINS[cls.id] = cls
	return cls


@register_plugin
class SimpleBuilder(Builder):
	"""Simple builder suitable for gcc-like programs

	This builder is suitable for programs outputting lines in the format specified by `pattern` attribute.
	Lines not matching this pattern are simply discarded (but the column is optional).

	The default pattern looks like `"<path>:<line>:<col>: <message>"`.
	"""

	pattern = r'^(?P<path>[^:]+):(?P<line>\d+):(?:(?P<col>\d+):)? (?P<message>.*)$'
	pattern_flags = 0

	id = 'command'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.reobj = re.compile(self.pattern, self.pattern_flags)

		self.proc = LineProcess()
		self.proc.stdout_line_read.connect(self.gotLine)
		self.proc.stderr_line_read.connect(self.gotLine)
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

		signal = self.warning_printed

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
				signal = self.error_printed
				msg = msg.replace('error: ', '', 1)
			elif msg.startswith('note: '):
				LOGGER.info('%r ignored note line %r', self, line)
				return
			obj['message'] = msg

		rootpath = self.proc.workingDirectory()
		# make path absolute and shortpath relative
		obj['path'] = os.path.join(rootpath, obj['path'])
		obj['shortpath'] = get_relative_path_in(obj['path'], rootpath) or obj['path']

		signal.emit(obj)

	def interrupt(self):
		self.proc.stop()

	def set_working_directory(self, path):
		self.proc.setWorkingDirectory(path)

	def working_directory(self):
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
		super().run(['pyflakes', path])


class JobHolder(QObject):
	def add_job(self, job):
		"""Re-parents the job to self and un-parent when job is finished.

		`addJob` should be called before the job is started, to avoid the possibility of the
		job being finished before `addJob` has done what it should do.

		The job is re-parented so a reference is kept. When the job is finished, it is un-parented,
		which may remove the last reference to it. The goal is that the `Builder` object may be
		garbage-collected once it has emitted its `finished` signal.
		To achieve this, the `JobHolder` must be the only one keeping a reference to the job object.

		:param job: job to hold
		:type job: :any:`eye.helpers.build.Builder`
		:returns: the `job` passed
		"""
		job.finished.connect(self._finished)
		job.setParent(self)
		return job

	@Slot()
	def _finished(self):
		self.sender().setParent(None)


DEFAULT_HOLDER = JobHolder()
