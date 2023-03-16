# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for recording macros
"""

from eye.connector import register_signal, disabled

__all__ = ('set_enabled', 'setup_recording', 'record_action', 'replay_recorded_macro')


@register_signal(['editor'], 'macro_record_started')
@disabled
def setup_recording(ed):
	"""Create an empty array for recorded macro actions"""
	ed.actions_recorded = []


@register_signal(['editor'], 'action_recorded')
@disabled
def record_action(ed, action):
	"""Record a macro action in an `editor.actions_recorded`"""
	ed.actions_recorded.append(action)


def replay_recorded_macro(ed):
	"""Replay the last recorded macro.

	Actions are replayed in an undo-group.
	"""
	if not getattr(ed, 'actions_recorded', None):
		return

	with ed.undo_group():
		for action in ed.actions_recorded:
			ed.replay_macro_action(action)


def set_enabled(enabled):
	setup_recording.enabled = enabled
	record_action.enabled = enabled
