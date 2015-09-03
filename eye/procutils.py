# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os

def findCommand(cmd):
	for elem in os.getenv('PATH').split(os.pathsep):
		path = os.path.join(elem, cmd)
		if os.path.isfile(path):
			return path

