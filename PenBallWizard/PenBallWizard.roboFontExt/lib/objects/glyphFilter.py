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
    >>> filter = GlyphFilter(FlattenPen)
    >>> filteredGlyph = filter(glyph, glyph.getParent(), approximateSegmentLength=25)
    """
    def __init__(self, *filterTuples):
        self.filterObjects = []
        self.filterArguments = {}
        for filterObject, filterArguments in filterTuples:
            self.filterObjects.append(filterObject)
            self.filterArguments[filterObject] = filterArguments

    def __call__(self, glyph, font=None, **globalArguments):
        filterObjects = self.filterObjects

        for filterObject in filterObjects:
            filterArguments = self.filterArguments[filterObject]
            arguments = {argumentName: argumentValue for argumentName, argumentValue in globalArguments.items() if argumentName in filterArguments}
            glyph = self.processGlyph(filterObject, glyph, font=None, **arguments)
        return glyph

    def processGlyph(self, filterObject, glyph, font, **arguments):
        filteredGlyph = RGlyph()
        try:
            filteredGlyph.width = glyph.width
            drawingPen = filteredGlyph.getPen()
            filterPen = filterObject(drawingPen, **arguments)
            glyph.draw(filterPen)
        except:
            try:
                filteredGlyph.appendGlyph(glyph)
                filteredGlyph.width = glyph.width
                filteredGlyph = filterObject(filteredGlyph, **arguments)
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
                thresholdFilter = GlyphFilter(ThresholdPen)
                testGlyph = self.testGlyph
                filteredGlyph = thresholdFilter(testGlyph, testGlyph.getParent(), threshold=20)

        unittest.main()

    except:
        pass