# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

from base64 import b64encode, b64decode
import hashlib
import hmac
import json
import logging
import mimetypes
import os
try:
	from simplejson import JSONDecodeError
except ImportError:
	JSONDecodeError = ValueError
import socket
import tempfile
import time

from six.moves.urllib.parse import urlunsplit
from PyQt5.QtCore import pyqtSignal as Signal, QObject, QTimer, QProcess, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QMessageBox

from ..three import str, bytes
from ..structs import PropDict
from ..connector import registerSignal, disabled, CategoryMixin, categoryObjects
from ..qt import Slot
from ..app import qApp
from ..pathutils import getConfigFilePath
from .intent import sendIntent, registerIntentListener


__all__ = ('Ycm',)


HMAC_SECRET_LENGTH = 16
HMAC_HEADER = 'X-Ycm-Hmac'

LOGGER = logging.getLogger(__name__)


### ycm daemon control

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
	YCMD_CMD = ['ycmd']
	IDLE_SUICIDE = 120
	CHECK_REPLY_SIGNATURE = True
	TIMEOUT = 10

	def __init__(self, **kwargs):
		super(Ycm, self).__init__(**kwargs)

		self.port = 0
		self.proc = QProcess()
		self._ready = False
		self.addr = None
		self.secret = ''
		self.config = {}

		self.pingTimer = QTimer(self)
		self.pingTimer.timeout.connect(self.ping)

		self.network = QNetworkAccessManager()

		qApp().aboutToQuit.connect(self.stop)

		self.addCategory('ycm_control')

	def makeConfig(self):
		self.secret = generate_key()
		self.config['hmac_secret'] = b64encode(self.secret).decode('ascii')

		fd, path = tempfile.mkstemp()
		with open(path, 'w') as fd:
			fd.write(json.dumps(self.config))
			fd.flush()
		return path

	def checkReply(self, reply):
		reply.content = bytes(reply.readAll())

		if reply.error():
			raise ServerError(reply.error() + 1000, reply.errorString())
		status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
		if status_code != 200:
			data = reply.content.decode('utf-8')
			try:
				data = json.loads(data)
			except (ValueError, JSONDecodeError):
				LOGGER.info('ycmd replied non-json body: %r', data)

			raise ServerError(status_code, data)

		if not self.CHECK_REPLY_SIGNATURE:
			return
		actual = b64decode(bytes(reply.rawHeader(HMAC_HEADER)))
		expected = self._hmacDigest(reply.content)

		if not hmac.compare_digest(expected, actual):
			raise RuntimeError('Server signature did not match')

	def _jsonReply(self, reply):
		body = reply.content.decode('utf-8')
		return json.loads(body)

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

		request = QNetworkRequest(QUrl(url))
		for hname in headers:
			request.setRawHeader(hname, headers[hname])

		reply = self.network.get(request)
		return reply

	def _doPost(self, path, **params):
		url = urlunsplit(('http', self.addr, path, '', ''))
		body = json.dumps(params)
		sig = self._sign(b'POST', path.encode('utf-8'), body.encode('utf-8'))
		headers = {
			HMAC_HEADER: b64encode(sig),
			'Content-Type': 'application/json'
		}

		request = QNetworkRequest(QUrl(url))
		for hname in headers:
			request.setRawHeader(hname, headers[hname])
		reply = self.network.post(request, body)
		return reply

	def ping(self):
		def handleReply():
			self.checkReply(reply)
			if not self._ready:
				self._ready = True
				self.pingTimer.start(60000)
				self.ready.emit()

		reply = self._doGet('/healthy')
		reply.finished.connect(handleReply)

	def start(self):
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

		LOGGER.debug('will run %r', cmd)

		self.proc.start(cmd[0], cmd[1:])

		self._ready = False
		self.pingTimer.start(1000)

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
		self.addr = addr
		self._ready = False
		self.pingTimer.start(1000)

	ready = Signal()

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

	def sendParse(self, filepath, filetype, contents, retry_extra=True):
		d = {
			'event_name': 'FileReadyToParse'
		}
		reply = self._postSimpleRequest('/event_notification', filepath, filetype, contents, **d)

		def handleReply():
			try:
				self.checkReply(reply)
			except ServerError as exc:
				excdata = exc.args[1]
				if (isinstance(excdata, dict) and 'exception' in excdata and
					excdata['exception']['TYPE'] == 'UnknownExtraConf' and
					retry_extra):
					confpath = excdata['exception']['extra_conf_file']
					LOGGER.info('ycmd encountered %r and wonders if it should be loaded', confpath)

					accepted = sendIntent(None, 'queryExtraConf', conf=confpath)
					if accepted:
						LOGGER.info('extra conf %r will be loaded', confpath)
						self.acceptExtraConf(confpath, filetype, contents)
					else:
						LOGGER.info('extra conf %r will be rejected', confpath)
						self.rejectExtraConf(confpath, filetype, contents)

					return self.sendParse(filepath, filetype, contents, retry_extra=False)
				raise

		reply.finished.connect(handleReply)

	if 0:
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

	if 0:
		def queryDiagnostic(self, filepath, filetype, contents, line, col):
			return self._postSimpleRequest('/detailed_diagnostic', filepath, filetype, contents)

		def queryDebug(self, filepath, filetype, contents, line, col):
			return self._postSimpleRequest('/debug_info', filepath, filetype, contents)


DAEMON = Ycm()

### give source files to ycm

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
def onSave(editor, path):
	if not isCompletionAvailable():
		return

	DAEMON.sendParse(path, editor.ycm.filetype, editor.text())


@registerSignal('ycm_control', 'ready')
@disabled
def onYcmReady(ycm):
	for editor in categoryObjects('editor'):
		if editor.path:
			onLoad(editor, editor.path)

### queries

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


def isCompletionAvailable():
	return DAEMON and DAEMON.isRunning()


def doCompletion(editor, replace=True):
	if not isCompletionAvailable():
		return

	def handleReply():
		DAEMON.checkReply(reply)
		res = DAEMON._jsonReply(reply)

		if res['completions']:
			col = res['completion_start_column'] - 1
			offset = editor.positionFromLineIndex(editor.cursorLine(), col)
			items = [{
				'insert': item['insertion_text'],
				'display': item.get('menu') or item['insertion_text'],
			} for item in res['completions']]

			showCompletionList(editor, offset, items, replace)

	reply = _query(DAEMON.queryCompletions, editor)
	reply.finished.connect(handleReply)


@registerSignal('editor', 'SCN_CHARADDED')
@registerSignal('editor', 'SCN_AUTOCCHARDELETED')
def onCharAdded(editor, *args):
	if not isCompletionAvailable():
		return

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

	startl, startc = ed.lineIndexFromPosition(start)
	with ed.undoGroup():
		ed.deleteRange(start, end - start)
		ed.insertAt(text, startl, startc)
	ed.setCursorPosition(startl, startc + len(text))


if 0:
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


def repr_qrequest(request):
	return '<QNetworkRequest url=%r>' % request.url()


def setEnabled(enabled=True):
	onLoad.enabled = enabled
	onSave.enabled = enabled
	onCharAdded.enabled = enabled
	onYcmReady.enabled = enabled

	if enabled:
		if not DAEMON.isRunning():
			DAEMON.start()
	else:
		if DAEMON.isRunning():
			DAEMON.stop()

### ycm "extra conf" intent listeners

def isInFile(expected, path):
	if os.path.exists(path):
		with open(path) as fd:
			for line in fd:
				line = line.strip()
				if line.startswith('#'):
					continue
				if line == expected:
					return True
	return False


def addToFile(line, path):
	with open(path, 'a') as fd:
		print(line, file=fd)


CONF_ACCEPT = 'ycm.extra.accept.conf'
CONF_REJECT = 'ycm.extra.reject.conf'

@registerIntentListener('queryExtraConf')
@disabled
def queryExtraConfUseConf(source, ev, defaultReject=True):
	ycmpath = ev.info['conf']
	if isInFile(ycmpath, getConfigFilePath(CONF_ACCEPT)):
		ev.accept(True)
		return True

	if defaultReject or isInFile(ycmpath, getConfigFilePath(CONF_REJECT)):
		ev.accept(False)
		return True

	return False


@registerIntentListener('queryExtraConf')
@disabled
def queryExtraConfDialog(source, ev):
	if queryExtraConfUseConf(source, ev, defaultReject=False):
		return True

	ycmpath = ev.info['conf']

	title = 'Allow YouCompleteMe extra conf?'
	text = 'Load %r? This may be a security risk if the file comes from an untrusted source.' % ycmpath
	dlg = QMessageBox(QMessageBox.Question, title, text)
	bOkOnce = dlg.addButton('Load once', QMessageBox.AcceptRole)
	bOkAlways = dlg.addButton('Load always', QMessageBox.AcceptRole)
	bNoOnce = dlg.addButton('Reject once', QMessageBox.RejectRole)
	bNoAlways = dlg.addButton('Reject always', QMessageBox.RejectRole)
	dlg.setDefaultButton(bNoOnce)
	dlg.setEscapeButton(bNoOnce)
	dlg.exec_()

	clicked = dlg.clickedButton()
	if clicked in (bOkOnce, bOkAlways):
		if clicked is bOkAlways:
			addToFile(ycmpath, getConfigFilePath(CONF_ACCEPT))
		ev.accept(True)
		return True
	elif clicked in (bNoOnce, bNoAlways):
		if clicked is bNoAlways:
			addToFile(ycmpath, getConfigFilePath(CONF_REJECT))
		ev.accept(False)
		return True

	return False
