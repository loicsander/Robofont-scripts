"""
june 2014 — Loïc Sander
– Adds anchors to any glyph in the baseGlyphList, if present in font.keys() and no specific glyph is selectedGlyphs,
otherwise, adds anchors only to the selected glyphs
– If a glyph already has the named anchor, the script skips this anchor
– Any glyph that received new anchors is colored in a weird blue

– baseGlyphList structure:
{
	"glyphName": [
		["anchorName", "yPos", "xPos"]
	]
}

keywords for positions:
	xPos: left, center, right (based on the glyphs bounding box)
	yPos: baseline, xHeight(+offset), xHeightCenter, ascender(+offset), capHeight(+offset), belowBaseline, belowGlyph, glyphCenter, glyphBase, glyphTop 

to add yours, see xPos and yPos dicts below.
"""


baseGlyphList = {
	
	### UPPERCASE GLYPHS ############################

	"A": [
		["top", 	"capHeight", 	"center"], 
		["right", 	"baseline", 	"right"] ],

	"AE": [
		["top", 	"capHeight", 	"center"] ],

	"C": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"D": [
		["top", 	"capHeight", 	"center"] ],

	"E": [
		["top", 	"capHeight", 	"center"], 
		["right", 	"baseline", 	"right"],
		["bottom", 	"baseline", 	"center"] ],

	"G": [
		["top", 	"capHeight", 	"center"], 
		["bottom",	"baseline", 	"center"] ],

	"H": [
		["top", 	"capHeight", 	"center"] ],

	"I": [
		["top", 	"capHeight", 	"center"], 
		["right", 	"baseline", 	"center"],
		["bottom", 	"belowBaseline", "center"] ],

	"J": [
		["top", 	"capHeight", 	"center"] ],

	"K": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"L": [
		["top", 	"capHeight", 	"left"], 
		["right", 	"capHeight", 	"center"],
		["mid", 	"center", 		"center"],
		["bottom", 	"baseline", 	"center"] ],

	"N": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"O": [
		["top", 	"capHeight", 	"center"],
		["bottom", 	"baseline", 	"center"] ],

	"R": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"S": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"T": [
		["top", 	"capHeight", 	"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"U": [
		["top", 	"capHeight", 	"center"], 
		["right", 	"baseline", 	"center"],
		["bottom", 	"belowBaseline", "center"] ],

	"W": [
		["top", 	"capHeight", 	"center"] ],

	"Y": [
		["top", 	"capHeight", 	"center"] ],

	"Z": [
		["top", 	"capHeight", 	"center"] ],

	### LOWERCASE ############################	

	"a": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"], 
		["right", 	"baseline", 	"right"] ],

	"ae": [
		["top", 	"xHeight", 		"center"] ],

	"c": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"d": [
		["right", 	"ascender", 	"right"] ],

	"e": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"],
		["right", 	"baseline", 	"right"] ],

	"g": [
		["top", 	"xHeight", 		"center"],
		["bottom", 	"belowGlyph",	"center"] ],

	"h": [
		["top", 	"ascender", 	"left"], 
		["bottom", 	"baseline", 	"center"] ],

	"i": [
		["right", 	"baseline", 	"right"] ],

	"dotlessi": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"],
		["right", 	"baseline", 	"right"] ],

	"dotlessj": [
		["top", 	"xHeight", 		"center"] ],

	"k": [
		["top", 	"ascender", 	"left"], 
		["bottom", 	"baseline", 	"center"] ],

	"l": [
		["top", 	"ascender", 	"center"], 
		["bottom", 	"baseline", 	"center"],
		["mid", 	"xHeightCenter", "center"],
		["right", 	"ascender", 	"right"] ],

	"n": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"o": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"r": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"left"] ],

	"s": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"] ],

	"t": [
		["right", 	"glyphTop", 	"right"], 
		["bottom", 	"baseline", 	"center"] ],

	"u": [
		["top", 	"xHeight", 		"center"], 
		["bottom", 	"baseline", 	"center"],
		["right", 	"baseline", 	"right"] ],

	"w": [
		["top", 	"xHeight", 		"center"], ],

	"y": [
		["top", 	"xHeight", 		"center"], ],

	"z": [
		["top", 	"xHeight", 		"center"], ],

	### DIACRITICS ############################

	"acute": [
		["_top", 	"glyphBase", 	"center"] ],

	"acute.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"grave": [
		["_top", 	"glyphBase", 	"center"] ],

	"grave.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"circumflex": [
		["_top", 	"glyphBase", 	"center"] ],

	"circumflex.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"dieresis": [
		["_top", 	"glyphBase", 	"center"] ],

	"dieresis.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"ring": [
		["_top", 	"glyphBase", 	"center"] ],

	"ring.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"tilde": [
		["_top", 	"glyphBase", 	"center"] ],

	"tilde.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"cedilla": [
		["_bottom", "baseline", 	"center"] ],

	"caron": [
		["_top", 	"glyphBase", 	"center"] ],

	"caron.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"breve": [
		["_top", 	"glyphBase", 	"center"] ],

	"breve.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"ogonek": [
		["_bottom", "belowBaseline", 		"center"],
		["_right", 	"baseline", 	"right"] ],

	"macron": [
		["_top", 	"glyphBase", 	"center"] ],

	"macron.cap": [
		["_top", 	"glyphBase", 	"center"] ],

	"dotaccent": [
		["_top", 	"glyphBase", 	"center"],
		["_right", 	"center", 		"left"] ],

	"dotaccent.cap": [
		["_top", 	"glyphBase", 	"center"],
		["_right", 	"center", 		"left"] ],

	"commaaccent.cap": [
		["_top", 	"glyphTop", 	"center"] ],

	"commaaccent.alt": [
		["_top", 	"glyphBase", 	"center"],
		["_right", 	"glyphBase", 	"right"] ],

	"hungarumlaut": [
		["_top", 	"glyphBase", 	"center"] ],

	"hungarumlaut.cap": [
		["_top", 	"glyphBase", 	"center"] ],
}

def addAnchors(font, glyphName, anchors, offset=None):

	if font is not None:

		selectedGlyphs = font.selection

		if (glyphName in font.keys()) and ((len(selectedGlyphs) == 0) or ((len(selectedGlyphs) > 0) and (glyphName in selectedGlyphs))):
			glyph = font[glyphName]
			anchorList = [ glyph.anchors[anchor].name for anchor in range(len(glyph.anchors))]

			from math import radians, tan
			italicAngle = radians(font.info.italicAngle)

			if offset == None:
				offset = round(font.info.unitsPerEm * 0.03)

			xPos = {
				"center": ((glyph.width - (glyph.angledLeftMargin + glyph.angledRightMargin)) / 2) + glyph.angledLeftMargin,
				"right": glyph.width - glyph.angledRightMargin,
				"left": glyph.angledLeftMargin
			}

			yPos = {
				"baseline": 0,
				"ascender": font.info.ascender + offset,
				"capHeight": font.info.capHeight + offset,
				"xHeight": font.info.xHeight + (offset*2),
				"xHeightCenter": font.info.xHeight / 2,
				"belowBaseline": -offset,
				"belowGlyph": glyph.box[1] - offset,
				"center": (glyph.box[3] - glyph.box[1]) / 2,
				"glyphBase": glyph.box[1],
				"glyphTop": glyph.box[3],
			}

			for anchor in anchors:

				italicOffset = -round(yPos[anchor[1]]) * tan(italicAngle)
				anchorName = anchor[0]
				anchorPos = (round(xPos[anchor[2]]) + italicOffset, round(yPos[anchor[1]]))

				if anchorName not in anchorList:
					glyph.prepareUndo("add-anchors")
					glyph.appendAnchor(anchorName, anchorPos)
					setattr(glyph, "mark", (0.5, 0.8, 0.8, 0.5))
					glyph.performUndo()
	else:
		print "No current font."


font = CurrentFont()
# value defining the offset of anchors from their reference point (as in baseGlyphList supra)
# defaults to 3% of UPM value (~30 units for 1000 UPM, ~60 units for 2048) 
offset = None

for glyphName, anchors in baseGlyphList.items():
	addAnchors(font, glyphName, anchors, offset)
	