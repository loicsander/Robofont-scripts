#coding=utf8
from __future__ import division

from math import pi, cos, sin, hypot
from robofab.world import RGlyph

_LETTERFORMS = {
        'interpolation':[
            [
                (296, 322), (201, 322),
                (201, 352), (231, 352),
                (231, 397), (201, 397),
                (201, 427), (296, 427),
                (296, 397), (266, 397),
                (266, 352), (296, 352)
            ]
        ],
        'none':[
            [
                (231, 322), (201, 322),
                (201, 427), (236, 427),
                (266, 374), (266, 427),
                (296, 427), (296, 322),
                (261, 322), (231, 375)
            ]
        ],
        'boolean':[
            [
                (271, 401), (236, 401),
                (236, 386), (271, 386),
                (276, 393),
            ],[
                (290, 322),
                (201, 322), (201, 427),
                (290, 427), (309, 408),
                (309, 392), (294, 375),
                (309, 357), (309, 341),
            ],[
                (271, 364), (236, 364),
                (236, 348), (271, 348),
                (276, 356)
            ]
        ]
    }

class ErrorGlyph(RGlyph):

    def __new__(cls, errorName=None, report=None, size=500, upm=1000):
        newGlyph = super(ErrorGlyph, cls).__new__(cls)
        newGlyph.__init__(errorName, report, size, upm)
        return newGlyph

    def __init__(self, errorName=None, report=None, size=500, upm=1000):
        super(ErrorGlyph, self).__init__()
        self.note = report
        self.name = '_error_'
        self.upm = upm
        self.pen = self.getPen()
        size = 300
        self._setSize(size)
        self.width = 500
        self._drawError(errorName)
        scale = upm / 1000
        self.scale((scale, scale))

    def _setSize(self, size):
        self.si = size
        self.st = (
            250 - (size / 4),
            (750 / 2) - (size / 2)
            )
        self.le = hypot(size, size) / 4

    def _drawError(self, errorName):
        errorSign = self._getErrorSign()
        self._drawPoints(errorSign)
        if errorName is not None:
            points = self._getLetter(errorName)
            self._drawPoints(points)

    def _drawPoints(self, contours):
        pen = self.pen
        for points in contours:
            for i, point in enumerate(points):
                if i == 0:
                    pen.moveTo(point)
                else:
                    pen.lineTo(point)
            pen.closePath()

    def _getErrorSign(self):
        points = []
        a = pi/4
        size = self.le
        start = self.st
        px, py = start
        for i in range(12):
            x = px + (size * cos(a))
            y = py + (size * sin(a))
            points.append((x, y))
            px = x
            py = y
            if i%3 == 0:
                a -= pi/2
            elif i%3 != 0:
                a += pi/2
        return [points]

    def _getLetter(self, errorName):
        errorName = errorName.lower()
        if errorName in _LETTERFORMS:
            return _LETTERFORMS[errorName]

if __name__ == '__main__':

    import unittest

    class ErrorGlyphTests(unittest.TestCase):

        def test_building_errorGlyph_with_note(self):
            for letter in _LETTERFORMS:
                e = ErrorGlyph(letter, report='No idea what happened.')

        def test_building_errorGlyphs(self):
            for letter in _LETTERFORMS:
                e = ErrorGlyph(letter)

    unittest.main()