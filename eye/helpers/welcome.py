# this project is licensed under the WTFPLv2, see COPYING.txt for details

import shutil

from PyQt5.QtWidgets import QMessageBox, QApplication
from eye.pathutils import dataPath, getConfigPath
from eye.connector import categoryObjects


def copy_sample_config():
	shutil.copy(dataPath('sample_conf/keyboard.ini'), getConfigPath())
	shutil.copy(dataPath('sample_conf/sample.py'), getConfigPath('startup'))


def ask_to_copy():
	app = QApplication.instance()

	reply = QMessageBox.question(None,
		app.tr('Welcome to EYE!'),
		app.tr("You have no EYE configuration, do you want to use with a sample configuration?"),
		QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
	)
	if reply == QMessageBox.Yes:
		copy_sample_config()
		return True


SAMPLE_TEXT = """\
Welcome to EYE!
===============

EYE is a Python text editor for developers. Its configuration files are Python files.

A sample configuration has been written to $XDG_CONFIG_HOME/eyeditor/startup/sample.py
(Usually, $XDG_CONFIG_HOME is ~/.config)

Read documentation at <https://eye.readthedocs.io/>.
"""


def open_welcome_text():
	window = categoryObjects('window')[0]
	editor = window.bufferNew()

	editor.setText(editor.tr(SAMPLE_TEXT))

	editor.setModified(False)
	editor.setReadOnly(True)
