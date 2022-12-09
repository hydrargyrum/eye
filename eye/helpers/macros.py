# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for recording macros
"""

from eye.connector import registerSignal, disabled

__all__ = ('setEnabled', 'setupRecording', 'recordAction', 'replayRecordedMacro')


@registerSignal(['editor'], 'macroRecordStarted')
@disabled
def setupRecording(ed):
	"""Create an empty array for recorded macro actions"""
	ed.actionsRecorded = []


@registerSignal(['editor'], 'actionRecorded')
@disabled
def recordAction(ed, action):
	"""Record a macro action in an `editor.actionsRecorded`"""
	ed.actionsRecorded.append(action)


def replayRecordedMacro(ed):
	"""Replay the last recorded macro.

	Actions are replayed in an undo-group.
	"""
	if not getattr(ed, 'actionsRecorded', None):
		return

	with ed.undoGroup():
		for action in ed.actionsRecorded:
			ed.replayMacroAction(action)


def setEnabled(enabled):
	setupRecording.enabled = enabled
	recordAction.enabled = enabled
