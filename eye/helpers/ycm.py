# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

from PyQt5.QtCore import pyqtSignal as Signal, QObject, QTimer, QProcess

from base64 import b64encode, b64decode
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import requests
try:
	from simplejson import JSONDecodeError
except ImportError:
	JSONDecodeError = ValueError
import socket
import sys
import tempfile
import time

from six.moves.urllib.parse import urljoin, urlunsplit

from ..three import str
from ..structs import PropDict
from ..connector import registerSignal, disabled
from ..qt import Slot
from ..app import qApp
from .intent import sendIntent


__all__ = ('Ycm',)


HMAC_SECRET_LENGTH = 16
HMAC_HEADER = 'X-Ycm-Hmac'

LOGGER = logging.getLogger(__name__)


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


class Ycm(QObject):
	YCMD_CMD = ['ycmd']
	IDLE_SUICIDE = 120
	CHECK_REPLY_SIGNATURE = True
	TIMEOUT = 10

	def __init__(self, **kwargs):
		super(Ycm, self).__init__(**kwargs)

		self.port = 0
		self.proc = QProcess()
		self.addr = None
		self.secret = ''
		self.config = {}

		self.pingTimer = QTimer(self)
		self.pingTimer.timeout.connect(self.ping)

		qApp().aboutToQuit.connect(self.stop)

	def makeConfig(self):
		self.secret = generate_key()
		self.config['hmac_secret'] = b64encode(self.secret).decode('ascii')

		fd, path = tempfile.mkstemp()
		with open(path, 'w') as fd:
			fd.write(json.dumps(self.config))
			fd.flush()
		return path

	def _checkReply(self, reply):
		try:
			data = reply.json()
		except (ValueError, JSONDecodeError):
			LOGGER.info('ycmd replied non-json body: %r', reply.text)
			data = reply.text

		if reply.status_code != 200:
			raise ServerError(reply.status_code, data)

		if not self.CHECK_REPLY_SIGNATURE:
			return
		actual = b64decode(reply.headers[HMAC_HEADER])
		expected = self._hmacDigest(reply.content)

		if not hmac.compare_digest(expected, actual):
			raise RuntimeError('Server signature did not match')

	def _hmacDigest(self, msg):
		return hmac.new(self.secret, msg, hashlib.sha256).digest()

	def _sign(self, verb, path, body=b''):
		digests = [self._hmacDigest(part) for part in [verb, path, body]]
		return self._hmacDigest(b''.join(digests))

	def _doGet(self, path):
		url = urlunsplit(('http', self.addr, path, '', ''))
		sig = self._sign(b'GET', path.encode('utf-8'), b'')
		headers = {
			HMAC_HEADER: b64encode(sig)
		}

		reply = requests.get(url, headers=headers, timeout=self.TIMEOUT)
		self._checkReply(reply)
		return reply.json()

	def _doPost(self, path, **params):
		ignore_body = params.pop('_ignore_body', False)

		url = urlunsplit(('http', self.addr, path, '', ''))
		body = json.dumps(params)
		sig = self._sign(b'POST', path.encode('utf-8'), body.encode('utf-8'))
		headers = {
			HMAC_HEADER: b64encode(sig),
			'Content-Type': 'application/json'
		}

		reply = requests.post(url, data=body, headers=headers, timeout=self.TIMEOUT)
		self._checkReply(reply)
		if ignore_body:
			return
		else:
			return reply.json()

	def ping(self):
		self._doGet('/healthy')

	def start(self):
		self.pingTimer.start(60000)
		if not self.port:
			self.port = generate_port()
		self.addr = 'localhost:%s' % self.port
		path = self.makeConfig()

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

		self.proc.start(cmd[0], cmd[1:])

	def waitForStarted(self, wait=1):
		start = time.time()
		while time.time() - start < wait:
			try:
				self.ping()
			except requests.exceptions.ConnectionError:
				time.sleep(0.1)
			else:
				break

	@Slot()
	def stop(self, wait=0.2):
		if self.proc.state() == QProcess.NotRunning:
			return
		self.proc.terminate()
		if self.proc.state() == QProcess.NotRunning:
			return
		time.sleep(wait)
		self.proc.kill()

	def isRunning(self):
		return self.proc.state() == QProcess.Running

	def connectTo(self, addr):
		self.pingTimer.start(60000)
		self.addr = addr

	def _commonPostDict(self, filepath, filetype, contents):
		d = {
			'filepath': filepath,
			'filetype': filetype,
			'file_data': {
				filepath: {
					'filetypes': [filetype],
					'contents': contents
				}
			},
			'line_num': 1, # useless but required
			'column_num': 1,
		}
		return d

	def _postSimpleRequest(self, urlpath, filepath, filetype, contents, **kwargs):
		d = self._commonPostDict(filepath, filetype, contents)
		d.update(**kwargs)

		return self._doPost(urlpath, **d)

	def acceptExtraConf(self, filepath, filetype, contents):
		return self._postSimpleRequest('/load_extra_conf_file', filepath, filetype, contents)

	def rejectExtraConf(self, filepath, filetype, contents):
		return self._postSimpleRequest('/ignore_extra_conf_file', filepath, filetype, contents,
		                               _ignore_body=True)

	def sendParse(self, filepath, filetype, contents):
		d = {
			'event_name': 'FileReadyToParse'
		}
		attempt = lambda: self._postSimpleRequest('/event_notification', filepath, filetype, contents, **d)

		try:
			return attempt()
		except ServerError as exc:
			excdata = exc.args[1]
			if (isinstance(excdata, dict) and 'exception' in excdata and
			    excdata['exception']['TYPE'] == 'UnknownExtraConf'):
				confpath = excdata['exception']['extra_conf_file']
				LOGGER.info('ycmd encountered %r and wonders if it should be loaded', confpath)

				accepted = sendIntent(None, 'queryExtraConf', conf=confpath)
				if accepted:
					LOGGER.info('extra conf %r will be loaded', confpath)
					self.acceptExtraConf(confpath, filetype, contents)
				else:
					LOGGER.info('extra conf %r will be rejected', confpath)
					self.rejectExtraConf(confpath, filetype, contents)
				return attempt()
			raise

	def querySubcommandsList(self, filepath, filetype, contents, line, col):
		return self._postSimpleRequest('/defined_subcommands', filepath, filetype, contents)

	def _querySubcommand(self, filepath, filetype, contents, line, col, *args):
		d = {
			'command_arguments': list(args)
		}
		return self._postSimpleRequest('/run_completer_command', filepath, filetype, contents, **d)

	def queryGoTo(self, *args):
		res = self._querySubcommand(*args)
		if res.get('filepath'):
			return {
				'filepath': res['filepath'],
				'line': res['line_num'],
				'column': res['column_num'],
			}

	def queryInfo(self, *args):
		res = self._querySubcommand(*args)
		return res.get('message', '') or res.get('detailed_info', '')

	def queryCompletions(self, filepath, filetype, contents, line, col):
		d = {
			'line_num': line,
			'column_num': col,
		}
		return self._postSimpleRequest('/completions', filepath, filetype, contents, **d)

	def queryDiagnostic(self, filepath, filetype, contents, line, col):
		return self._postSimpleRequest('/detailed_diagnostic', filepath, filetype, contents)

	def queryDebug(self, filepath, filetype, contents, line, col):
		return self._postSimpleRequest('/debug_info', filepath, filetype, contents)


DAEMON = Ycm()


MIME_YCMFILETYPE = {
	'application/javascript': 'js',
	'text/x-chdr': 'c',
	'text/x-csrc': 'c',
	'text/x-c++hdr': 'cpp',
	'text/x-c++src': 'cpp',
	'text/x-python': 'python',
}

EXT_YCMFILETYPE = {
	'c': 'c',
	'cc': 'cpp',
	'cpp': 'cpp',
	'cs': 'cs',
	'go': 'go',
	'h': 'cpp',
	'hh': 'cpp',
	'hpp': 'cpp',
	'js': 'js',
	'py': 'python',
}

def ycmFiletype(path):
	mime, _ = mimetypes.guess_type(path)
	try:
		return MIME_YCMFILETYPE[mime]
	except KeyError:
		pass

	_, dotext = os.path.splitext(path)
	ext = dotext[1:]
	try:
		return EXT_YCMFILETYPE[ext]
	except KeyError:
		return 'general'


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@disabled
def onLoad(editor, path):
	editor.ycm = PropDict()
	editor.ycm.filetype = ycmFiletype(path)
	DAEMON.sendParse(path, editor.ycm.filetype, editor.text())


@registerSignal('editor', 'fileSaved')
@disabled
def onSave(editor):
	DAEMON.sendParse(path, editor.ycm.filetype, editor.text())


def _query(cb, editor, *args, **kwargs):
	line = kwargs.pop('line', editor.cursorLine() + 1)
	col = kwargs.pop('col', editor.cursorColumn() + 1)

	return cb(editor.path, editor.ycm.filetype, editor.text(), line, col, *args, **kwargs)


def showCompletionList(editor, offset, items, replace=True):
	editor.compListItems = {
		item['display']: item for item in items
	}

	if replace:
		editor.compStartOffset = offset
	editor.showUserList(1, [item['display'] for item in items])


def doCompletion(editor, replace=True):
	res = _query(DAEMON.queryCompletions, editor)

	if res['completions']:
		col = res['completion_start_column'] - 1
		offset = editor.positionFromLineIndex(editor.cursorLine(), col)
		items = [{
			'insert': item['insertion_text'],
			'display': item.get('menu') or item['insertion_text'],
		} for item in res['completions']]

		showCompletionList(editor, offset, items, replace)


@registerSignal('editor', 'SCN_CHARADDED')
@registerSignal('editor', 'SCN_AUTOCCHARDELETED')
def onCharAdded(editor, *args):
	if not editor.isListActive() or editor.autoCompListId != 1:
		return
	doCompletion(editor)


@registerSignal('editor', 'userListActivated')
def onActivate(ed, listid, display):
	if listid != 1:
		return

	start = ed.compStartOffset
	end = ed.cursorOffset()

	item = ed.compListItems[display]

	text = item['insert']

	ed.setTargetRange(start, end)
	line, col = ed.lineIndexFromPosition(start)
	ed.replaceTarget(-1, text.encode('utf-8'))
	ed.setCursorPosition(line, col + len(text))


def querySub(editor):
	res = _query(DAEMON.querySubcommandsList, editor)
	print(res)


def queryDiag(editor):
	res = _query(DAEMON.queryDiagnostic, editor)
	print(res)


def queryDebug(editor):
	res = _query(DAEMON.queryDebug, editor)
	print(res)


def queryGoTo(editor, *args, **kwargs):
	res = _query(DAEMON.queryGoTo, editor, *args, **kwargs)
	print(res)


def queryInfo(editor, *args, **kwargs):
	res = _query(DAEMON.queryInfo, editor, *args, **kwargs)
	print(res)


def setEnabled(enabled=True):
	onLoad.enabled = enabled
	onCharAdded.enabled = enabled

	if enabled:
		if not DAEMON.isRunning():
			DAEMON.start()
			DAEMON.waitForStarted()
	else:
		if DAEMON.isRunning():
			DAEMON.stop()
