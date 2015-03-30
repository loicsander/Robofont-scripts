#coding=utf-8
from __future__ import division

from robofab.world import RGlyph
from math import atan2, tan, hypot, cos, degrees
from fontTools.misc.bezierTools import splitCubic
from mutatorScale.booleanOperations.booleanGlyph import BooleanGlyph
from mutatorScale.pens.utilityPens import CollectSegmentsPen


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
    angle = getSlantAngle(font, True)

    for i, glyphName in enumerate(['I','H']):

        if glyphName in font:

            baseGlyph = font[glyphName]

            # removing overlap
            glyph = singleContourGlyph(baseGlyph)
            width = glyph.width

            glyph.skew(-angle)

            xMin, yMin, xMax, yMax = glyph.box
            xCenter = width / 2
            yCenter = (yMax - yMin) / 2

            # glyph I, cut thick stem
            if i == 0:
                intersections = intersect(glyph, yCenter, True)

            # glyph H, cut thin stem
            elif i == 1:
                intersections = intersect(glyph, xCenter, False)

            if len(intersections) > 1:
                (x1,y1), (x2,y2) = (intersections[0], intersections[-1])

                stemWidth = hypot(x2-x1, y2-y1)
                stems.append(round(stemWidth))
            else:
                stems.append(None)

        elif glyphName not in font:
            stems.append(None)

    return stems


def getSlantAngle(font, returnDegrees=False):
    '''
    Returns the probable slant/italic angle of a font measuring the slant of a capital I.
    '''
    if 'I' in font:
        testGlyph = font['I']
        xMin, yMin, xMax, yMax = testGlyph.box
        hCenter = (yMax - yMin) / 2
        delta = 10
        intersections = []

        for i in range(2):
            horizontal = hCenter + (i * delta)
            glyph = singleContourGlyph(testGlyph)
            intersections.append(intersect(glyph, horizontal, True))

        if len(intersections) > 1:
            if len(intersections[0]) > 1 and len(intersections[1]) > 1:
                (x1,y1), (x2,y2) = (intersections[0][0], intersections[1][0])
                angle = atan2(x2-x1, y2-y1)
                if returnDegrees == False:
                    return angle
                elif returnDegrees == True:
                    return round(degrees(angle), 2)
    return 0

def singleContourGlyph(glyph):

    singleContourGlyph = RGlyph()
    singleContourGlyph.width = glyph.width
    pointPen = singleContourGlyph.getPointPen()

    if len(glyph.contours) > 1:

        booleanGlyphs = []

        for c in glyph.contours:
            b = BooleanGlyph()
            pen = b.getPen()
            c.draw(pen)
            booleanGlyphs.append(b)

            finalBooleanGlyph = reduce(lambda g1, g2: g1 | g2, booleanGlyphs)
            finalBooleanGlyph.drawPoints(pointPen)
    else:
        glyph.drawPoints(pointPen)

    return singleContourGlyph


def intersect(glyph, where, isHorizontal):
    '''
    Intersection of a glyph with a horizontal or vertical line.
    Intersects each segment of a glyph using fontTools splitCubic and splitLine methods.
    '''
    pen = CollectSegmentsPen()
    glyph.draw(pen)
    nakedGlyph = pen.getSegments()
    glyphIntersections = []

    for i, contour in enumerate(nakedGlyph):

        for segment in contour:

            length = len(segment)

            if length == 2:
                pt1, pt2 = segment
                returnedSegments = splitLine(pt1, pt2, where, int(isHorizontal))
            elif length == 4:
                pt1, pt2, pt3, pt4 = segment
                returnedSegments = splitCubic(pt1, pt2, pt3, pt4, where, int(isHorizontal))

            if len(returnedSegments) > 1:
                intersectionPoints = findDuplicatePoints(returnedSegments)
                if len(intersectionPoints):
                    box = boundingBox(segment)
                    intersectionPoints = [point for point in intersectionPoints if inRect(point, box)]
                    glyphIntersections.extend(intersectionPoints)

    return glyphIntersections


def findDuplicatePoints(segments):
    counter = {}
    for seg in segments:
        for (x, y) in seg:
            p = round(x, 4), round(y, 4)
            if counter.has_key(p):
                counter[p] += 1
            elif not counter.has_key(p):
                counter[p] = 1
    return [key for key in counter if counter[key] > 1]


def inRect(point, box):
    xMin, yMin, xMax, yMax = box
    x, y = point
    xIn = xMin <= x <= xMax
    yIn = yMin <= y <= yMax
    return xIn == yIn == True


def boundingBox(points):
    xMin, xMax, yMin, yMax = None, None, None, None
    for (x, y) in points:
        for xRef in [xMin, xMax]:
            if xRef is None: xMin, xMax = x, x
        for yRef in [yMin, yMax]:
            if yRef is None: yMin, yMax = y, y
        if x > xMax: xMax = x
        if x < xMin: xMin = x
        if y > yMax: yMax = y
        if y < yMin: yMin = y
    box = [round(value, 4) for value in [xMin, yMin, xMax, yMax]]
    return tuple(box)

# had to add that splitLine method from Robofont’s version of fontTools
# using fontTools 2.4’s method didn’t work, don’t know why.

def splitLine(pt1, pt2, where, isHorizontal):
    """Split the line between pt1 and pt2 at position 'where', which
    is an x coordinate if isHorizontal is False, a y coordinate if
    isHorizontal is True. Return a list of two line segments if the
    line was successfully split, or a list containing the original
    line.

        >>> printSegments(splitLine((0, 0), (100, 100), 50, True))
        ((0, 0), (50.0, 50.0))
        ((50.0, 50.0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 100, True))
        ((0, 0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, True))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
        >>> printSegments(splitLine((0, 0), (100, 100), 0, False))
        ((0, 0), (0.0, 0.0))
        ((0.0, 0.0), (100, 100))
    """
    pt1x, pt1y = pt1
    pt2x, pt2y = pt2

    ax = (pt2x - pt1x)
    ay = (pt2y - pt1y)

    bx = pt1x
    by = pt1y

    a = (ax, ay)[isHorizontal]

    if a == 0:
        return [(pt1, pt2)]

    t = float(where - (bx, by)[isHorizontal]) / a
    if 0 <= t < 1:
        midPt = ax * t + bx, ay * t + by
        return [(pt1, midPt), (midPt, pt2)]
    else:
        return [(pt1, pt2)]