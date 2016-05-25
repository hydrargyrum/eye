Configuration
=============

EYE's config dir is `$XDG_CONFIG_HOME/eyeditor`, which maps to `~/.config/eyeditor` by default.

In the config dir, the `startup` dir should contains Python scripts. Those scripts are the user configuration.
They are run when EYE is started and use the EYE API to enable/configure plugins, set keyboard shortcuts, change
colors styles, register callbacks to perform when some actions happen. The scripts are run in alphabetical order.

Some plugins delegate some configuration to specific file formats, for example, the :doc:`eye.helpers.keys` plugin
can load INI files for configuring keyboard shortcuts in EYE. Nothing prevents plugins to provide dialog-based
configuration helpers.

Plugins
-------

In EYE, plugins are regular Python modules which can be imported. All plugins are submodules of `eye.helpers`.

However, just importing a plugin's module doesn't enable its features straight away.
Some plugins provide ready-to-enable feature, while some just contain building blocks to help writing a more
customized feature.

The simpler plugins register callbacks to perform when some action is performed, but just don't enable them by
default. But those can be enabled by just setting a boolean, as can be seen in the lexer plugin example below.

Examples
--------

Enabling a basic plugin
'''''''''''''''''''''''

The default EYE configuration is very plain. Even syntax coloring isn't enabled by default.
The :doc:`eye.helpers.lexer` plugin provides a function `autoLexer` which sets the appropriate lexer for an editor
widget. Furthermore, this function is registered to run automatically when a file is loaded or saved.

Here's a very brief extract of `eye.helpers.lexer`::

	from ..connector import registerSignal, disabled

	@registerSignal(['editor'], 'fileOpened')
	@registerSignal(['editor'], 'fileSaved')
	@disabled
	def autoLexer(editor, path=None):

Without going in depth (see :doc:`eye.connector` for that), what this does is:

* the `autoLexer` helper is defined
* this helper is "decorated" to register it in various ways
* it's registered to run when the `fileOpened` action or the `fileSaved` action is done in an editor widget
* it's disabled by default

To have syntax coloring, one could create a `syntax_coloring.py` file into the config dir
`~/.config/eyeditor/startup`, containing the following::

	import eye.helpers.lexer
	
	eye.helpers.lexer.autoLexer.enabled = True

Misc configuration
''''''''''''''''''

Here, we will see a way to configure the font of editor widgets. We can create `~/.config/eyeditor/startup/style.py`
with this content::

	from eye.connector import defaultEditorConfig
	from PyQt5.QtGui import QFont

	@defaultEditorConfig
	def font_setting(editor):
		editor.setFont(QFont('monospace'))

The `@defaultEditorConfig` decorator registers the function to be run for every new editor widget creation, which is
a good opportunity to customize the editor. Our function will receive the editor as parameter, and we can use all
methods of the editor widget (see :any:`eye.widgets.editor.Editor`), among which the `setFont` method.

Another way to configure all editor widgets' styles is to use the :doc:`eye.helpers.lexercolor` plugin.
This plugin allows to load INI theme files, which can set colors and fonts for editor widgets.

It may be less flexible than writing code for completely customize styles depending on many factors, but most often
it won't be necessary to customize further than what this plugin does, since it allows to customize syntax coloring
by language.

import *
--------

Even though using `import *` is discouraged in released code, personal configuration files are not released code, and
using `import *` in this context could simplify writing configuration files::

	# instead of:
	# from eye.connector import registerSignal, registerShortcut
	# from eye.helpers.buffers import openEditor

	# just:
	from eye.connector import *
	from eye.helpers.buffers import *

EYE plugins generally keep a small set of exported symbols in `__all__`, and configuration files can be split, and
thus can be small, so namespace pollution is less a problem. Readability also suffers less.

.. TODO tutorial?
.. TODO registering shortcuts, callbacks
.. TODO import *

