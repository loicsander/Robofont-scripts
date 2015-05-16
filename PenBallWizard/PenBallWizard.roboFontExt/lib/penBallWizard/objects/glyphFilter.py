 #coding=utf-8
import json
import inspect

from fontTools.pens.basePen import BasePen
from robofab.world import RGlyph
from errorGlyph import ErrorGlyph
from penUtils import FilterPointPen, CollectComponentsPen

class GlyphFilter(object):
    """
    Filter object initiated with a robofab pen and, if need be, arguments for that pen,
    and then acts like a filter function returning a filtered glyph.

    >>> from robofab.pens.filterPen import FlattenPen
    >>> filter = GlyphFilter(FlattenPen)
    >>> filteredGlyph = filter(glyph, glyph.getParent(), approximateSegmentLength=25)
    """

    def __init__(self, filterObject, filterArguments={}, ignoreComponents=False):
        self.filterObject = filterObject
        self.filterArguments = filterArguments
        self.ignoreComponents = ignoreComponents


    def __call__(self, glyph, font=None, **arguments):
        filterObject = self.filterObject
        filterArguments = self.filterArguments
        validArguments = {argumentName: argumentValue for argumentName, argumentValue in arguments.items() if argumentName in filterArguments}

        outputGlyph = self.processGlyph(glyph, font=font, **arguments)

        if outputGlyph.name != '_error_':
            outputGlyph.name = glyph.name

        outputGlyph.unicode = glyph.unicode

        if outputGlyph.width is None:
            outputGlyph = ErrorGlyph('none')

        return outputGlyph


    def processGlyph(self, glyph, font, **arguments):
        filterObject = self.filterObject
        glyph, components, anchors = self.normalizeGlyph(glyph)

        if inspect.isfunction(filterObject):
            try:
                filteredGlyph = filterObject(glyph, **arguments)
                if filteredGlyph is None:
                    filteredGlyph = glyph

            except Exception as e:
                print u'PenBallWizard — GlyphFilter: Error (function): {0}'.format(e)
                error = True
                filteredGlyph = ErrorGlyph()
        else:
            try:
                filteredGlyph = RGlyph()
                filteredGlyph.width = glyph.width
                drawingPen = filteredGlyph.getPen()
                filterPen = filterObject(drawingPen, **arguments)
                glyph.draw(filterPen)

            except Exception as e:
                print u'PenBallWizard — GlyphFilter: Error (pen): {0}'.format(e)
                error = True
                filteredGlyph = ErrorGlyph()

        for baseGlyphName, transformation in components:
            offset = transformation[-2:]
            scale = (transformation[0], transformation[3])
            filteredGlyph.appendComponent(baseGlyphName, offset, scale)

        for anchor in anchors:
            filteredGlyph.appendAnchor(*anchor)

        return filteredGlyph


    def normalizeGlyph(self, glyph):
        componentsCollector = CollectComponentsPen()
        glyph.draw(componentsCollector)
        components = componentsCollector.get()
        anchors = []

        for anchor in reversed(glyph.anchors):
            anchors.append((anchor.name, (anchor.x, anchor.y)))

        cleanGlyph = self.getCleanedGlyph(glyph)

        return cleanGlyph, components, anchors


    def getCleanedGlyph(self, glyph):
        cleanGlyph = RGlyph()
        cleanGlyph.width = glyph.width
        pen = cleanGlyph.getPointPen()
        cleanPen = FilterPointPen()
        glyph.drawPoints(cleanPen)
        cleanPen.extract(pen)
        return cleanGlyph




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