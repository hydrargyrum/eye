# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging
import shlex

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QLocalServer

from ..widgets.helpers import CategoryMixin
from ..connector import registerSignal, disabled
from ..app import qApp

Signal = pyqtSignal
Slot = pyqtSlot

__all__ = ('ServerSocket', 'SERVER', 'onRequestOpen')


LOGGER = logging.getLogger(__name__)
MAX_REQUEST_SIZE = 4096


class ClientSession(QObject, CategoryMixin):
	receivedRequest = Signal(object)
	error = Signal()

	def __init__(self, sock):
		super(ClientSession, self).__init__(parent=sock)
		self.sock = sock
		self.buffer = ''

		sock.readyRead.connect(self.onReadyRead)

		self.addCategory('remote_socket')

	@Slot()
	def onReadyRead(self):
		nb = self.sock.bytesAvailable()
		self.buffer += self.sock.read(nb)
		LOGGER.debug('received %d bytes', nb)

		if len(self.buffer) > MAX_REQUEST_SIZE:
			return self.error()
		elif '\n' in self.buffer:
			self.handle_requests()

	def handle_requests(self):
		while '\n' in self.buffer:
			pos = self.buffer.find('\n')
			assert pos >= 0
			line, self.buffer = self.buffer[:pos], self.buffer[pos + 1:]
			self.handle_request(line)

	def handle_request(self, line):
		try:
			request = shlex.split(line)
		except ValueError as exc:
			LOGGER.warning('received malformed request %r: %s', line, exc)
			self.error.emit()
		else:
			LOGGER.info('received request %r', request)
			self.receivedRequest.emit(request)


class ServerSocket(QObject):
	def __init__(self):
		super(ServerSocket, self).__init__()

		self.server = QLocalServer(self)
		self.server.newConnection.connect(self.clientConnected)

		self.socketPath = 'eye-control'

	def listen(self):
		# TODO allow multiple instances? multiple sockets, but clean on exit
		QLocalServer.removeServer(self.socketPath)
		if not self.server.listen(self.socketPath):
			LOGGER.error('could not listen: %s', self.server.errorString())

	@Slot()
	def clientConnected(self):
		sock = self.server.nextPendingConnection()
		session = ClientSession(sock)
		session.error.connect(sock.abort)


@registerSignal(['remote_socket'], 'receivedRequest')
@disabled
def onRequestOpen(sock, request):
	# TODO a decorator for handling this
	if len(request) != 2 or request[0] != 'open':
		return

	win = qApp().lastWindow
	win.bufferOpen(request[1])

# TODO json requests?
# TODO responses?


SERVER = ServerSocket()
