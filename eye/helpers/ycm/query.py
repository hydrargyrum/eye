# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

from PyQt5.QtCore import QObject

from ...connector import registerSignal, disabled
from ...qt import Signal, Slot
from .daemon import getDaemon, isDaemonAvailable, ServerError


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
	if not isDaemonAvailable():
		return

	def handleReply():
		getDaemon().checkReply(reply)
		res = getDaemon()._jsonReply(reply)

		if res['completions']:
			col = res['completion_start_column'] - 1
			offset = editor.positionFromLineIndex(editor.cursorLine(), col)
			items = [{
				'insert': item['insertion_text'],
				'display': item.get('menu') or item['insertion_text'],
			} for item in res['completions']]

			showCompletionList(editor, offset, items, replace)

	reply = _query(getDaemon().queryCompletions, editor)
	reply.finished.connect(handleReply)
	reply.finished.connect(reply.deleteLater)


def doGoTo(editor, go_type):
	if not isDaemonAvailable():
		return

	def handleReply():
		getDaemon().checkReply(reply)
		res = getDaemon()._jsonReply(reply)
		from ..buffers import openEditor
		openEditor(res['filepath'], (res['line_num'], res['column_num']))

	reply = _query(getDaemon().querySubcommand, editor, go_type)
	reply.finished.connect(handleReply)
	reply.finished.connect(reply.deleteLater)


@registerSignal('editor', 'SCN_CHARADDED')
@registerSignal('editor', 'SCN_AUTOCCHARDELETED')
@disabled
def completeOnCharAdded(editor, *args):
	if not isDaemonAvailable():
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


def querySubCommandsList(editor):
	def handleReply():
		getDaemon().checkReply(reply)
		res = getDaemon()._jsonReply(reply)
		print(res)

	reply = _query(getDaemon().querySubcommandsList, editor)
	reply.finished.connect(handleReply)
	reply.finished.connect(reply.deleteLater)


if 1:
	def queryDiag(editor):
		res = _query(getDaemon().queryDiagnostic, editor)
		print(res)


	def queryDebug(editor):
		res = _query(getDaemon().queryDebug, editor)
		print(res)


	def querySubCommand(editor, *args, **kwargs):
		def handleReply():
			getDaemon().checkReply(reply)
			res = getDaemon()._jsonReply(reply)
			print(res)

		reply = _query(getDaemon().querySubcommand, editor, *args, **kwargs)
		reply.finished.connect(handleReply)
		reply.finished.connect(reply.deleteLater)


class YcmSearch(QObject):
	"""Search plugin using ycmd engine

	The `started`, `found` and `finished` signals work like other search plugins
	(see :any:`eye.helpers.file_search_plugins.base.SearchPlugin`).
	However, the entry point of the search is not a pattern but a position in a
	file, to follow a symbol name in a source context.
	"""

	started = Signal()
	found = Signal(dict)
	finished = Signal(int)

	searchType = None

	def __init__(self, *args, **kwargs):
		super(YcmSearch, self).__init__(*args, **kwargs)
		self.reply = None

	def findUnderCursor(self, editor):
		self.started.emit()
		self.reply = _query(getDaemon().querySubcommand, editor, self.searchType)
		self.reply.finished.connect(self._onReply)
		self.reply.finished.connect(self.reply.deleteLater)

	@Slot()
	def interrupt(self):
		if self.reply:
			self.reply.finished.disconnect(self._onReply)
			self.reply.abort()
			self.reply.deleteLater()
			self.reply = None

	@Slot()
	def _onReply(self):
		resultCode = 1

		try:
			getDaemon().checkReply(self.reply)
		except ServerError:
			pass
		else:
			self._handleReply(getDaemon()._jsonReply(self.reply))
			resultCode = 0
		finally:
			self.reply = None
			self.finished.emit(resultCode)

	def _handleReply(self, obj):
		if isinstance(obj, dict):
			obj = [obj]
		if isinstance(obj, list):
			for sub in obj:
				self._sendResult(sub)

	def _sendResult(self, obj):
		ret = {
			'path': obj['filepath'],
			'line': obj['line_num'],
			'col': obj['column_num'],
		}
		if 'description' in obj:
			ret['snippet'] = obj['description']

		self.found.emit(ret)


class YcmGoToDeclaration(YcmSearch):
	"""Plugin to find the declaration of a symbol"""

	searchType = 'GoToDeclaration'


class YcmGoToDefinition(YcmSearch):
	"""Plugin to find the definition of a symbol"""

	searchType = 'GoToDefinition'


class YcmGoToReferences(YcmSearch):
	"""Plugin to find usage of a symbol"""

	searchType = 'GoToReferences'

