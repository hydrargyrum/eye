# this project is licensed under the WTFPLv2, see COPYING.txt for details

from .daemon import get_daemon, build_daemon
from .feed import feed_on_load, feed_on_save, feed_on_daemon_ready, feed_on_change
from .query import complete_on_char_added, do_completion, do_go_to


__all__ = ('set_enabled', 'do_completion', 'do_go_to')


def set_enabled(enabled=True):
	feed_on_load.enabled = enabled
	feed_on_save.enabled = enabled
	complete_on_char_added.enabled = enabled
	feed_on_daemon_ready.enabled = enabled
	feed_on_change.enabled = enabled

	d = get_daemon()
	if enabled:
		if not d:
			d = build_daemon()
		if not d.is_running():
			d.start()
	else:
		if d and d.is_running():
			d.stop()
