
from ..connector import registerSignal, disabled

__all__ = ('setupRecording', 'recordAction')

@registerSignal(['editor'], 'macroRecordStarted')
def setupRecording(ed):
	ed.actionsRecorded = []

@registerSignal(['editor'], 'actionRecorded')
def recordAction(ed, action):
	ed.actionsRecorded.append(action)
