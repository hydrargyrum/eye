# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging
import os

from PyQt5.QtCore import QProcess, pyqtSignal as Signal, pyqtSlot as Slot

from .three import str, bytes


__all__ = ('findCommand', 'LineProcess')


LOGGER = logging.getLogger(__name__)


def findCommand(cmd):
	"""Find `cmd` in `$PATH`"""
	for elem in os.getenv('PATH').split(os.pathsep):
		path = os.path.join(elem, cmd)
		if os.path.isfile(path):
			return path


class LineProcess(QProcess):
	"""Process with stdout/stderr line handling

	The process is run in background. Signals are emitted when full lines are read from stdout or stderr.
	"""

	stdoutLineRead = Signal(str)

	"""Signal stdoutLineRead(str)"""

	stderrLineRead = Signal(str)

	"""Signal stderrLineRead(str)"""

	def __init__(self, **kwargs):
		super(LineProcess, self).__init__(**kwargs)
		self.bufs = [b'', b'']
		self.encoding = 'utf-8'
		self.linesep = b'\n'

		self.readyReadStandardError.connect(self.onStderr)
		self.readyReadStandardOutput.connect(self.onStdout)
		self.stateChanged.connect(self.onStateChanged)
		self.finished.connect(self.onFinish)
		if hasattr(self, 'errorOccurred'): # qt >=5.6
			self.errorOccurred.connect(self.onError)
		elif hasattr(self, 'error'):
			self.error.connect(self.onError)

	def stop(self, wait=0):
		"""Terminate process"""
		if wait and self.state() != self.NotRunning:
			self.terminate()
			self.waitForFinished(wait)
		if self.state() != self.NotRunning:
			self.kill()

	@Slot(QProcess.ProcessState)
	def onStateChanged(self, state):
		if state == self.Starting:
			cmd = [self.program()] + self.arguments()
			LOGGER.debug('starting process %r', cmd)

	def setEncoding(self, encoding):
		"""Set encoding for reading stdout/stderr"""
		self.encoding = encoding

	def _perform(self, fd, incoming, sig):
		# TODO decode before searching newline?
		self.bufs[fd] += bytes(incoming)
		while b'\n' in self.bufs[fd]:
			line, self.bufs[fd] = self.bufs[fd].split(self.linesep, 1)
			sig.emit(line.decode(self.encoding))

	@Slot()
	def onStdout(self):
		self._perform(0, self.readAllStandardOutput(), self.stdoutLineRead)

	@Slot()
	def onStderr(self):
		self._perform(1, self.readAllStandardError(), self.stderrLineRead)

	@Slot()
	def onError(self):
		cmd = [self.program()] + self.arguments()
		LOGGER.warning('error when running %r: %s', cmd, self.errorString())

	@Slot(int)
	def onFinish(self, ret):
		if ret != 0:
			cmd = [self.program()] + self.arguments()
			LOGGER.info('command %r exited with code %r', cmd, ret)
