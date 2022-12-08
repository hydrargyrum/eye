# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging

from PyQt5.QtCore import QObject, QTimer, QElapsedTimer

from eye.connector import CategoryMixin
from eye.helpers.editor_search import props_to_re
from eye.qt import Signal, Slot
from eye.widgets.editor import HasWeakEditorMixin, SciModification

__all__ = (
	'RegexHighlighter',
)


LOGGER = logging.getLogger(__name__)


class RegexHighlighter(QObject, HasWeakEditorMixin, CategoryMixin):
	started = Signal()
	found = Signal(int, int)
	finished = Signal(int)

	def __init__(self, editor=None, indicatorName=None, props=None, **kwargs):
		super().__init__(**kwargs)
		self.editor = editor
		self.props = props

		self.indicator = editor.indicators.get(indicatorName)
		if not self.indicator:
			self.indicator = editor.create_indicator(indicatorName, 0)

		self.timer = QTimer(self)
		self.timer.setSingleShot(True)
		self.timer.setInterval(10)
		self.timer.timeout.connect(self._search_some)

		self.job = None

		self.edited_lines = []

		self.reobj = None

		self.editor.sciModified.connect(self.onModify)

		idx = self.metaObject().indexOfSignal('found(int,int)')
		self.foundMethod = self.metaObject().method(idx)

		self.add_category('highlighter')

	def __del__(self):
		self.clear()

	def clear(self):
		if self.indicator:
			self.indicator.clear()

	def doHighlight(self):
		self.clear()
		self.reobj = props_to_re(self.props)

		self.edited_lines = []
		self.timer.start()
		self.started.emit()

	@Slot()
	def _search_some(self):
		self.start_time = QElapsedTimer()
		self.start_time.start()

		if self.job is None:
			self.job = self._full_job()

		for _ in self.job:
			if self.start_time.hasExpired(10):
				self.timer.start()
				break
		else:
			self.job = None
			self.finished.emit(0)

	def _line_job(self, line):
		line_offset = self.editor.positionFromLineIndex(line, 0)

		linetext = self.editor.text(line)
		it = self.reobj.finditer(linetext)
		while True:
			mtc = next(it, None)
			if mtc is None:
				return
			else:
				self.indicator.putAt(line, mtc.start(), line, mtc.end())

				if len(linetext) < 4000 or self.isSignalConnected(self.foundMethod):
					offset_start = line_offset + self.editor.positionRelative(line_offset, mtc.start())
					offset_end = line_offset + self.editor.positionRelative(line_offset, mtc.end())
					self.found.emit(offset_start, offset_end)
			yield

	def _full_job(self):
		if self.edited_lines:
			for line in self.edited_lines:
				self.indicator.removeAt(line, 0, line + 1, 0)
				for _ in self._line_job(line):
					yield
			self.edited_lines = []
			return

		for line in range(self.editor.lines()):
			for _ in self._line_job(line):
				yield

	@Slot(SciModification)
	def onModify(self, modif):
		if modif.modificationType & (self.editor.SC_MOD_INSERTTEXT | self.editor.SC_MOD_DELETETEXT):
			line, _ = self.editor.lineIndexFromPosition(modif.position)
			if line not in self.edited_lines:
				self.edited_lines.append(line)
				self.timer.start()

		# TODO if regex can match newlines, we need to check neighbour lines

	def iterRanges(self):
		return list(self.indicator.iterRanges())

