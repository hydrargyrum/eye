#!/usr/bin/env python3
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import glob

from setuptools import setup


if __name__ == '__main__':
	setup(
		data_files=[
			('share/eye/colorschemes', glob.glob('data/colorschemes/*')),
			('share/eye/sample_conf', glob.glob('data/sample_conf/*')),
			('share/applications', ['data/eye.desktop']),
			('share/icons/hicolor/256x256/apps', ['data/eye.png']),
		],
	)
