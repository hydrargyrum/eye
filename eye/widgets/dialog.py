# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel

from .helpers import CategoryMixin

__all__ = ('Dialog', 'openDialog')


class Dialog(QDialog, CategoryMixin):
	"""Basic dialog showing one widget and a set of buttons

	By default, the dialog has the "Ok" and "Cancel" buttons, which trigger the `accept` and `reject`
	slots. Instances of this class have the `'dialog'` category by default.
	"""

	def __init__(self, **kwargs):
		super(Dialog, self).__init__(**kwargs)

		layout = QVBoxLayout()
		self.setLayout(layout)

		self.widget = QLabel() # placeholder
		layout.addWidget(self.widget)

		self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		"""`QDialogButtonBox` instance of buttons to show on this dialog"""

		layout.addWidget(self.buttonBox)
		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.reject)

		self.addCategory('dialog')

	def setWidget(self, w):
		"""Set/replace the central widget shown in this dialog"""

		self.layout().replaceWidget(self.widget, w)
		self.widget = w
		# warning: don't use insertWidget, it has strange bugs


def openDialog(widget, parent=None, modal=True):
	"""Open a Dialog showing a widget

	Create and show a :any:`Dialog`. The dialog will contain `widget`.

	:param widget: the widget to show in the dialog
	:param parent: the parent of the dialog, if any
	:param modal: whether the dialog should be modal
	:returns: the new dialog
	:rtype: Dialog
	"""
	d = Dialog(parent=parent)
	d.setModal(modal)
	d.setWidget(widget)
	d.show()
	widget.setFocus()
	return d
