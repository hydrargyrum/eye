# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Dim lightness of non-focused splits

To enable the plugin::

	>>> import eye.helpers.focus_light
	>>> eye.helpers.focus_light.setEnabled(True)
"""

from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QRubberBand

from eye.connector import registerSetup, registerEventFilter, CategoryMixin, disabled
from eye.app import qApp
from eye.colorutils import QColorAlpha


__all__ = ('setEnabled', 'DimBand')


def getTabWidget(w):
	if hasattr(w, 'parentTabBar'):
		return w.parentTabBar()


class DimBand(QRubberBand, CategoryMixin):
	"""Dimming widget

	This widget covers with a dimming transparent color.
	Instances have the "dimband" category set.
	"""

	def __init__(self, parent):
		super(QRubberBand, self).__init__(self.Rectangle, parent)
		self.dimBrush = QColorAlpha('#80808030')
		self.addCategory('dimband')
		self.setStyle(None)

	def paintEvent(self, ev):
		self.clearMask() # TODO is it safe to call that here?

		painter = QPainter(self)
		painter.fillRect(self.rect(), self.dimBrush)


def showBand(tw):
	if not hasattr(tw, 'dimBand'):
		tw.dimBand = DimBand(tw)
	tw.dimBand.setGeometry(tw.rect())
	tw.dimBand.show()


def hideBand(tw):
	if hasattr(tw, 'dimBand'):
		tw.dimBand.setParent(None)
		tw.dimBand.hide()
		del tw.dimBand


@disabled
def focusChanged(old, new):
	if not getattr(focusChanged, 'enabled', True):
		return

	oldtw = getTabWidget(old)
	newtw = getTabWidget(new)

	if oldtw and oldtw != newtw:
		showBand(oldtw)
	if newtw:
		hideBand(newtw)


qApp().focusChanged.connect(focusChanged)


@registerSetup('tabwidget')
@disabled
def onCreate(tw):
	if not tw.isAncestorOf(qApp().focusWidget()):
		showBand(tw)


@registerEventFilter('tabwidget', [QEvent.Resize])
@disabled
def onResize(tw, ev):
	band = getattr(tw, 'dimBand', None)
	if band:
		band.setGeometry(tw.rect())


def setEnabled(enabled=True):
	"""Enable or disable the plugin"""
	onCreate.enabled = enabled
	onResize.enabled = enabled
	focusChanged.enabled = enabled

# TODO do not dim when a minibuffer is opened
