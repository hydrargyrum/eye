# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRegExp

from eye.app import qApp
from eye.connector import register_signal, disabled
from eye.consts import AbsolutePathRole
from eye.widgets.locationlist import LocationList

__all__ = ('set_enabled',)


@register_signal('builder', 'started')
@disabled
def on_build_start(builder):
	loclist = add_location_list(qApp().last_window, show=False)

	if loclist is None:
		return

	loclist.clear()
	loclist.setColumns(builder.columns())


@register_signal('builder', 'warning_printed')
@disabled
def on_build_warning(builder, info):
	add_item(builder, info, 'warning')


@register_signal('builder', 'error_printed')
@disabled
def on_build_error(builder, info):
	add_item(builder, info, 'error')


def add_location_list(win, show=True):
	if getattr(win, 'build_loclist', None) is None:
		win.build_loclist = LocationList()
		win.build_loclist.setWindowTitle(win.build_loclist.tr('Build results'))
		win.build_loclist.add_category('build_location_list')
		win.add_dockable(Qt.BottomDockWidgetArea, win.build_loclist)

	if show:
		win.build_loclist.show()

	return win.build_loclist


def add_item(builder, info, msg_type):
	loclist = add_location_list(qApp().last_window)
	loclist.addItem(info)


@register_signal('window', 'focused_buffer')
@disabled
def filter_on_focus(window, focused):
	loclist = getattr(window, 'build_loclist', None)
	if not loclist:
		return

	model = loclist.model()
	if not getattr(model, 'is_filter_on_focus', False):
		orig = model

		model = QSortFilterProxyModel()
		model.is_filter_on_focus = True
		loclist.setModel(model)
		model.setSourceModel(orig)
		model.setFilterRole(AbsolutePathRole)

	model.setFilterRegExp(QRegExp.escape(focused.path or ''))


def set_enabled(enabled=True):
	"""Enable or disable the plugin"""

	on_build_start.enabled = enabled
	on_build_warning.enabled = enabled
	on_build_error.enabled = enabled
