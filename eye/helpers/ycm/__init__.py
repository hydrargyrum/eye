# this project is licensed under the WTFPLv2, see COPYING.txt for details

from .daemon import getDaemon
from .feed import feedOnLoad, feedOnSave, feedOnDaemonReady
from .query import completeOnCharAdded, doCompletion


__all__ = ('setEnabled', 'doCompletion')


def setEnabled(enabled=True):
	feedOnLoad.enabled = enabled
	feedOnSave.enabled = enabled
	completeOnCharAdded.enabled = enabled
	feedOnDaemonReady.enabled = enabled

	if enabled:
		if not getDaemon().isRunning():
			getDaemon().start()
	else:
		if getDaemon().isRunning():
			getDaemon().stop()
