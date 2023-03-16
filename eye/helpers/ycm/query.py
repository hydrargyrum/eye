# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

from PyQt5.QtCore import QObject

from eye.connector import register_signal, disabled
from eye.qt import Signal, Slot

from .daemon import get_daemon, is_daemon_available, ServerError


def _query(cb, editor, *args, **kwargs):
	line = kwargs.pop('line', editor.cursorLine() + 1)
	col = kwargs.pop('col', editor.cursorColumn() + 1)

	return cb(editor.path, editor.ycm.filetype, editor.text(), line, col, *args, **kwargs)


def show_completion_list(editor, offset, items, replace=True):
	editor.compListItems = {
		item['display']: item for item in items
	}

	if replace:
		editor.comp_start_offset = offset
	editor.showUserList(1, [item['display'] for item in items])


def do_completion(editor, replace=True):
	if not is_daemon_available():
		return

	def handle_reply():
		get_daemon().check_reply(reply)
		res = get_daemon()._json_reply(reply)

		if res['completions']:
			col = res['completion_start_column'] - 1
			offset = editor.positionFromLineIndex(editor.cursorLine(), col)
			items = [{
				'insert': item['insertion_text'],
				'display': item.get('menu') or item['insertion_text'],
			} for item in res['completions']]

			show_completion_list(editor, offset, items, replace)

	reply = _query(get_daemon().query_completions, editor)
	reply.finished.connect(handle_reply)
	reply.finished.connect(reply.deleteLater)


def do_go_to(editor, go_type):
	if not is_daemon_available():
		return

	def handle_reply():
		get_daemon().check_reply(reply)
		res = get_daemon()._json_reply(reply)
		from eye.helpers.buffers import open_editor
		open_editor(res['filepath'], (res['line_num'], res['column_num']))

	reply = _query(get_daemon().query_subcommand, editor, go_type)
	reply.finished.connect(handle_reply)
	reply.finished.connect(reply.deleteLater)


@register_signal('editor', 'SCN_CHARADDED')
@register_signal('editor', 'SCN_AUTOCCHARDELETED')
@disabled
def complete_on_char_added(editor, *args):
	if not is_daemon_available():
		return

	if not editor.isListActive() or editor.autoCompListId != 1:
		return
	do_completion(editor)


@register_signal('editor', 'userListActivated')
def on_activate(ed, listid, display):
	if listid != 1:
		return

	start = ed.comp_start_offset
	end = ed.cursor_offset()

	item = ed.comp_list_items[display]

	text = item['insert']

	startl, startc = ed.lineIndexFromPosition(start)
	with ed.undo_group():
		ed.delete_range(start, end - start)
		ed.insertAt(text, startl, startc)
	ed.set_cursor_position(startl, startc + len(text))


def query_sub_commands_list(editor):
	def handle_reply():
		get_daemon().check_reply(reply)
		res = get_daemon()._json_reply(reply)
		print(res)

	reply = _query(get_daemon().query_subcommands_list, editor)
	reply.finished.connect(handle_reply)
	reply.finished.connect(reply.deleteLater)


if 1:
	def query_diag(editor):
		res = _query(get_daemon().query_diagnostic, editor)
		print(res)


	def query_debug(editor):
		res = _query(get_daemon().query_debug, editor)
		print(res)


	def query_sub_command(editor, *args, **kwargs):
		def handle_reply():
			get_daemon().check_reply(reply)
			res = get_daemon()._json_reply(reply)
			print(res)

		reply = _query(get_daemon().query_subcommand, editor, *args, **kwargs)
		reply.finished.connect(handle_reply)
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

	search_type = None

	def __init__(self, *args, **kwargs):
		super(YcmSearch, self).__init__(*args, **kwargs)
		self.reply = None

	def find_under_cursor(self, editor):
		self.started.emit()
		self.reply = _query(get_daemon().query_subcommand, editor, self.search_type)
		self.reply.finished.connect(self._on_reply)
		self.reply.finished.connect(self.reply.deleteLater)

	@Slot()
	def interrupt(self):
		if self.reply:
			self.reply.finished.disconnect(self._on_reply)
			self.reply.abort()
			self.reply.deleteLater()
			self.reply = None

	@Slot()
	def _on_reply(self):
		result_code = 1

		try:
			get_daemon().check_reply(self.reply)
		except ServerError:
			pass
		else:
			self._handle_reply(get_daemon()._json_reply(self.reply))
			result_code = 0
		finally:
			self.reply = None
			self.finished.emit(result_code)

	def _handle_reply(self, obj):
		if isinstance(obj, dict):
			obj = [obj]
		if isinstance(obj, list):
			for sub in obj:
				self._send_result(sub)

	def _send_result(self, obj):
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

	search_type = 'GoToDeclaration'


class YcmGoToDefinition(YcmSearch):
	"""Plugin to find the definition of a symbol"""

	search_type = 'GoToDefinition'


class YcmGoToReferences(YcmSearch):
	"""Plugin to find usage of a symbol"""

	search_type = 'GoToReferences'

