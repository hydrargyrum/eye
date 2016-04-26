# this project is licensed under the WTFPLv2, see COPYING.txt for details

import fnmatch
import logging
import os

from .base import registerPlugin, SearchPlugin
from ...pathutils import findAncestorContaining, findInAncestors


__all__ = ('ETagSearch',)


LOGGER = logging.getLogger(__name__)


class TagParser(object):
	START = 0
	SECTION_HEADER = 1
	SECTION_DATA = 2
	END = 3

	def __init__(self, file, db):
		super(TagParser, self).__init__()
		self.file = file
		self.db = db
		self.current_filename = None

	def parse(self):
		funcs = {
			self.START: self.parse_start,
			self.SECTION_HEADER: self.parse_header,
			self.SECTION_DATA: self.parse_data
		}

		state = TagParser.START
		while state != TagParser.END:
			state = funcs[state]()

	def parse_start(self):
		return self.SECTION_DATA

	def parse_header(self):
		line = self.file.readline().rstrip('\n')
		self.current_filename, size = line.rsplit(',', 1)
		return self.SECTION_DATA

	def parse_data(self):
		line = self.file.readline().rstrip('\n')
		if not line:
			return TagParser.END
		elif line == '\x0c':
			return self.SECTION_HEADER
		else:
			next = line
			definition, next = next.split('\x7f', 1)
			name, next = next.split('\x01', 1)
			linenumber, offset = next.split(',')

			self.db.add_tag(name, self.current_filename, linenumber, offset, definition)
			return TagParser.SECTION_DATA


class ETagDb(object):
	def __init__(self):
		super(ETagDb, self).__init__()
		self.db = {}

	def add_tag(self, name, filename, line, offset, definition):
		d = {'path': filename, 'line': line, 'tag_name': name, 'col': offset, 'definition': definition}
		occurences = self.db.setdefault(name, [])
		occurences.append(d)

	def find_tag(self, name):
		return self.db.get(name, [])

	def tags_matching(self, pattern):
		for tag in self.db:
			if fnmatch.fnmatch(tag, pattern):
				yield tag


def findTagDir(path):
	return findAncestorContaining(path, ['TAGS'])


def findTagFile(path):
	return findInAncestors(path, ['TAGS'])


@registerPlugin
class ETagSearch(SearchPlugin):
	id = 'etags'

	@classmethod
	def isAvailable(cls, path):
		return bool(findTagDir(path))

	@classmethod
	def searchRootPath(cls, path):
		return findTagDir(path)

	def _dbInDir(self, root):
		f = os.path.join(root, 'TAGS')
		db = ETagDb()
		parser = TagParser(f, db)
		parser.parse()
		return db
		# TODO cache tag db per project/dir?

	def search(self, root, pattern, **options):
		db = self._dbInDir(root)
		for match in db.find_tag(pattern):
			self.found.emit(match)
		self.finished.emit()
