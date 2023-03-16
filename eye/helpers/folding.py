# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin for non-lexical code folding

Default lexers provide code folding, for example functions can be folded. This plugin provides folding that isn't
based on lexer tokens but on markers. For example "{{{" for starting a fold zone and "}}}" for ending a fold zone.

Simple usage:

	>>> import eye.helpers.folding
	>>> eye.helpers.folding.set_marker_folder.enabled = True
"""

import re

from PyQt5.Qsci import QsciScintilla
from PyQt5.QtCore import QObject, QTimer

from eye.connector import disabled, default_lexer_config, default_editor_config
from eye.qt import Slot
from eye.widgets.editor import HasWeakEditorMixin

__all__ = ('MarkerFolder', 'disable_lexer_folding', 'set_marker_folder')


@default_lexer_config
@disabled
def disable_lexer_folding(ed, *args):
	"""Disable folding based on QsciLexer for an editor widget"""
	ed.set_lexer_property(b'fold', b'0')


class MarkerFolder(QObject, HasWeakEditorMixin):
	marker_start = re.compile(r'\{\{\{')
	marker_end = re.compile(r'\}\}\}')
	interval = 100

	def __init__(self, editor=None, **kwargs):
		super(MarkerFolder, self).__init__(**kwargs)
		self.editor = editor
		editor.sci_modified.connect(self.on_modification)
		self.timer = QTimer()
		self.timer.setSingleShot(True)
		self.timer.timeout.connect(self.refold_queue)
		self.lines_to_refold = set()

		if editor:
			self.refold(True)

	@Slot()
	def refold(self, force=False):
		self.refold_at(0, force)

	@Slot()
	def refold_queue(self, force=False):
		while len(self.lines_to_refold):
			start = self.lines_to_refold.pop()
			self.refold_at(start, force)

	def refold_at(self, start, force=False):
		waitnext = True
		level = self.editor.get_fold_level(start) & QsciScintilla.SC_FOLDLEVELNUMBERMASK
		for i in range(start, self.editor.lines()):
			self.lines_to_refold.discard(i)
			flag = 0

			line = self.editor.text(i)
			diff = len(self.marker_start.findall(line))
			if diff:
				flag |= QsciScintilla.SC_FOLDLEVELHEADERFLAG
			diff -= len(self.marker_end.findall(line))

			new = level | flag
			current = self.editor.get_fold_level(i)
			if force or current != new:
				self.editor.set_fold_level(i, new)
				waitnext = True
			else:
				if not waitnext:
					break
				waitnext = False

			level += diff

	@Slot(object)
	def on_modification(self, st):
		refold = None

		if st.modificationType & QsciScintilla.SC_MOD_INSERTTEXT:
			refold, _ = self.editor.lineIndexFromPosition(st.position)
		elif st.modificationType & QsciScintilla.SC_MOD_DELETETEXT:
			refold, _ = self.editor.lineIndexFromPosition(st.position)

		if refold is not None:
			self.lines_to_refold.add(refold)
			if not self.timer.isActive():
				self.timer.start(self.interval)

		# TODO smarter refold: check if insert/delete contains pattern or changes folding


@default_editor_config
@default_lexer_config
@disabled
def set_marker_folder(editor, *args):
	"""Enable folding based on markers for an editor widget"""
	editor.set_lexer_property(b'fold', b'0')
	editor.folding = MarkerFolder(editor=editor)
