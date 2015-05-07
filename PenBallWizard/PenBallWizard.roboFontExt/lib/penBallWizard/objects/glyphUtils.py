from robofab.world import RGlyph
from robofab.pens.reverseContourPointPen import ReverseContourPointPen

def passThrough(glyph):
    return glyph

def copyContours(glyph):
    glyphCopy = RGlyph()
    glyphCopy.width = glyph.width
    pen = glyphCopy.getPen()
    glyph.draw(pen)
    glyphCopy.unicode = glyph.unicode
    glyphCopy.name = glyph.name
    return glyphCopy

def reverseContours(glyph):
    glyphCopy = RGlyph()
    glyphCopy.width = glyph.width
    pointPen = glyphCopy.getPointPen()
    reversePen = ReverseContourPointPen(pointPen)
    glyph.drawPoints(reversePen)
    return glyphCopy

def removeOverlap(glyph):
    glyphCopy = RGlyph()
    glyphCopy.width = glyph.width
    pointPen = glyphCopy.getPointPen()
    glyph.drawPoints(pointPen)
    glyphCopy.removeOverlap()
    return glyphCopy