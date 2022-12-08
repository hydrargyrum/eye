# this project is licensed under the WTFPLv2, see COPYING.txt for details

from ..build import Builder
# TODO use 'base.py'


ERROR = 1
WARNING = 2


class CcBuilder(Builder):
	# works for gcc and clang
	errorRe = re.compile(r'(?P<file>[.*]+):(?P<line>\d+):(?P<col>\d+): error: (?P<msg>.*)')

	def __init__(self, **kwargs):
		super(CcBuilder, self).__init__(**kwargs)

		self.obj = None
		self.buf = []
		self.severity = None

	@Slot(str)
	def lineReceived(self, line):
		mtc = self.errorRe.match(line)
		if mtc:
			if self.obj:
				self.emitObj()
			self.obj = mtc.groupdict()
			self.buf = []
			self.severity = ERROR
		else:
			if self.obj:
				self.buf.append(line)

	def emitObj(self):
		self.obj['text'] = '\n'.join(self.buf)
		if self.severity == ERROR:
			self.error_printed.emit(self.obj)
