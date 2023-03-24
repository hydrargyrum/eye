# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye.utils import ignore_exceptions
from eye.app import qApp


@ignore_exceptions(None)
def show_quick_message(msg, timeout=0):
	win = qApp().last_window
	win.statusBar().showMessage(msg, timeout)
