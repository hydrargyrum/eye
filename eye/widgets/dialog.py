# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel

from .helpers import CategoryMixin

__all__ = ('Dialog', 'openDialog')


class Dialog(QDialog, CategoryMixin):
	def __init__(self, **kwargs):
		super(Dialog, self).__init__(**kwargs)

		layout = QVBoxLayout()
		self.setLayout(layout)

		self.widget = QLabel() # placeholder
		layout.addWidget(self.widget)

		self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		layout.addWidget(self.buttonBox)
		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.reject)

		self.addCategory('dialog')

	def setWidget(self, w):
		self.layout().replaceWidget(self.widget, w)
		self.widget = w
		# warning: don't use insertWidget, it has strange bugs


def openDialog(widget, parent=None, modal=True):
	d = Dialog(parent=parent)
	d.setModal(modal)
	d.setWidget(widget)
	d.show()
	widget.setFocus()
	return d
