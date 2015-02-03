# Loïc Sander
# 150203
# v0.4

'''
Robofont script meant to help with sidebearings adjustments regarding italic fonts
in which the italic angle display options of Robofont was used.
It allows you to set an italic font’s metrics according to an angle and base glyph
for which you wish to have equal sidebearings (usually a lowercase or uppercase O).
'''

def shiftMetricsToAngle(font, angle, baseGlyphName, setItalicAngle=True, glyphSet=None):

    fontKeys = font.keys()

    if glyphSet is None:
        glyphSet = fontKeys
    elif glyphSet is not None:
        glyphSet = list(set(fontKeys) & set(glyphSet))

    if setItalicAngle:
        font.info.italicAngle = angle

    # the glyph that should be centered in its width, by design
    baseGlyph = f[baseGlyphName]

    if angle == 0:
        baseLeftMargin = (baseGlyph.leftMargin + baseGlyph.rightMargin) / 2
        xshift = - baseGlyph.leftMargin + baseLeftMargin

    elif angle != 0:
        baseLeftMargin = (baseGlyph.angledLeftMargin + baseGlyph.angledRightMargin) / 2
        xshift = - baseGlyph.angledLeftMargin + baseLeftMargin

    if xshift and (round(baseGlyph.angledLeftMargin) != round(baseLeftMargin)) and len(glyphSet):

        font.prepareUndo('shift.back.italic')

        for glyphName in glyphSet:
            if glyphName in fontKeys:
                g = f[glyphName]
                g.move((xshift, 0))
                if not len(g.anchors):
                    for c in g.components:
                        c.move((-xshift, 0))
                g.update()

        font.performUndo()

        print '\n%s %s' % (font.info.familyName, font.info.styleName)
        if setItalicAngle:
            print 'changed italic angle to %s' % (font.info.italicAngle)
        print 'Moved all glyphs by %0.2f units' % (xshift)

    else:
        print unicode('Didn’t move anything, no need.', 'utf-8')

f = CurrentFont()
shiftMetricsToAngle(f, 0, 'o')