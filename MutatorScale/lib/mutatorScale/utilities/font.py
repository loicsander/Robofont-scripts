#coding=utf-8
from __future__ import division

from robofab.world import RGlyph
from math import atan2, tan, hypot, cos
from mojo.tools import IntersectGlyphWithLine

def makeListFontName(font):
    '''
    Returns a font name in the form: 'Family name > style name'.
    The separator allows to easily split this full name later on with name.split(' > ').
    '''
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None:
        familyName = font.info.familyName = 'Unnamed'
    if styleName is None:
        styleName = font.info.styleName = 'Unnamed'
    return ' > '.join([familyName, styleName])

def getRefStems(font, slantedSection=False):
    '''
    Looks for stem values to serve as reference for a font in an interpolation scheme,
    only one typical value is returned for both horizontal and vertical stems.
    The method intersets the thick stem of a capital I and thin stem of a capital H.
    '''
    stems = []
    angle = getSlantAngle(font)

    for i, glyphName in enumerate(['I','H']):

        if glyphName in font:

            baseGlyph = font[glyphName]
            glyph = RGlyph()
            pen = glyph.getPen()
            baseGlyph.draw(pen)
            glyph.removeOverlap()
            if glyphName == 'I':
                width = 2000
            elif glyphName == 'H':
                width = baseGlyph.width

            xMin, yMin, xMax, yMax = glyph.box
            xCenter = width / 2
            yCenter = (yMax - yMin) / 2

            # glyph I, cut thick stem
            if i == 0:
                if slantedSection == False:
                    sectionAngle = 0
                else:
                    sectionAngle = angle
                refPoint1 = (0, yCenter + (xCenter * tan(sectionAngle)))
                refPoint2 = (width, yCenter - (xCenter * tan(sectionAngle)))

            # glyph H, cut thin stem
            elif i == 1:
                refPoint1 = (xCenter + ((yMax - yMin) * tan(angle)), yMax)
                refPoint2 = (xCenter, yMin)

            intersections = IntersectGlyphWithLine(glyph, (refPoint1, refPoint2))

            print glyphName, intersections

            (x1,y1), (x2,y2) = (intersections[0], intersections[-1])

            stemWidth = hypot(x2-x1, y2-y1)
            if i == 1: stemWidth = stemWidth * cos(angle)
            stems.append(round(stemWidth))

        elif glyphName not in font:
            stems.append(None)

    return stems


def getSlantAngle(font):
    '''
    Returns the probable slant/italic angle of a font measuring the slant of a capital I.
    '''
    if 'I' in font:
        glyph = font['I']
        xMin, yMin, xMax, yMax = glyph.box
        width = xMax - xMin
        hCenter = (yMax - yMin) / 2
        delta = 10
        intersections = []
        for i in range(2):
            refPoint1 = (0, hCenter + (i*delta))
            refPoint2 = (width, hCenter + (i*delta))
            intersections.append(IntersectGlyphWithLine(glyph, (refPoint1, refPoint2)))
        if len(intersections) > 1:
            if len(intersections[0]) > 1 and len(intersections[1]) > 1:
                (x1,y1), (x2,y2) = (intersections[0][0], intersections[1][0])
                return atan2(x2-x1, y2-y1)
    return 0
