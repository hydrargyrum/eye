# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QRegExp

from ..connector import registerSignal, disabled
from ..app import qApp
from ..consts import AbsolutePathRole
from ..widgets.locationlist import LocationList


__all__ = ('setEnabled',)


@registerSignal('builder', 'started')
@disabled
def onBuildStart(builder):
	loclist = addLocationList(qApp().lastWindow, show=False)

	if loclist is None:
		return

	loclist.clear()
	loclist.setColumns(builder.columns())


@registerSignal('builder', 'warningPrinted')
@disabled
def onBuildWarning(builder, info):
	addItem(builder, info, 'warning')


@registerSignal('builder', 'errorPrinted')
@disabled
def onBuildError(builder, info):
	addItem(builder, info, 'error')


def addLocationList(win, show=True):
	if getattr(win, 'build_loclist', None) is None:
		win.build_loclist = LocationList()
		win.build_loclist.setWindowTitle(win.build_loclist.tr('Build results'))
		win.build_loclist.addCategory('build_location_list')
		win.addDockable(Qt.BottomDockWidgetArea, win.build_loclist)

	if show:
		win.build_loclist.show()

	return win.build_loclist


def addItem(builder, info, msg_type):
	loclist = addLocationList(qApp().lastWindow)
	loclist.addItem(info)


@registerSignal('window', 'focusedBuffer')
@disabled
def filterOnFocus(window, focused):
	loclist = getattr(window, 'build_loclist', None)
	if not loclist:
		return

	model = loclist.model()
	if not getattr(model, 'isFilterOnFocus', False):
		orig = model

		model = QSortFilterProxyModel()
		model.isFilterOnFocus = True
		loclist.setModel(model)
		model.setSourceModel(orig)
		model.setFilterRole(AbsolutePathRole)

	model.setFilterRegExp(QRegExp.escape(focused.path or ''))


def setEnabled(enabled=True):
	"""Enable or disable the plugin"""

	onBuildStart.enabled = enabled
	onBuildWarning.enabled = enabled
	onBuildError.enabled = enabled
