#!/usr/bin/env python3
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import argparse
import glob
import logging
import os
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow

from eye import pathutils, connector
from eye.qt import Slot

__all__ = ('App', 'qApp', 'main')


def qApp():
	return QApplication.instance()


class App(QApplication):
	"""Application"""

	def __init__(self, argv):
		super().__init__(argv)
		self.setApplicationName('eye')
		self.setApplicationDisplayName('eye')

		self.logger = logging.getLogger()

		self.args = None

		self.last_window = None
		self.focusChanged.connect(self._app_focus_changed)

		self.setWindowIcon(QIcon(pathutils.data_path('eye.png')))

	def init_ui(self):
		from eye.widgets import window

		win = window.Window()
		win.create_default_menu_bar()
		win.quit_requested.connect(self.quit)
		return win

	def startup_scripts(self):
		"""Get list of startup script files

		These are the script present at the moment, not the scripts that were run when the app started.
		"""
		files = glob.glob(os.path.join(pathutils.get_config_path('startup'), '*.py'))
		files.sort()
		return files

	def script_dict(self):
		"""Build a env suitable for running conf scripts.

		The built dict will contain `'qApp'` key pointing to this App instance.
		"""
		return {'qApp': QApplication.instance()}

	def run_start_scripts(self):
		for f in self.startup_scripts():
			self.run_script(f)

	def run_script(self, path):
		"""Run a config script in this app

		The script will be run with the variables returned by :any:`script_dict`.
		Exceptions thrown  by the script are catched and logged.
		"""
		self.logger.debug('execing script %s', path)
		try:
			execfile(path, self.script_dict())
		except Exception:
			self.logger.error('cannot execute startup script %r', path, exc_info=True)

	def run(self):
		"""Run app until exit

		Create and show interface, run config script, handle command-line args and run.
		Does not return until app is quit.
		"""

		self.parse_arguments()
		self.init_logging()

		if self.args.remote and self.process_remote():
			return 0

		welcome = False
		if not self.args.no_config:
			if not self.startup_scripts():
				from eye.helpers.welcome import ask_to_copy, open_welcome_text

				welcome = ask_to_copy()

			self.run_start_scripts()

		win = self.init_ui()
		win.show()
		self.open_command_line_files()

		if welcome:
			open_welcome_text()

		return self.exec_()

	def parse_arguments(self):
		parser = argparse.ArgumentParser()
		parser.add_argument('files', metavar='FILE', nargs='*')
		parser.add_argument('--debug', action='store_true', default=False)
		parser.add_argument('--debug-only', action='append', default=[])
		parser.add_argument('--no-config', action='store_true', default=False)
		parser.add_argument('--remote', action='store_true', default=False)

		argv = self.arguments()[1:]
		self.args = parser.parse_args(argv)

	def init_logging(self):
		if self.args.debug:
			self.logger.handlers[0].setLevel(logging.DEBUG)
		for logger_name in self.args.debug_only:
			handler = logging.StreamHandler()
			handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
			handler.setLevel(logging.DEBUG)

			logger = logging.getLogger(logger_name)
			logger.addHandler(handler)

	def process_remote(self):
		from eye.helpers import remote_control

		try:
			remote_control.send_request('ping')
		except ValueError:
			remote_control.create_server()
			return False

		try:
			path, row = pathutils.vim_filename_arg(self.args.files)
		except TypeError:
			pass
		else:
			path = os.path.abspath(path)
			remote_control.send_request('open', "%s:%s" % (path, row))
			return True

		for path in self.args.files:
			path = os.path.abspath(path)
			remote_control.send_request('open', path)
		return True

	def open_command_line_files(self):
		if not self.args.files:
			return

		win = connector.category_objects('window')[0]

		from eye.helpers.intent import send_intent

		try:
			path, row = pathutils.vim_filename_arg(self.args.files)
		except TypeError:
			pass
		else:
			send_intent(win, 'open_editor', path=path, loc=(row,), reason='commandline')
			# only 1 filename in this case
			return

		for name in self.args.files:
			path, row, col = pathutils.parse_filename(name)
			path = os.path.abspath(path)

			loc = None
			if row and col:
				loc = (row, col)
			elif row:
				loc = (row,)
			send_intent(win, 'open_editor', path=path, loc=loc, reason='commandline')

	@Slot('QWidget*', 'QWidget*')
	def _app_focus_changed(self, old, new):
		while new and not new.isWindow():
			new = new.parentWidget()
		if not new or not isinstance(new, QMainWindow):
			# exclude dialogs
			return
		self.last_window = new


def setup_logging():
	logging.basicConfig()
	root = logging.getLogger()
	root.setLevel(logging.DEBUG)
	root.handlers[0].setLevel(logging.WARNING)


def execfile(path, globals):
	"""Exec Python `file` with `globals` as in Python 2"""
	with open(path) as fd:
		src = fd.read()
	code = compile(src, path, 'exec')
	exec(code, globals)  # pylint: disable=exec-used


def main():
	"""Run eye app"""

	# if the default excepthook is used, PyQt 5.5 *aborts* the app when an unhandled exception occurs
	# see http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
	# as this behaviour is questionable, we restore the old one

	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	setup_logging()

	app = App(sys.argv)
	return app.run()


if __name__ == '__main__':
	sys.exit(main())
