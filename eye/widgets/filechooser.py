# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QSortFilterProxyModel, QModelIndex, QRegExp, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QTreeView, QWidget, QFileSystemModel
Signal = pyqtSignal
Slot = pyqtSlot

import os

from ..three import str
from ..structs import PropDict
from .helpers import WidgetMixin
from ..helpers import buffers


__all__ = ('FileChooser',)


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
		super(RootChangerProxy, self).__init__(**kwargs)
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


class FileChooser(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super(FileChooser, self).__init__(**kwargs)

		self.options = PropDict()

		# sub-widgets
		layout = QVBoxLayout()
		self.setLayout(layout)

		self.edit = QLineEdit()
		layout.addWidget(self.edit)
		self.edit.textEdited.connect(self._onTextEdited)
		self.setFocusProxy(self.edit)

		self.view = QTreeView()
		layout.addWidget(self.view)
		self.view.activated.connect(self._onActivated)

		# models
		self.rootChanger = RootChangerProxy()

		fsModel = QFileSystemModel(self)
		self.setModel(fsModel)

		self.filter = QSortFilterProxyModel()
		self.filter.setSourceModel(self.rootChanger)
		self.view.setModel(self.filter)

		self.addCategory('filechooser')

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
	def _onTextEdited(self, txt):
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
				 for i in xrange(self.filter.rowCount(QModelIndex()))]
			names = [n[len(base):] for n in names]
			add = commonPrefix(names)

			cursor = self.edit.cursorPosition()
			self.edit.setText(self.edit.text()[:cursor] + add)
			self.edit.setSelection(cursor, len(self.edit.text()))

	@Slot(QModelIndex)
	def _onActivated(self, idx):
		idx = self.filter.mapToSource(idx)
		idx = self.rootChanger.mapToSource(idx)
		info = self.baseModel.fileInfo(idx)
		if info.isDir():
			return
		path = info.absoluteFilePath()
		buffers.openEditor(path)
