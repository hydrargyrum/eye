# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""YouCompleteMe daemon control module"""

from base64 import b64encode, b64decode
import hashlib
import hmac
import json
import logging
import os
import socket
import tempfile
import time
from urllib.parse import urlunsplit
import uuid

from PyQt5.QtCore import QObject, QTimer, QProcess, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from eye.connector import CategoryMixin
from eye.qt import Signal, Slot
from eye.app import qApp
from eye.helpers.intent import send_intent


HMAC_SECRET_LENGTH = 16
HMAC_HEADER = b'X-Ycm-Hmac'

LOGGER = logging.getLogger(__name__)
LOGGER_REQUESTS = LOGGER.getChild('requests')

DAEMON = None


__all__ = ('get_daemon', 'is_daemon_available', 'build_daemon', 'Ycm', 'ServerError')

def generate_port():
	sock = socket.socket()
	sock.bind(('', 0))
	port = sock.getsockname()[1]
	sock.close()
	return port


def generate_key():
	return os.urandom(HMAC_SECRET_LENGTH)


class ServerError(RuntimeError):
	pass


class Ycm(QObject, CategoryMixin):
	"""YCMD instance control"""

	YCMD_CMD = ['ycmd']
	"""Base ycmd command.

	Useful if ycmd is not in `PATH` or set permanent arguments
	"""

	IDLE_SUICIDE = 120
	"""Maximum time after which ycmd should quit if it has received no requests.

	A periodic ping is sent by `Ycm` objects.
	"""

	CHECK_REPLY_SIGNATURE = True
	TIMEOUT = 10

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.addr = None
		"""Address of the ycmd server."""

		self.port = 0
		"""TCP port of the ycmd server."""

		self._ready = False
		self.secret = ''
		self.config = {}

		self.proc = QProcess()
		self.proc.started.connect(self.proc_started)
		self.proc.errorOccurred.connect(self.proc_error)
		self.proc.finished.connect(self.proc_finished)

		self.ping_timer = QTimer(self)
		self.ping_timer.timeout.connect(self.ping)

		self.network = QNetworkAccessManager()

		qApp().aboutToQuit.connect(self.stop)

		self.add_category('ycm_control')

	def make_config(self):
		self.secret = generate_key()
		self.config['hmac_secret'] = b64encode(self.secret).decode('ascii')

		fd, path = tempfile.mkstemp()
		with open(path, 'w') as fd:
			fd.write(json.dumps(self.config))
			fd.flush()
		return path

	def check_reply(self, reply):
		"""Check the ycmd reply is a success.

		Checks the `reply` has a HTTP 200 status code and the signature is valid.
		In case of error, raises a :any:`ServerError`.

		:type reply: QNetworkReply
		"""
		reply.content = bytes(reply.readAll())

		if reply.error():
			raise ServerError(reply.error() + 1000, reply.errorString(), reply.content)
		status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
		if status_code != 200:
			data = reply.content.decode('utf-8')
			try:
				data = json.loads(data)
			except json.JSONDecodeError:
				LOGGER.info('ycmd replied non-json body: %r', data)

			raise ServerError(status_code, data)

		if not self.CHECK_REPLY_SIGNATURE:
			return
		actual = b64decode(bytes(reply.rawHeader(HMAC_HEADER)))
		expected = self._hmac_digest(reply.content)

		if not hmac.compare_digest(expected, actual):
			raise RuntimeError('Server signature did not match')

	def _json_reply(self, reply):
		body = reply.content.decode('utf-8')
		return json.loads(body)

	def _hmac_digest(self, msg):
		return hmac.new(self.secret, msg, hashlib.sha256).digest()

	def _sign(self, verb, path, body=b''):
		digests = [self._hmac_digest(part) for part in [verb, path, body]]
		return self._hmac_digest(b''.join(digests))

	def _do_get(self, path):
		url = urlunsplit(('http', self.addr, path, '', ''))
		sig = self._sign(b'GET', path.encode('utf-8'), b'')
		headers = {
			HMAC_HEADER: b64encode(sig)
		}

		request = QNetworkRequest(QUrl(url))
		for hname in headers:
			request.setRawHeader(hname, headers[hname])

		LOGGER_REQUESTS.debug('GET %r', url)
		reply = self.network.get(request)
		return reply

	def _do_post(self, path, **params):
		url = urlunsplit(('http', self.addr, path, '', ''))
		body = json.dumps(params).encode('utf-8')
		sig = self._sign(b'POST', path.encode('utf-8'), body)
		headers = {
			HMAC_HEADER: b64encode(sig),
			b'Content-Type': b'application/json'
		}

		request = QNetworkRequest(QUrl(url))
		for hname in headers:
			request.setRawHeader(hname, headers[hname])
		LOGGER_REQUESTS.debug('POST %r with data %r', url, body)
		reply = self.network.post(request, body)
		return reply

	def ping(self):
		reply = self._do_get('/healthy')
		reply.finished.connect(self._handle_reply_ping)
		reply.finished.connect(reply.deleteLater)

	@Slot()
	def _handle_reply_ping(self):
		reply = self.sender()
		self.check_reply(reply)
		if not self._ready:
			self._ready = True
			self.ping_timer.start(60000)
			self.ready.emit()

	def start(self):
		if not self.port:
			self.port = generate_port()
		self.addr = 'localhost:%s' % self.port
		path = self.make_config()

		_, outlogpath = tempfile.mkstemp(prefix='eye-ycm', suffix='.out.log')
		_, errlogpath = tempfile.mkstemp(prefix='eye-ycm', suffix='.err.log')
		LOGGER.info('ycmd will log to %r and %r', outlogpath, errlogpath)

		cmd = (self.YCMD_CMD +
			[
				'--idle_suicide_seconds', str(self.IDLE_SUICIDE),
				'--port', str(self.port),
				'--options_file', path,
				'--stdout', outlogpath,
				'--stderr', errlogpath,
			])

		LOGGER.debug('will run %r', cmd)

		self.proc.start(cmd[0], cmd[1:])

		self._ready = False

	@Slot()
	def stop(self, wait=0.2):
		if self.proc.state() == QProcess.NotRunning:
			return
		self.proc.terminate()
		if self.proc.state() == QProcess.NotRunning:
			return
		time.sleep(wait)
		self.proc.kill()

	def is_running(self):
		return self.proc.state() == QProcess.Running

	def connect_to(self, addr):
		self.addr = addr
		self._ready = False
		self.ping_timer.start(1000)

	@Slot()
	def proc_started(self):
		LOGGER.debug('daemon has started')
		self.ping_timer.start(1000)

	@Slot(int, QProcess.ExitStatus)
	def proc_finished(self, code, status):
		LOGGER.info('daemon has exited with status %r and code %r', status, code)
		self.ping_timer.stop()
		self._ready = False

	@Slot(QProcess.ProcessError)
	def proc_error(self, error):
		LOGGER.warning('daemon failed to start (%r): %s', error, self.proc.errorString())

	ready = Signal()

	def _common_post_dict(self, filepath, filetype, contents, line=1, column=1):
		d = {
			'filepath': filepath,
			'filetype': filetype,
			'file_data': {
				filepath: {
					'filetypes': [filetype],
					'contents': contents
				}
			},
			'line_num': line,
			'column_num': column,
		}
		return d

	def _post_simple_request(self, urlpath, filepath, filetype, contents, **kwargs):
		d = self._common_post_dict(filepath, filetype, contents)
		d.update(**kwargs)

		return self._do_post(urlpath, **d)

	def accept_extra_conf(self, filepath, filetype, contents):
		reply = self._post_simple_request('/load_extra_conf_file', filepath, filetype, contents)
		reply.finished.connect(reply.deleteLater)

	def reject_extra_conf(self, filepath, filetype, contents):
		reply = self._post_simple_request('/ignore_extra_conf_file', filepath, filetype, contents,
		                                _ignore_body=True)
		reply.finished.connect(reply.deleteLater)

	@Slot()
	def _handle_send_parse_reply(self):
		reply = self.sender()
		filepath, filetype, contents, retry_extra = reply.property("parse_params")

		try:
			self.check_reply(reply)
		except ServerError as exc:
			excdata = exc.args[1]
			if (
				isinstance(excdata, dict)
				and 'exception' in excdata
				and excdata['exception']['TYPE'] == 'UnknownExtraConf'
				and retry_extra
			):
				confpath = excdata['exception']['extra_conf_file']
				LOGGER.info('ycmd encountered %r and wonders if it should be loaded', confpath)

				accepted = send_intent(None, 'queryExtraConf', conf=confpath)
				if accepted:
					LOGGER.info('extra conf %r will be loaded', confpath)
					self.accept_extra_conf(confpath, filetype, contents)
				else:
					LOGGER.info('extra conf %r will be rejected', confpath)
					self.reject_extra_conf(confpath, filetype, contents)

				return self.send_parse(filepath, filetype, contents, retry_extra=False)

	def send_parse(self, filepath, filetype, contents, retry_extra=True):
		d = {
			'event_name': 'FileReadyToParse'
		}
		reply = self._post_simple_request('/event_notification', filepath, filetype, contents, **d)

		reply.setProperty("parse_params", [filepath, filetype, contents, retry_extra])

		reply.finished.connect(self._handle_send_parse_reply)
		reply.finished.connect(reply.deleteLater)

	def query_subcommands_list(self, filepath, filetype, contents, line, col):
		return self._post_simple_request('/defined_subcommands', filepath, filetype, contents)

	def query_subcommand(self, filepath, filetype, contents, line, col, *args):
		d = {
			'command_arguments': list(args),
			'line_num': line,
			'column_num': col,
		}
		return self._post_simple_request('/run_completer_command', filepath, filetype, contents, **d)

	def query_completions(self, filepath, filetype, contents, line, col):
		d = {
			'line_num': line,
			'column_num': col,
		}
		return self._post_simple_request('/completions', filepath, filetype, contents, **d)

	if 0:
		def query_diagnostic(self, filepath, filetype, contents, line, col):
			return self._post_simple_request('/detailed_diagnostic', filepath, filetype, contents)

		def query_debug(self, filepath, filetype, contents, line, col):
			return self._post_simple_request('/debug_info', filepath, filetype, contents)


def get_daemon():
	return DAEMON


def is_daemon_available():
	return DAEMON and DAEMON.is_running()


def build_daemon():
	global DAEMON
	DAEMON = Ycm()
	return DAEMON
