# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin to re-run startup scripts on edit.

If the plugin is enabled, when a startup script file is modified, it will be re-run.

It relies on :any:`eye.connector.deleteCreatedBy`:

* if the startup script had registered anything to the connector, they will be unregistered before
  the script is re-run.

* other things may not be kept track and thus may be run twice

TODO let scripts provide an `unregister` method so they can undo their effects.
"""

import logging
import os

from eye.app import qApp
from eye.connector import deleteCreatedBy
from eye.helpers.file_monitor import MonitorWithRename
from eye.qt import Slot

__all__ = ('setEnabled', 'registerStartupFiles')


LOGGER = logging.getLogger(__name__)

MONITOR = None


class ScriptMonitor(MonitorWithRename):
	def __init__(self, **kwargs):
		super(ScriptMonitor, self).__init__(**kwargs)
		self.fileChanged.connect(self._on_file_changed)

	@Slot(str)
	def _on_file_changed(self, path):
		LOGGER.info('%r has been modified, reloading', path)
		deleteCreatedBy(path)
		if os.path.exists(path):
			qApp().runScript(path)


def addScript(path):
	MONITOR.addPath(path)


def registerStartupFiles():
	"""Start monitoring startup scripts from user configuration."""
	for path in qApp().startupScripts():
		addScript(path)


def setEnabled(enabled):
	"""Enable/disable auto-reloading of startup scripts."""

	global MONITOR

	if enabled:
		if not MONITOR:
			MONITOR = ScriptMonitor()
		registerStartupFiles()
	else:
		MONITOR.deleteLater()
		MONITOR = None
