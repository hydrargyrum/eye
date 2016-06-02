# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

Signal = pyqtSignal
Slot = pyqtSlot

import fnmatch
import os

from configparser import ConfigParser, NoOptionError

from eye.connector import register_signal
from eye.helpers import buffers
from eye.helpers.build import PLUGINS

__all__ = ('menuBuildFill',)


def run(d):
	ed = buffers.current_buffer()

	plugin_cls = PLUGINS[d['type']]
	builder = plugin_cls()

	d = dict(d)
	d.pop('type')
	d.pop('name')
	d['file'] = ed.path

	builder.run_conf(**d)
	return builder


class Runner(QObject):
	@Slot()
	def launch(self):
		action = self.sender()
		d = action.data()
		builder = run(d)

		builder.setParent(self)
		builder.finished.connect(builder.deleteLater)


RUNNER = Runner()


def menuBuildFill(menu):
	menu.clear()

	ed = buffers.current_buffer()

	cfgpath = os.path.join(os.path.dirname(ed.path), '.eye-build')
	if not os.path.exists(cfgpath):
		return

	cfg = ConfigParser()
	cfg.read([cfgpath])

	for section in cfg.sections():
		d = dict(cfg.items(section))
		if 'name' not in d:
			continue

		d['dir'] = os.path.dirname(ed.path)

		action = menu.addAction(d['name'])
		action.setData(d)
		action.triggered.connect(RUNNER.launch)


"""
[compile]
name=Compile w/ debug
type=make
command=make debug

[flakes]
name=pyflakes
type=pyflakes
filter=*.py
command=pyflakes {file}
"""
