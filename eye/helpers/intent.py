# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Action intents

Intents are generic actions triggered by plugins that are delegated to user configuration and other plugins.

An example is the "`openEditor`" intent. It be triggered by an "Open" dialog (:any:`eye.widgets.filechooser`) when a
file is selected by the user or by a :any:`eye.widgets.locationlist.LocationList` when a location is clicked.
Configuration scripts can register multiple intent callbacks for this intent type. They will be called in turn, until
one of the callbacks handles the intent, for example by opening a new tab (see :any:`eye.helpers.buffers`).
When the intent has been handled, callback processing for this intent stops.

Internally, intents are events and intent listeners are event filters.
"""

from functools import wraps
import logging

from PyQt5.QtCore import QCoreApplication, QEvent, QObject

from ..connector import registerEventFilter, CategoryMixin
from ..structs import PropDict


__all__ = ('IntentEvent', 'registerIntentListener', 'dummyListener', 'sendIntent',
           'defaultOpenEditor')


LOGGER = logging.getLogger(__name__)


class IntentEvent(QEvent):
	"""Intent
	"""

	Type = QEvent.registerEventType()

	def __init__(self, intent_type, **kwargs):
		super(IntentEvent, self).__init__(self.Type)

		self.intent_type = intent_type
		"""Type of the intent

		An intent has a type, which is a simple string, for example `"openEditor"` for the intent to open an
		editor with a particular file displayed.

		:type: str
		"""

		self.source = kwargs.pop('source', None)
		"""Object that sent the intent

		:type: QObject
		"""

		self.info = PropDict(**kwargs)
		"""Extra info about the intent

		This info is filled when the intent is sent (:any:`sendIntent`).

		:type: :any:`eye.structs.PropDict`
		"""

		self.result = None
		"""Result of the intent (if applicable)

		Optionally set by a handler with :any:`accept`.
		"""

		self.ignore()

	def accept(self, result=None):
		"""Accept the intent

		When an intent listener handles an `IntentEvent`, it should return True to avoid the intent being
		handled multiple times.
		Optionally, when the intent is handled, it can also be marked as accepted, with a result value. This
		result can then be retrieved by the object which sent the intent. The result is set in the
		:any:`result` attribute of the IntentEvent.

		For example, there could be an intent for querying user input, an object needing input would send the
		intent and would get back the input that one of the listeners produced, in the :any:`result`
		attribute.
		Or there could be an intent for creating a new tab, and a handler would create a different widget than
		the normal :any:`eye.widgets.editor.Editor`, and return it through this result.
		"""
		self.setAccepted(True)
		self.result = result

	def __repr__(self):
		return '<IntentEvent type=%r source=%r info=%r>' % (self.intent_type, self.source, self.info)


def registerIntentListener(intent_type, categories=None, stackoffset=0):
	"""Decorate a callback to be registered as an intent listener

	See :any:`dummyListener` for documentation of how the callback should be.

	:param intent_type: the type of the intent to listen to
	:type intent_type: str
	:param categories: If None, listen to intents from any object. Else, listen to intent emitted by objects
	                   matching the categories.
	"""
	if categories is None:
		categories = []

	def decorator(cb):
		@registerEventFilter(categories, [IntentEvent.Type], stackoffset=(1 + stackoffset))
		@wraps(cb)
		def wrapper(obj, ev):
			if getattr(cb, 'enabled', True) and ev.intent_type == intent_type:
				res = cb(obj, ev)
				if res and not ev.isAccepted():
					ev.accept(res)
				return bool(res)
			return False

		return cb
	return decorator


def sendIntent(source, intent_type, **kwargs):
	"""Send an intent

	If the intent was handled by a listener, it can have a result, see :any:`IntentEvent.result`.

	:param source: object sending the intent
	:param intent_type: type of the intent
	:type intent_type: str
	:param kwargs: extra info about the intent
	:returns: the result of the intent, if any
	"""
	if source is None:
		source = DefaultSender()

	event = IntentEvent(intent_type, source=source, **kwargs)
	QCoreApplication.sendEvent(source, event)
	if not event.isAccepted():
		LOGGER.info("intent %r for %r was not accepted (%r)", intent_type, source, kwargs)
	return event.result


def dummyListener(source, intent):
	"""Sample intent listener

	Intent listeners (see :any:`registerIntentListener`) should follow this function prototype.

	The function can handle `intent` and perform appropriate action if desired.

	If the function handled the intent, it should return True to mark the intent has having been already processed.
	Consequently, no more callbacks are called for this intent, to avoid it being handled multiple times.

	If the function handled the intent and returned a "truthy" value, but it did not call :any:`Intent.accept`,
	the Intent is automatically accepted and the value returned by the function is considered to be the `Intent`
	result (:any:`Intent.result`).

	If the function didn't handle the intent, it should return False, so other callbacks have a chance
	to handle it.

	:param source: object which sent the intent
	:type source: QObject
	:param intent:
	:type intent: IntentEvent
	:returns: True if the listener handled the intent, else False
	:rtype: bool
	"""

	return False


@registerIntentListener('openEditor')
def defaultOpenEditor(source, ev):
	from .buffers import openEditor

	editor = openEditor(ev.info.path, ev.info.get('loc'))
	return editor


class DefaultSender(QObject, CategoryMixin):
	def __init__(self):
		super(DefaultSender, self).__init__()
		self.addCategory('default_sender')
