# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging
import os

from PyQt5.QtCore import QProcess

from eye.qt import Signal, Slot

__all__ = ('find_command', 'LineProcess', 'run_blocking')


LOGGER = logging.getLogger(__name__)


def find_command(cmd):
	"""Find `cmd` in `$PATH`"""
	for elem in os.getenv('PATH').split(os.pathsep):
		path = os.path.join(elem, cmd)
		if os.path.isfile(path):
			return path


class LineProcess(QProcess):
	"""Process with stdout/stderr line handling

	The process is run in background. Signals are emitted when full lines are read from stdout or stderr.
	"""

	stdout_line_read = Signal(str)

	"""Signal stdout_line_read(str)"""

	stderr_line_read = Signal(str)

	"""Signal stderr_line_read(str)"""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.bufs = [b'', b'']
		self.encoding = 'utf-8'
		self.linesep = b'\n'

		self.readyReadStandardError.connect(self.on_stderr)
		self.readyReadStandardOutput.connect(self.on_stdout)
		self.stateChanged.connect(self.on_state_changed)
		self.finished.connect(self.on_finish)
		self.errorOccurred.connect(self.on_error)

	def stop(self, wait=0):
		"""Terminate process"""
		if wait and self.state() != self.NotRunning:
			self.terminate()
			self.waitForFinished(wait)
		if self.state() != self.NotRunning:
			self.kill()

	@Slot(QProcess.ProcessState)
	def on_state_changed(self, state):
		if state == self.Starting:
			cmd = [self.program()] + self.arguments()
			LOGGER.debug('starting process %r', cmd)

	def set_encoding(self, encoding):
		"""Set encoding for reading stdout/stderr"""
		self.encoding = encoding

	def _perform(self, fd, incoming, sig):
		# TODO decode before searching newline?
		self.bufs[fd] += bytes(incoming)
		while b'\n' in self.bufs[fd]:
			line, self.bufs[fd] = self.bufs[fd].split(self.linesep, 1)
			sig.emit(line.decode(self.encoding))

	@Slot()
	def on_stdout(self):
		self._perform(0, self.readAllStandardOutput(), self.stdout_line_read)

	@Slot()
	def on_stderr(self):
		self._perform(1, self.readAllStandardError(), self.stderr_line_read)

	@Slot()
	def on_error(self):
		cmd = [self.program()] + self.arguments()
		LOGGER.warning('error when running %r: %s', cmd, self.errorString())

	@Slot(int)
	def on_finish(self, ret):
		if ret != 0:
			cmd = [self.program()] + self.arguments()
			LOGGER.info('command %r exited with code %r', cmd, ret)


class ReadingProcess(QProcess):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.stdin = b''
		self.buf = []

		self.started.connect(self.on_started)
		self.bytesWritten.connect(self.on_started)
		self.readyReadStandardOutput.connect(self.on_stdout)

	@Slot()
	def on_started(self, _=None):
		while True:
			written = self.write(self.stdin)
			if written < 0:
				LOGGER.warning('error writing data to stdin for command %r', self.arguments())
				return
			elif written == 0:
				break
			self.stdin = self.stdin[written:]
		if not self.stdin:
			self.closeWriteChannel()

	@Slot()
	def on_stdout(self):
		while self.bytesAvailable() > 0:
			self.buf.append(self.read(self.bytesAvailable()))

	def set_standard_input(self, data):
		self.stdin = data

	def get_buffer(self):
		return b''.join(self.buf)


def run_blocking(cmd, stdin=b'', cwd=''):
	proc = ReadingProcess()
	if stdin:
		proc.set_standard_input(stdin)
	if cwd:
		proc.setWorkingDirectory(cwd)

	proc.start(cmd[0], cmd[1:])
	proc.waitForFinished(-1)
	return proc.exitCode(), proc.get_buffer()

