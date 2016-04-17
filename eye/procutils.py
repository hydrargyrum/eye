# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QProcess, pyqtSignal as Signal, pyqtSlot as Slot

import logging
import os

from .three import str, bytes


__all__ = ('findCommand', 'LineProcess')


LOGGER = logging.getLogger(__name__)

def findCommand(cmd):
	for elem in os.getenv('PATH').split(os.pathsep):
		path = os.path.join(elem, cmd)
		if os.path.isfile(path):
			return path


class LineProcess(QProcess):
	stdoutLineRead = Signal(str)
	stderrLineRead = Signal(str)

	def __init__(self, **kwargs):
		super(LineProcess, self).__init__(**kwargs)
		self.bufs = [b'', b'']
		self.encoding = 'utf-8'
		self.linesep = b'\n'

		self.readyReadStandardError.connect(self.onStderr)
		self.readyReadStandardOutput.connect(self.onStdout)
		self.stateChanged.connect(self.onStateChanged)

	@Slot(int)
	def onStateChanged(self, state):
		if state == self.Starting:
			cmd = [self.program()] + self.arguments()
			LOGGER.debug('starting process %r', cmd)

	def setEncoding(self, encoding):
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
		self._perform(1, self.readAllStandardError(), self.stderrLineRead.emit)
