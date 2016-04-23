# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtWidgets import QRubberBand

from logging import getLogger


LOGGER = getLogger(__name__)


class DropAreaMixin(object):
	# fileDropped = Signal(str)

	def __init__(self, **kwargs):
		super(DropAreaMixin, self).__init__(**kwargs)
		self.bandDrop = None

	def __hasSignal(self):
		return hasattr(self, 'fileDropped')

	def dragEnterEvent(self, ev):
		if not ev.mimeData().hasUrls() or not self.__hasSignal():
			return super(DropAreaMixin, self).dragEnterEvent(ev)

		ev.acceptProposedAction()
		self.bandDrop = QRubberBand(QRubberBand.Rectangle, parent=self)
		self.bandDrop.setGeometry(0, 0, self.width(), self.height())
		self.bandDrop.show()

	def hideBandDrop(self):
		if self.bandDrop:
			self.bandDrop.hide()
			self.bandDrop.setParent(None)
			self.bandDrop = None

	def dragLeaveEvent(self, ev):
		if not self.__hasSignal():
			return super(DropAreaMixin, self).dragLeaveEvent(ev)

		self.hideBandDrop()

	def dropEvent(self, ev):
		if not self.__hasSignal():
			return super(DropAreaMixin, self).dropEvent(ev)

		self.hideBandDrop()

		for url in ev.mimeData().urls():
			if url.isLocalFile():
				path = url.toLocalFile()
				LOGGER.info('file dropped: %r', path)
				self.fileDropped.emit(path)
