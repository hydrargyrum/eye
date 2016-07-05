# this project is licensed under the WTFPLv2, see COPYING.txt for details

from logging import getLogger

from PyQt5.QtWidgets import QRubberBand


LOGGER = getLogger(__name__)


class BandMixin(object):
	def __init__(self, **kwargs):
		super(BandMixin, self).__init__(**kwargs)
		self.__band = None

	def showBand(self, *geom):
		if not self.__band:
			self.__band = QRubberBand(QRubberBand.Rectangle, parent=self)
		self.__band.setGeometry(*geom)
		self.__band.show()

	def hideBand(self):
		if self.__band:
			self.__band.hide()
			self.__band.setParent(None)
			self.__band = None


class DropAreaMixin(BandMixin):
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
		self.showBand(self.rect())

	def dragLeaveEvent(self, ev):
		if not self.__hasSignal():
			return super(DropAreaMixin, self).dragLeaveEvent(ev)

		self.hideBand()

	def dropEvent(self, ev):
		if not self.__hasSignal():
			return super(DropAreaMixin, self).dropEvent(ev)

		self.hideBand()

		for url in ev.mimeData().urls():
			if url.isLocalFile():
				path = url.toLocalFile()
				LOGGER.info('file dropped: %r', path)
				self.fileDropped.emit(path)
