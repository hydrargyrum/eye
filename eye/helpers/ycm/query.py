# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

from ...connector import registerSignal, disabled
from.daemon import getDaemon, isDaemonAvailable


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


if 0:
	def querySub(editor):
		res = _query(getDaemon().querySubcommandsList, editor)
		print(res)


	def queryDiag(editor):
		res = _query(getDaemon().queryDiagnostic, editor)
		print(res)


	def queryDebug(editor):
		res = _query(getDaemon().queryDebug, editor)
		print(res)


	def queryGoTo(editor, *args, **kwargs):
		res = _query(getDaemon().queryGoTo, editor, *args, **kwargs)
		print(res)


	def queryInfo(editor, *args, **kwargs):
		res = _query(getDaemon().queryInfo, editor, *args, **kwargs)
		print(res)
