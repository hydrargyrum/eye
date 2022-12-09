# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye.connector import registerSignal, disabled

# http://nickgravgaard.com/elastic-tabstops/

# Python port of nickgravgaard's ElasticTabstopsForScintilla code.
# https://github.com/nickgravgaard/ElasticTabstopsForScintilla/blob/645e76810ac7aa2bfdaee21aa72f2cefefa9f4c7/ElasticTabstopsEdit.cpp
# Original C++ code is licensed under MIT license.

class Tabstop:
	text_width_pix: int = 0
	widest_width_pix: tuple = ()
	ends_in_tab: bool = False


class Line:
	num_tabs: int = 0


BACKWARDS = 0
FORWARDS = 1

MINIMUM_WIDTH_DEFAULT = 32
PADDING_WIDTH_DEFAULT = 12

tab_width_minimum = MINIMUM_WIDTH_DEFAULT
tab_width_padding = PADDING_WIDTH_DEFAULT


def get_line_start(edit, pos: int) -> int:
	line = edit.lineIndexFromPosition(pos)[0]
	return edit.positionFromLineIndex(line, 0)


def get_char_at(edit, pos: int):
	return chr(edit.SendScintilla(edit.SCI_GETCHARAT, pos))


def get_line_end(edit, pos: int) -> int:
	line = edit.lineIndexFromPosition(pos)[0]
	return edit.SendScintilla(edit.SCI_GETLINEENDPOSITION, line)


def is_line_end(edit, pos: int) -> bool:
	end_pos = get_line_end(edit, pos)
	return pos == end_pos


def get_text_width(edit, start: int, end: int) -> int:
	text = edit.text(start, end)
	style = edit.SendScintilla(edit.SCI_GETSTYLEAT, start)
	return edit.SendScintilla(edit.SCI_TEXTWIDTH, style, text.encode('utf-8'))


def calc_tab_width(text_width_in_tab: int) -> int:
	if text_width_in_tab < tab_width_minimum:
		text_width_in_tab = tab_width_minimum
	return text_width_in_tab + tab_width_padding


def change_line(edit, location: list, which_dir: int) -> bool:
	line = edit.SendScintilla(edit.SCI_LINEFROMPOSITION, location[0])

	if which_dir == FORWARDS:
		location[0] = edit.SendScintilla(edit.SCI_POSITIONFROMLINE, line + 1)
	else:
		if line <= 0:
			return False
		location[0] = edit.SendScintilla(edit.SCI_POSITIONFROMLINE, line - 1)
	return location[0] >= 0


def get_block_boundary(edit, location: list, which_dir: int) -> int:
	current_pos = 0
	max_tabs = 0
	orig_line = True

	location[0] = get_line_start(edit, location[0])
	while True:
		tabs_on_line = 0

		current_pos = location[0]
		current_char = get_char_at(edit, current_pos)
		current_char_ends_line = is_line_end(edit, current_pos)

		while current_char != '\x00' and not current_char_ends_line:
			if current_char == '\t':
				tabs_on_line += 1
				if tabs_on_line > max_tabs:
					max_tabs = tabs_on_line
			current_pos = edit.SendScintilla(edit.SCI_POSITIONAFTER, current_pos)
			current_char = get_char_at(edit, current_pos)
			current_char_ends_line = is_line_end(edit, current_pos)

		if tabs_on_line == 0 and not orig_line:
			return max_tabs

		orig_line = False

		if not change_line(edit, location, which_dir):
			break

	return max_tabs


def get_nof_tabs_between(edit, start: int, end: int) -> int:
	current_pos = [get_line_start(edit, start)]
	max_tabs = 0

	while True:
		current_char = get_char_at(edit, current_pos[0])
		current_char_ends_line = is_line_end(edit, current_pos[0])

		tabs_on_line = 0
		while current_char != '\x00' and not current_char_ends_line:
			if current_char == '\t':
				tabs_on_line += 1
				if tabs_on_line > max_tabs:
					max_tabs = tabs_on_line

			current_pos = [edit.SendScintilla(edit.SCI_POSITIONAFTER, current_pos[0])]
			current_char = get_char_at(edit, current_pos[0])
			current_char_ends_line = is_line_end(edit, current_pos[0])

		if not (change_line(edit, current_pos, FORWARDS) and current_pos[0] < end):
			break

	return max_tabs


def stretch_tabstops(edit, block_start_linenum: int, block_nof_lines: int, max_tabs: int) -> None:
	lines = [Line() for _ in range(block_nof_lines)]

	grid = [
		[
			Tabstop()
			for _ in range(max_tabs)
		]
		for _ in range(block_nof_lines)
	]

	# get width of text in cells
	for l in range(block_nof_lines):  # for each line
		text_width_in_tab = 0
		current_line_num = block_start_linenum + l
		current_tab_num = 0
		cell_empty = True

		current_pos = edit.positionFromLineIndex(current_line_num, 0)
		cell_start = current_pos
		current_char = get_char_at(edit, current_pos)
		current_char_ends_line = is_line_end(edit, current_pos)
		# maybe change this to search forwards for tabs/newlines

		while current_char != '\0':
			if current_char_ends_line:
				grid[l][current_tab_num].ends_in_tab = False
				text_width_in_tab = 0
				break
			elif current_char == '\t':
				if not cell_empty:
					text_width_in_tab = get_text_width(edit, cell_start, current_pos)
				grid[l][current_tab_num].ends_in_tab = True
				grid[l][current_tab_num].text_width_pix = calc_tab_width(text_width_in_tab)
				current_tab_num += 1
				lines[l].num_tabs += 1
				text_width_in_tab = 0
				cell_empty = True
			else:
				if cell_empty:
					cell_start = current_pos
					cell_empty = False
			current_pos = edit.SendScintilla(edit.SCI_POSITIONAFTER, current_pos)
			current_char = get_char_at(edit, current_pos)
			current_char_ends_line = is_line_end(edit, current_pos)

	# find columns blocks and stretch to fit the widest cell
	for t in range(max_tabs):  # for each column
		starting_new_block = True
		first_line_in_block = 0
		max_width = 0
		for l in range(block_nof_lines):  # for each line
			if starting_new_block:
				starting_new_block = False
				first_line_in_block = l
				max_width = 0
			if grid[l][t].ends_in_tab:
				# grid[l][t].widest_width_pix = &(grid[first_line_in_block][t].text_width_pix); // point widestWidthPix at first
				grid[l][t].widest_width_pix = (first_line_in_block, t)
				if grid[l][t].text_width_pix > max_width:
					max_width = grid[l][t].text_width_pix
					grid[first_line_in_block][t].text_width_pix = max_width
			else:  # end column block
				starting_new_block = True

	# set tabstops
	for l in range(block_nof_lines):  # for each line
		current_line_num = block_start_linenum + l
		acc_tabstop = 0

		edit.SendScintilla(edit.SCI_CLEARTABSTOPS, current_line_num)

		for t in range(lines[l].num_tabs):
			if grid[l][t].widest_width_pix:
				my_l, my_t = grid[l][t].widest_width_pix
				acc_tabstop += grid[my_l][my_t].text_width_pix
				edit.SendScintilla(edit.SCI_ADDTABSTOP, current_line_num, acc_tabstop)
			else:
				break


def updateElasticTabs(edit, start, end):
	start = [start]
	end = [end]
	max_tabs_between = get_nof_tabs_between(edit, start[0], end[0])
	max_tabs_backwards = get_block_boundary(edit, start, BACKWARDS)
	max_tabs_forwards = get_block_boundary(edit, end, FORWARDS)
	max_tabs = max(max(max_tabs_between, max_tabs_backwards), max_tabs_forwards)
	max_tabs += 1  # not in original C++ code, but seems it fails without that

	block_start_linenum = edit.lineIndexFromPosition(start[0])[0]
	block_end_linenum = edit.lineIndexFromPosition(end[0])[0]
	block_nof_lines = (block_end_linenum - block_start_linenum) + 1

	stretch_tabstops(edit, block_start_linenum, block_nof_lines, max_tabs)


# eye glue
@registerSignal('editor', 'sciModified')
@disabled
def onModified(editor, mod):
	# warning: changing tabstops does not trigger a redisplay in QScintilla
	# and calling update() doesn't refresh tabstops either

	if mod.modificationType & (editor.SC_MOD_INSERTTEXT | editor.SC_MOD_CHANGESTYLE):
		updateElasticTabs(editor, mod.position, mod.position + mod.length)
	elif mod.modificationType & editor.SC_MOD_DELETETEXT:
		updateElasticTabs(editor, mod.position, mod.position)


@registerSignal('editor', 'SCN_ZOOM')
@disabled
def onZoom(editor):
	updateElasticTabs(editor, 0, editor.bytesLength())


def setEnabled(b):
	onModified.disabled = onZoom.disabled = not b
