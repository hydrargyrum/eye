# this project is licensed under the WTFPLv2, see COPYING.txt for details

from functools import wraps
import logging
import os

from PyQt5.QtCore import QObject, Q_CLASSINFO
from PyQt5.QtDBus import QDBusConnection, QDBusVariant, QDBusMessage

from eye import pathutils
from eye.connector import CategoryMixin
from eye.helpers.intent import register_intent_listener, send_intent
from eye.qt import Slot

__all__ = ('register_remote_request', 'on_request_open', 'SimpleHandler')


LOGGER = logging.getLogger(__name__)


ROOT_OBJ = None
BUS = None


class SimpleHandler(QObject, CategoryMixin):
	Q_CLASSINFO('D-Bus Interface', 're.indigo.eye')

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.add_category('remote_control')

	@Slot(str, result=QDBusVariant)
	@Slot(str, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      QDBusVariant, result=QDBusVariant)
	def request(self, request_type, *args):
		args = tuple(arg.variant() if isinstance(arg, QDBusVariant) else arg for arg in args)

		LOGGER.debug('received request %r%r', request_type, args)
		result = send_intent(self, 'remote_request', request_type=request_type, args=args)
		if result is None:
			result = False

		LOGGER.debug('replying %r to request %r%r', result, request_type, args)
		return QDBusVariant(result)


def register_remote_request(request_type, stackoffset=0):
	def decorator(func):
		@register_intent_listener('remote_request', categories='remote_control', stackoffset=(1 + stackoffset))
		@wraps(func)
		def wrapper(remote, intent):
			if intent.info.request_type == request_type and getattr(func, 'enabled', True):
				result = func(intent.info.args)
				intent.accept(result)
				return True
			return False

		return func
	return decorator


def create_server():
	global BUS, ROOT_OBJ

	ROOT_OBJ = SimpleHandler()

	BUS = QDBusConnection.sessionBus()
	BUS.registerService('re.indigo.eye')
	BUS.registerObject('/', ROOT_OBJ, QDBusConnection.ExportAllContents)


def send_request(req, *args):
	global BUS

	LOGGER.debug('sending request %r%r', req, args)

	method_args = [req]
	method_args.extend(args)

	msg = QDBusMessage.createMethodCall('re.indigo.eye', '/', 're.indigo.eye', 'request')
	msg.setArguments(method_args)

	BUS = QDBusConnection.sessionBus()
	reply = BUS.call(msg)

	if reply.type() == QDBusMessage.ErrorMessage:
		raise ValueError(reply.errorMessage())
	return list(reply.arguments())


@register_remote_request('ping')
def on_request_ping(args):
	return True


@register_remote_request('open')
def on_request_open(args):
	path, row, col = pathutils.parse_filename(args[0])
	path = os.path.abspath(path)
	if row is None:
		loc = None
	else:
		loc = (row, col)

	send_intent(ROOT_OBJ, 'open_editor', path=path, loc=loc, reason='remote')
