# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, QTimer, pyqtSignal as Signal, pyqtSlot as Slot, QElapsedTimer, QUrl
from PyQt5.QtWidgets import QWidget, QLineEdit, QVBoxLayout

from PyQt5.QtWebKitWidgets import QWebView

from ..qt import Slot
from ..connector import CategoryMixin


class BasicView(QWidget, CategoryMixin):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setLayout(QVBoxLayout())

		self.urlbar = QLineEdit()
		self.urlbar.returnPressed.connect(self._return_pressed)

		self.web = QWebView()
		self.web.urlChanged.connect(self._url_changed)

		self.layout().addWidget(self.urlbar)
		self.layout().addWidget(self.web)

		self.setWindowTitle(self.tr('Web view'))

		self.add_category('webview')

	@Slot()
	def _return_pressed(self):
		self.web.load(QUrl(self.urlbar.text()))

	@Slot(QUrl)
	def _url_changed(self, url):
		self.urlbar.setText(url.toString())

