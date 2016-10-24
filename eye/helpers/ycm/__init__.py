# this project is licensed under the WTFPLv2, see COPYING.txt for details

from .daemon import getDaemon, buildDaemon
from .feed import feedOnLoad, feedOnSave, feedOnDaemonReady, feedOnChange
from .query import completeOnCharAdded, doCompletion


__all__ = ('setEnabled', 'doCompletion')


def setEnabled(enabled=True):
	feedOnLoad.enabled = enabled
	feedOnSave.enabled = enabled
	completeOnCharAdded.enabled = enabled
	feedOnDaemonReady.enabled = enabled
	feedOnChange.enabled = enabled

	d = getDaemon()
	if enabled:
		if not d:
			d = buildDaemon()
		if not d.isRunning():
			d.start()
	else:
		if d and d.isRunning():
			d.stop()
