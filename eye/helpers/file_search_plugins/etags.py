# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
import fnmatch
import logging
import os

from PyQt5.QtCore import QTimer, QElapsedTimer

from eye.helpers.confcache import ConfCache
from eye.helpers.file_search_plugins.base import register_plugin, SearchPlugin
from eye.pathutils import find_ancestor_containing, find_in_ancestors
from eye.qt import Slot

__all__ = ('ETagsSearch',)


LOGGER = logging.getLogger(__name__)


class ETagsParser:
	START = 0
	SECTION_HEADER = 1
	SECTION_DATA = 2
	END = 3

	def __init__(self, path):
		super().__init__()
		self.path = path

		self.state = None
		self.fd = None
		self.current_filename = None

	def parse(self):
		funcs = {
			self.START: self.parse_start,
			self.SECTION_HEADER: self.parse_header,
			self.SECTION_DATA: self.parse_data
		}

		LOGGER.debug('parsing tags database %r', self.path)

		with open(self.path, 'rb') as self.fd:
			self.state = self.START
			while self.state != self.END:
				res = funcs[self.state]()
				if res is not None:
					yield res

	def parse_start(self):
		self.state = self.SECTION_DATA

	def parse_header(self):
		line = self.fd.readline().rstrip(b'\n')
		self.current_filename, size = line.rsplit(b',', 1)
		self.current_filename = self.current_filename.decode('utf-8')
		self.current_filename = os.path.join(os.path.dirname(self.path), self.current_filename)
		self.state = self.SECTION_DATA

	def parse_data(self):
		line = self.fd.readline().rstrip(b'\n')
		if not line:
			self.state = self.END
		elif line == b'\x0c':
			self.state = self.SECTION_HEADER
		else:
			next = line
			definition, next = next.split(b'\x7f', 1)
			name, next = next.split(b'\x01', 1)
			linenumber, offset = next.split(b',')

			linenumber = int(linenumber)
			#definition = definition.decode('utf-8')
			try:
				name = name.decode('utf-8')
			except UnicodeDecodeError:
				name = name.decode('latin-1')

			self.state = self.SECTION_DATA
			return {
				'tag': name,
				'path': self.current_filename,
				'line': linenumber,
			}


class TagDb:
	def __init__(self):
		super().__init__()
		self.db = {}

	def add_tag(self, d):
		LOGGER.debug('adding tag %r', d)

		occurences = self.db.setdefault(d['tag'], [])
		occurences.append(d)

	def find_tag(self, name):
		return self.db.get(name, [])

	def tags_matching(self, pattern):
		for tag in self.db:
			if fnmatch.fnmatch(tag, pattern):
				yield tag


def find_tag_dir(path):
	return find_ancestor_containing(path, ['TAGS'])


def find_tag_file(path):
	return find_in_ancestors(path, ['TAGS'])


class DbCache(ConfCache):
	pass


CACHE = DbCache(weak=False)


@register_plugin
class ETagsSearch(SearchPlugin):
	id = 'etags'

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.db = None
		self.parser = None
		self.parsing = None
		self.request = None

		self.timer = QTimer(self)
		self.timer.timeout.connect(self._batch_load)

	@classmethod
	def is_available(cls, path):
		return bool(find_tag_dir(path))

	@classmethod
	def search_root_path(cls, path):
		return find_tag_dir(path)

	@contextmanager
	def safe_batch(self):
		try:
			yield
		except:
			self.timer.stop()
			self.finished.emit(0)
			raise

	def _load_db(self, dbpath):
		self.db = CACHE.get(dbpath)
		if self.db:
			self._search_in_db(self.request)
			return

		LOGGER.debug('loading db %r because it is not in cache', dbpath)
		self.db = TagDb()
		self.parser = ETagsParser(dbpath)
		self.parsing = self.parser.parse()
		self.timer.start()

	@Slot()
	def _batch_load(self):
		with self.safe_batch():
			duration = QElapsedTimer()
			duration.start()

			for taginfo in self.parsing:
				self.db.add_tag(taginfo)

				if duration.hasExpired(10):
					return

			CACHE.add_conf(self.parser.path, self.db)
			self.timer.stop()

			LOGGER.debug('db %r has finished loading', self.parser.path)
			self._search_in_db(self.request)

	def _search_in_db(self, pattern: str):
		for match in self.db.find_tag(pattern):
			self.found.emit(match)
		self.finished.emit(0)

	def search(self, root, pattern: str, **options):
		self.request = pattern
		self.started.emit()

		with self.safe_batch():
			dbpath = find_tag_file(root)
			if not dbpath:
				self.finished.emit(0)
				return

			self._load_db(dbpath)
