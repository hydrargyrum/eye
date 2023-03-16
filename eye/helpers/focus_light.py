# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Dim lightness of non-focused splits

To enable the plugin::

	>>> import eye.helpers.focus_light
	>>> eye.helpers.focus_light.setEnabled(True)
"""

from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QRubberBand

from eye.app import qApp
from eye.colorutils import QColorAlpha
from eye.connector import register_setup, register_event_filter, CategoryMixin, disabled
from eye.widgets.helpers import parent_tab_widget

__all__ = ('set_enabled', 'DimBand')


class DimBand(QRubberBand, CategoryMixin):
	"""Dimming widget

	This widget covers with a dimming transparent color.
	Instances have the "dimband" category set.
	"""

	def __init__(self, parent):
		super(DimBand, self).__init__(self.Rectangle, parent)
		self.dim_brush = QColorAlpha('#80808030')
		self.add_category('dimband')
		self.setStyle(None)

	def paintEvent(self, _):
		self.clearMask() # TODO is it safe to call that here?

		painter = QPainter(self)
		painter.fillRect(self.rect(), self.dim_brush)


def show_band(tw):
	if not hasattr(tw, 'dim_band'):
		tw.dim_band = DimBand(tw)
	tw.dim_band.setGeometry(tw.rect())
	tw.dim_band.show()


def hide_band(tw):
	if hasattr(tw, 'dim_band'):
		tw.dim_band.setParent(None)
		tw.dim_band.hide()
		del tw.dim_band


@disabled
def focus_changed(old, new):
	if not getattr(focus_changed, 'enabled', True):
		return

	oldtw = parent_tab_widget(old)
	newtw = parent_tab_widget(new)

	if oldtw and oldtw != newtw:
		show_band(oldtw)
	if newtw:
		hide_band(newtw)


qApp().focusChanged.connect(focus_changed)


@register_setup('tabwidget')
@disabled
def on_create(tw):
	if not tw.isAncestorOf(qApp().focusWidget()):
		show_band(tw)


@register_event_filter('tabwidget', [QEvent.Resize])
@disabled
def on_resize(tw, ev):
	band = getattr(tw, 'dim_band', None)
	if band:
		band.setGeometry(tw.rect())


def set_enabled(enabled=True):
	"""Enable or disable the plugin"""
	on_create.enabled = enabled
	on_resize.enabled = enabled
	focus_changed.enabled = enabled

# TODO do not dim when a minibuffer is opened
