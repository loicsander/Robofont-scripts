 #coding=utf-8
import json

from fontTools.pens.basePen import AbstractPen, BasePen
from robofab.pens.pointPen import AbstractPointPen
from robofab.world import RGlyph
from errorGlyph import ErrorGlyph

def getFileName(path):
    fileName = path.split('/')
    return fileName[-1][:-3]

class GlyphFilter(object):
    """
    Filter object initiated with a robofab pen and, if need be, arguments for that pen,
    and then acts like a filter function returning a filtered glyph.

    >>> from robofab.pens.filterPen import FlattenPen
    >>> filter = GlyphFilter(FlattenPen, approximateSegmentLength=25)
    >>> filteredGlyph = filter(glyph)
    """
    def __init__(self, filterObject):
        self.filterObject = filterObject

    def __call__(self, glyph, font, **arguments):
        try:
            filteredGlyph = RGlyph()
            filteredGlyph.width = glyph.width
            drawingPen = filteredGlyph.getPen()
            filterPen = self.filterObject(drawingPen, **arguments)
            glyph.draw(filterPen)
        except:
            try:
                sourceGlyph = RGlyph()
                sourceGlyph.appendGlyph(glyph)
                sourceGlyph.width = glyph.width
                filteredGlyph = self.filterObject(sourceGlyph, **arguments)
            except:
                filteredGlyph = ErrorGlyph()

        return filteredGlyph

if __name__ == '__main__':

    try:
        import fontTools
        import robofab
        from robofab.pens.filterPen import ThresholdPen
        import defcon
        from defcon import Glyph

        import unittest

        class GlyphFilterTest(unittest.TestCase):

            def setUp(self):
                testGlyph = Glyph()
                pen = testGlyph.getPen()
                self.drawTestGlyph(pen)
                self.testGlyph = testGlyph

            def drawTestGlyph(self, pen):
                pen.moveTo((10, 10))
                pen.lineTo((110, 10))
                pen.lineTo((110, 110))
                pen.lineTo((10, 110))
                pen.closePath()

            def test_GlyphFilterInit(self):
                thresholdFilter = GlyphFilter(ThresholdPen, threshold=20)
                testGlyph = self.testGlyph
                filteredGlyph = thresholdFilter(testGlyph, testGlyph.getParent())

        unittest.main()

    except:
        pass