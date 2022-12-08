from eye.connector import category_objects
from eye.utils import ignore_exceptions


@ignore_exceptions(None)
def show_quick_message(msg, timeout=0):
	win = category_objects('window')[0]
	win.statusBar().showMessage(msg, timeout)
