# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for recording macros
"""

from ..connector import registerSignal, disabled


__all__ = ('setupRecording', 'recordAction')


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
