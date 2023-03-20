# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os
import re

from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex, QRegExp, Qt, QTimer, QElapsedTimer, QEvent
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QTreeView, QWidget, QFileSystemModel, QApplication

from eye.consts import AbsolutePathRole
from eye.helpers.intent import send_intent
from eye.qt import Slot
from eye.structs import PropDict
from eye.widgets.helpers import WidgetMixin

__all__ = ('FileChooser', 'SubSequenceFileChooser', 'selectFileInChooser')


def commonPrefix(strings):
	res = ''
	for cs in zip(*strings):
		if len(set(cs)) == 1:
			res += cs[0]
		else:
			break
	return res


class RootChangerProxy(QSortFilterProxyModel):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.srcRoot = QModelIndex()

	def setRootSource(self, srcRoot):
		self.modelAboutToBeReset.emit() # TODO be a bit more clever
		self.srcRoot = srcRoot
		self.modelReset.emit()
		self.sourceModel().fetchMore(srcRoot)

	def mapToSource(self, proxyIdx):
		if not proxyIdx.isValid():
			return self.srcRoot
		srcParent = self.mapToSource(proxyIdx.parent())
		return self.sourceModel().index(proxyIdx.row(), proxyIdx.column(), srcParent)

	def mapFromSource(self, srcIdx):
		if srcIdx == self.srcRoot or not srcIdx.isValid():
			return QModelIndex()
		proxyParent = self.mapFromSource(srcIdx.parent())
		return self.index(srcIdx.row(), srcIdx.column(),proxyParent)


class BaseFileChooser(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.options = PropDict()

		# sub-widgets
		layout = QVBoxLayout()
		self.setLayout(layout)

		self.edit = QLineEdit()
		layout.addWidget(self.edit)
		self.setFocusProxy(self.edit)

		self.view = QTreeView()
		layout.addWidget(self.view)

		self.edit.installEventFilter(self)

		self.setWindowTitle(self.tr('File selector'))
		self.add_category('filechooser')

	def setModel(self, model):
		self.view.setModel(model)

	@Slot(str)
	def setRoot(self, path):
		raise NotImplementedError()

	def openFile(self, path):
		send_intent(self, 'open_editor', path=path, reason='filechooser')

	def eventFilter(self, obj, ev):
		if (obj is not self.edit
			or ev.type() not in (QEvent.KeyPress, QEvent.KeyRelease)
			or ev.key() not in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_PageDown)):

			return super().eventFilter(obj, ev)

		QApplication.sendEvent(self.view, ev)
		return True


def walk_files(root, ignore_re=None):
	for dp, dirs, files in os.walk(root):
		if ignore_re:
			dirs[:] = filter(ignore_re.match, dirs)

		for f in files:
			if ignore_re and ignore_re.match(f):
				continue
			yield os.path.join(dp, f)


class SubSequenceProxy(QSortFilterProxyModel):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.reobj = re.compile('')
		self.scores = {}

	def setFilter(self, text):
		parts = map(QRegExp.escape, text)
		pattern = '.*?'.join('(%s)' % part for part in parts)
		self.reobj = re.compile(pattern, re.I)
		self.cache = {}
		self.invalidate()

	def filterAcceptsRow(self, row, parent):
		if not self.reobj.pattern:
			return False

		mdl = self.sourceModel()
		qidx = mdl.index(row, 0, parent)
		text = mdl.data(qidx)
		mtc = self.reobj.search(text)
		if mtc:
			self.scores[text] = self._score_match(mtc, text)
		return bool(mtc)

	def _score(self, qidx):
		text = self.sourceModel().data(qidx)
		try:
			return self.scores[text]
		except KeyError:
			pass

		mtc = self.reobj.search(text)
		self.scores[text] = self._score_match(mtc, text)
		return self.scores[text]

	def _score_match(self, mtc, text):
		n = self.reobj.groups

		seq = 0
		sub = 0
		left = 0
		for i in range(1, n + 1):
			if i == 1:
				left += mtc.start(i)
			else:
				if mtc.start(i) == mtc.start(i - 1) + 1:
					seq += 1
				else:
					left += mtc.start(i) - mtc.start(i - 1)

			if mtc.start(i) == 0:
				sub += 1
			else:
				sub += int(text[mtc.start(i) - 1] in '/.-_')

		score = (-seq, -sub, left, text)
		return score

	def lessThan(self, qidx1, qidx2):
		if not self.reobj.groups:
			return qidx1.data() < qidx2.data()
		return self._score(qidx1) < self._score(qidx2)


class SubSequenceFileChooser(BaseFileChooser):
	maxSecsPerCrawlBatch = .1

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.mdl = QStandardItemModel()
		self.filter = SubSequenceProxy()
		self.filter.setSourceModel(self.mdl)
		self.view.setModel(self.filter)

		self.view.setRootIsDecorated(False)
		self.view.setAlternatingRowColors(True)
		self.view.sortByColumn(0, Qt.AscendingOrder)

		self.view.activated.connect(self._on_activated)

		self.edit.textEdited.connect(self._on_text_edited)

		self.crawlTimer = QTimer()
		# restart the timer manually so an exception breaks the loop and timer
		self.crawlTimer.setSingleShot(True)
		self.crawlTimer.timeout.connect(self.crawlBatch)
		self.crawler = None

	@Slot(str)
	def _on_text_edited(self, text):
		selected = self.view.selectedIndexes()
		qidx = None
		if len(selected):
			qidx = self.filter.mapToSource(selected[0])

		self.filter.setFilter(text)

		if qidx is not None:
			qidx = self.filter.mapFromSource(qidx)

		if qidx is None or not qidx.isValid():
			qidx = self.filter.index(0, 0)
		self.view.setCurrentIndex(qidx)

	@Slot()
	def crawlBatch(self):
		start_time = QElapsedTimer()
		start_time.start()
		prefix_len = len(self.root) + 1 # 1 for the /

		for path in self.crawler:
			subpath = path[prefix_len:]

			qitem = QStandardItem(subpath)
			qitem.setData(path, AbsolutePathRole)
			qitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
			self.mdl.appendRow(qitem)

			if start_time.hasExpired(self.maxSecsPerCrawlBatch * 1000):
				self.crawlTimer.start(0)
				break

	def setRoot(self, root):
		self.root = os.path.abspath(root)
		self.mdl.clear()
		self.mdl.setHorizontalHeaderLabels([self.tr('File')])

		self.crawler = walk_files(root)
		self.crawlTimer.start(0)

	@Slot(QModelIndex)
	def _on_activated(self, qidx):
		path = self.filter.data(qidx, AbsolutePathRole)
		if not os.path.isfile(path): # symlinks?
			return
		self.openFile(path)

	# TODO be able to configure crawling: ignored patterns, depth, etc.


class FileChooser(BaseFileChooser):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.options = PropDict()

		self.edit.textEdited.connect(self._on_text_edited)

		self.view.activated.connect(self._on_activated)

		# models
		self.rootChanger = RootChangerProxy()

		fsModel = QFileSystemModel(self)
		self.setModel(fsModel)

		self.filter = QSortFilterProxyModel()
		self.filter.setSourceModel(self.rootChanger)
		self.view.setModel(self.filter)

	def setModel(self, model):
		self.baseModel = model
		self.rootChanger.setSourceModel(self.baseModel)

	@Slot(str)
	def setRoot(self, path):
		self.root = path
		srcIdx = self.baseModel.setRootPath(path)
		self.rootChanger.setRootSource(srcIdx)
		self.view.setRootIndex(QModelIndex())

	@Slot(str)
	def _on_text_edited(self, txt):
		elems = txt.rsplit('/', 1)
		if len(elems) == 2:
			dir, base = elems
		else:
			dir, base = '', elems[0]

		path = os.path.join(self.root, dir)
		self.rootChanger.setRootSource(self.baseModel.index(path))
		self.filter.setFilterRegExp(QRegExp(base, Qt.CaseInsensitive, QRegExp.Wildcard))

		if self.options.get('autosuggest'):
			names = [self.filter.data(self.filter.index(i, 0)).toString()
				 for i in range(self.filter.rowCount(QModelIndex()))]
			names = [n[len(base):] for n in names]
			add = commonPrefix(names)

			cursor = self.edit.cursorPosition()
			self.edit.setText(self.edit.text()[:cursor] + add)
			self.edit.setSelection(cursor, len(self.edit.text()))

	@Slot(QModelIndex)
	def _on_activated(self, idx):
		idx = self.filter.mapToSource(idx)
		idx = self.rootChanger.mapToSource(idx)
		info = self.baseModel.fileInfo(idx)
		if info.isDir():
			return
		path = info.absoluteFilePath()
		self.openFile(path)


def selectFileInChooser(path, chooser):
	"""Select file/dir item in file chooser

	Does nothing if file is not in the tree viewed by file chooser.
	"""

	if not path.startswith(chooser.root):
		return False

	model = chooser.view.model()
	chain = [model]
	while hasattr(model, "sourceModel"):
		model = model.sourceModel()
		chain.append(model)

	qidx = chain[-1].index(path)
	if not qidx.isValid():
		return False

	for model in reversed(chain[:-1]):
		qidx = model.mapFromSource(qidx)

	chooser.view.setCurrentIndex(qidx)
	return True
