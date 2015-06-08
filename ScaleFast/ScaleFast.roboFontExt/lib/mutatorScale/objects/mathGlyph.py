import weakref
from robofab.world import RGlyph
from robofab.pens.pointPen import BasePointToSegmentPen, AbstractPointPen
from robofab.objects.objectsBase import addPt, subPt, mulPt, BaseGlyph
from math import radians, tan, cos, sin, pi

'''
Custom implementation of a MathGlyph with skewing.
Original MathGlyph in FontMath, by Tal Leming: https://github.com/typesupply/fontMath
See license (MIT), here: https://github.com/typesupply/fontMath/blob/master/License.txt
'''

def divPt(pt, scalar):
    if not isinstance(scalar, tuple):
        f1 = scalar
        f2 = scalar
    else:
        f1, f2 = scalar
    return pt[0] / f1, pt[1] / f2


class MathGlyphPen(AbstractPointPen):

    """
    Point pen for building MathGlyph data structures.
    """

    def __init__(self):
        self.contours = []
        self.components = []
        self.anchors = []
        self._points = []

    def _flushContour(self):
        points = self._points
        if len(points) == 1:
            segmentType, pt, smooth, name = points[0]
            self.anchors.append((pt, name))
        else:
            self.contours.append([])
            prevOnCurve = None
            offCurves = []
            # deal with the first point
            segmentType, pt, smooth, name = points[0]
            # if it is an offcurve, add it to the offcurve list
            if segmentType is None:
                offCurves.append((segmentType, pt, smooth, name))
            # if it is a line, change the type to curve and add it to the contour
            # create offcurves corresponding with the last oncurve and
            # this point and add them to the points list
            elif segmentType == "line":
                prevOnCurve = pt
                self.contours[-1].append(("curve", pt, smooth, name))
                lastPoint = points[-1][1]
                points.append((None, lastPoint, False, None))
                points.append((None, pt, False, None))
            # a move, curve or qcurve. simple append the data.
            else:
                self.contours[-1].append((segmentType, pt, smooth, name))
                prevOnCurve = pt
            # now go through the rest of the points
            for segmentType, pt, smooth, name in points[1:]:
                # store the off curves
                if segmentType is None:
                    offCurves.append((segmentType, pt, smooth, name))
                    continue
                # make off curve corresponding the the previous
                # on curve an dthis point
                if segmentType == "line":
                    segmentType = "curve"
                    offCurves.append((None, prevOnCurve, False, None))
                    offCurves.append((None, pt, False, None))
                # add the offcurves to the contour
                for offCurve in offCurves:
                    self.contours[-1].append(offCurve)
                # add the oncurve to the contour
                self.contours[-1].append((segmentType, pt, smooth, name))
                # reset the stored data
                prevOnCurve = pt
                offCurves = []
            # catch offcurves that belong to the first
            if len(offCurves) != 0:
                self.contours[-1].extend(offCurves)

    def beginPath(self):
        self._points = []

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        self._points.append((segmentType, pt, smooth, name))

    def endPath(self):
        self._flushContour()

    def addComponent(self, baseGlyphName, transformation):
        self.components.append((baseGlyphName, transformation))


class FilterRedundantPointPen(AbstractPointPen):

    def __init__(self, anotherPointPen):
        self._pen = anotherPointPen
        self._points = []

    def _flushContour(self):
        points = self._points
        # an anchor
        if len(points) == 1:
            pt, segmentType, smooth, name = points[0]
            self._pen.addPoint(pt, segmentType, smooth, name)
        else:
            prevOnCurve = None
            offCurves = []

            pointsToDraw = []

            # deal with the first point
            pt, segmentType, smooth, name = points[0]
            # if it is an offcurve, add it to the offcurve list
            if segmentType is None:
                offCurves.append((pt, segmentType, smooth, name))
            else:
                # potential redundancy
                if segmentType == "curve":
                    # gather preceding off curves
                    testOffCurves = []
                    lastPoint = None
                    for i in xrange(len(points)):
                        i = -i - 1
                        testPoint = points[i]
                        testSegmentType = testPoint[1]
                        if testSegmentType is not None:
                            lastPoint = testPoint[0]
                            break
                        testOffCurves.append(testPoint[0])
                    # if two offcurves exist we can test for redundancy
                    if len(testOffCurves) == 2:
                        if testOffCurves[1] == lastPoint and testOffCurves[0] == pt:
                            segmentType = "line"
                            # remove the last two points
                            points = points[:-2]
                # add the point to the contour
                pointsToDraw.append((pt, segmentType, smooth, name))
                prevOnCurve = pt
            for pt, segmentType, smooth, name in points[1:]:
                # store offcurves
                if segmentType is None:
                    offCurves.append((pt, segmentType, smooth, name))
                    continue
                # curves are a potential redundancy
                elif segmentType == "curve":
                    if len(offCurves) == 2:
                        # test for redundancy
                        if offCurves[0][0] == prevOnCurve and offCurves[1][0] == pt:
                            offCurves = []
                            segmentType = "line"
                # add all offcurves
                for offCurve in offCurves:
                    pointsToDraw.append(offCurve)
                # add the on curve
                pointsToDraw.append((pt, segmentType, smooth, name))
                # reset the stored data
                prevOnCurve = pt
                offCurves = []
            # catch any remaining offcurves
            if len(offCurves) != 0:
                for offCurve in offCurves:
                    pointsToDraw.append(offCurve)
            # draw to the pen
            for pt, segmentType, smooth, name in pointsToDraw:
                self._pen.addPoint(pt, segmentType, smooth, name)

    def beginPath(self):
        self._points = []
        self._pen.beginPath()

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        self._points.append((pt, segmentType, smooth, name))

    def endPath(self):
        self._flushContour()
        self._pen.endPath()

    def addComponent(self, baseGlyphName, transformation):
        self._pen.addComponent(baseGlyphName, transformation)


class MathGlyph(object):

    """
    A very shallow glyph object for rapid math operations.

    This glyph differs from a standard RGlyph in many ways.
    Most notably "line" segments do not exist. This is done
    to make contours more compatible.

    Notes about glyph math:
    -   absolute contour compatibility is required
    -   absolute comoponent and anchor compatibility is NOT required. in cases
        of incompatibility in this data, only compatible data is processed and
        returned. becuase of this, anchors and components may not be returned
        in the same order as the original.

    If a MathGlyph is created by another glyph that is not another MathGlyph instance,
    a weakref that points to the original glyph is maintained.
    """

    def __init__(self, glyph):
        self._structure = None
        if glyph is None:
            self.contours = []
            self.components = []
            self.anchors = []
            self.lib = {}
            #
            self.name = None
            self.unicodes = None
            self.width = None
            self.note = None
            self.generationCount = 0
        else:
            p = MathGlyphPen()
            glyph.drawPoints(p)
            self.contours = p.contours
            self.components = p.components
            self.anchors = p.anchors
            self.lib = {}
            #
            self.name = glyph.name
            self.unicodes = glyph.unicodes
            self.width = glyph.width
            self.note = glyph.note
            #
            for k, v in glyph.lib.items():
                self.lib[k] = v
            #
            # set a weakref for the glyph
            # ONLY if it is not a MathGlyph.
            # this could happen as a result
            # of a MathGlyph.copy()
            if not isinstance(glyph, MathGlyph):
                self.getRef = weakref.ref(glyph)
                self.generationCount = 0
            else:
                self.generationCount = glyph.generationCount + 1

    def getRef(self):
        """
        return the original glyph that self was built from.
        this will return None if self was built from
        another MathGlyph instance
        """
        # overriden by weakref.ref if present
        return None

    def _get_structure(self):
        if self._structure is not None:
            return self._structure
        contourStructure = []
        for contour in self.contours:
            contourStructure.append([segmentType for segmentType, pt, smooth, name in contour])
        componentStructure = [baseName for baseName, transformation in self.components]
        anchorStructure = [name for pt, name in self.anchors]
        return contourStructure, componentStructure, anchorStructure

    structure = property(_get_structure, doc="returns a tuple of (contour structure, component structure, anchor structure)")

    def _get_box(self):
        from fontTools.pens.boundsPen import BoundsPen
        bP = BoundsPen(None)
        self.draw(bP)
        return bP.bounds

    box = property(_get_box, doc="Bounding rect for self. Returns None is glyph is empty. This DOES NOT measure components.")

    def copy(self):
        """return a new MathGlyph containing all data in self"""
        return MathGlyph(self)

    def copyWithoutIterables(self):
        """
        return a new MathGlyph containing all data except:
        contours
        components
        anchors

        this is used mainly for internal glyph math.
        """
        n = MathGlyph(None)
        n.generationCount = self.generationCount + 1
        #
        n.name = self.name
        n.unicodes = self.unicodes
        n.width = self.width
        n.note = self.note
        #
        for k, v in self.lib.items():
            n.lib[k] = v
        return n

    def _anchorCompare(self, other):
        # gather compatible anchors
        #
        # adapted from robofab.objects.objectsBase.RGlyph._anchorCompare
        selfAnchors = {}
        for pt, name in self.anchors:
            if not selfAnchors.has_key(name):
                selfAnchors[name] = []
            selfAnchors[name].append(pt)
        otherAnchors = {}
        for pt, name in other.anchors:
            if not otherAnchors.has_key(name):
                otherAnchors[name] = []
            otherAnchors[name].append(pt)
        compatAnchors = set(selfAnchors.keys()) & set(otherAnchors.keys())
        finalSelfAnchors = {}
        finalOtherAnchors = {}
        for name in compatAnchors:
            if not finalSelfAnchors.has_key(name):
                finalSelfAnchors[name] = []
            if not finalOtherAnchors.has_key(name):
                finalOtherAnchors[name] = []
            selfList = selfAnchors[name]
            otherList = otherAnchors[name]
            selfCount = len(selfList)
            otherCount = len(otherList)
            if selfCount != otherCount:
                r = range(min(selfCount, otherCount))
            else:
                r = range(selfCount)
            for i in r:
                finalSelfAnchors[name].append(selfList[i])
                finalOtherAnchors[name].append(otherList[i])
        return finalSelfAnchors, finalOtherAnchors

    def _componentCompare(self, other):
        # gather compatible compoenents
        #
        selfComponents = {}
        for baseName, transformation in self.components:
            if not selfComponents.has_key(baseName):
                selfComponents[baseName] = []
            selfComponents[baseName].append(transformation)
        otherComponents = {}
        for baseName, transformation in other.components:
            if not otherComponents.has_key(baseName):
                otherComponents[baseName] = []
            otherComponents[baseName].append(transformation)
        compatComponents = set(selfComponents.keys()) & set(otherComponents.keys())
        finalSelfComponents = {}
        finalOtherComponents = {}
        for baseName in compatComponents:
            if not finalSelfComponents.has_key(baseName):
                finalSelfComponents[baseName] = []
            if not finalOtherComponents.has_key(baseName):
                finalOtherComponents[baseName] = []
            selfList = selfComponents[baseName]
            otherList = otherComponents[baseName]
            selfCount = len(selfList)
            otherCount = len(otherList)
            if selfCount != otherCount:
                r = range(min(selfCount, otherCount))
            else:
                r = range(selfCount)
            for i in r:
                finalSelfComponents[baseName].append(selfList[i])
                finalOtherComponents[baseName].append(otherList[i])
        return finalSelfComponents, finalOtherComponents

    def _processMathOne(self, copiedGlyph, otherGlyph, funct):
        # glyph processing that recalculates glyph values based on another glyph
        # used by: __add__, __sub__
        #
        # contours
        copiedGlyph.contours = []
        if len(self.contours) > 0:
            for contourIndex in range(len(self.contours)):
                copiedGlyph.contours.append([])
                selfContour = self.contours[contourIndex]
                otherContour = otherGlyph.contours[contourIndex]
                for pointIndex in range(len(selfContour)):
                    segType, pt, smooth, name = selfContour[pointIndex]
                    newX, newY = funct(selfContour[pointIndex][1], otherContour[pointIndex][1])
                    copiedGlyph.contours[-1].append((segType, (newX, newY), smooth, name))
        # anchors
        copiedGlyph.anchors = []
        if len(self.anchors) > 0:
            selfAnchors, otherAnchors = self._anchorCompare(otherGlyph)
            anchorNames = selfAnchors.keys()
            for anchorName in anchorNames:
                selfAnchorList = selfAnchors[anchorName]
                otherAnchorList = otherAnchors[anchorName]
                for i in range(len(selfAnchorList)):
                    selfAnchor = selfAnchorList[i]
                    otherAnchor = otherAnchorList[i]
                    newAnchor = funct(selfAnchor, otherAnchor)
                    copiedGlyph.anchors.append((newAnchor, anchorName))
        # components
        copiedGlyph.components = []
        if len(self.components) > 0:
            selfComponents, otherComponents = self._componentCompare(otherGlyph)
            componentNames = selfComponents.keys()
            for componentName in componentNames:
                selfComponentList = selfComponents[componentName]
                otherComponentList = otherComponents[componentName]
                for i in range(len(selfComponentList)):
                    # transformation breakdown: xScale, xyScale, yxScale, yScale, xOffset, yOffset
                    selfXScale, selfXYScale, selfYXScale, selfYScale, selfXOffset, selfYOffset = selfComponentList[i]
                    otherXScale, otherXYScale, otherYXScale, otherYScale, otherXOffset, otherYOffset = otherComponentList[i]
                    newXScale, newXYScale = funct((selfXScale, selfXYScale), (otherXScale, otherXYScale))
                    newYXScale, newYScale = funct((selfYXScale, selfYScale), (otherYXScale, otherYScale))
                    newXOffset, newYOffset = funct((selfXOffset, selfYOffset), (otherXOffset, otherYOffset))
                    copiedGlyph.components.append((componentName, (newXScale, newXYScale, newYXScale, newYScale, newXOffset, newYOffset)))

    def _processMathTwo(self, copiedGlyph, factor, funct):
        # glyph processing that recalculates glyph values based on a factor
        # used by: __mul__, __div__
        #
        # contours
        copiedGlyph.contours = []
        if len(self.contours) > 0:
            for selfContour in self.contours:
                copiedGlyph.contours.append([])
                for segType, pt, smooth, name in selfContour:
                    newX, newY = funct(pt, factor)
                    copiedGlyph.contours[-1].append((segType, (newX, newY), smooth, name))
        # anchors
        copiedGlyph.anchors = []
        if len(self.anchors) > 0:
            for pt, anchorName in self.anchors:
                newPt = funct(pt, factor)
                copiedGlyph.anchors.append((newPt, anchorName))
        # components
        copiedGlyph.components = []
        if len(self.components) > 0:
            for baseName, transformation in self.components:
                xScale, xyScale, yxScale, yScale, xOffset, yOffset = transformation
                newXOffset, newYOffset = funct((xOffset, yOffset), factor)
                newXScale, newYScale = funct((xScale, yScale), factor)
                newXYScale, newYXScale = funct((xyScale, yxScale), factor)
                copiedGlyph.components.append((baseName, (newXScale, newXYScale, newYXScale, newYScale, newXOffset, newYOffset)))

    def __repr__(self):
        return "<MathGlyph %s>" % self.name

    def __cmp__(self, other):
        flag = False
        if self.name != other.name:
            flag = True
        if self.unicodes != other.unicodes:
            flag = True
        if self.width != other.width:
            flag = True
        if self.note != other.note:
            flag = True
        if self.lib != other.lib:
            flag = True
        if self.contours != other.contours:
            flag = True
        if self.components != other.components:
            flag = True
        if self.anchors != other.anchors:
            flag = True
        return flag

    def __add__(self, otherGlyph):
        copiedGlyph = self.copyWithoutIterables()
        self._processMathOne(copiedGlyph, otherGlyph, addPt)
        copiedGlyph.width = self.width + otherGlyph.width
        return copiedGlyph

    def __sub__(self, otherGlyph):
        copiedGlyph = self.copyWithoutIterables()
        self._processMathOne(copiedGlyph, otherGlyph, subPt)
        copiedGlyph.width = self.width - otherGlyph.width
        return copiedGlyph

    def __mul__(self, factor):
        if not isinstance(factor, tuple):
            factor = (factor, factor)
        copiedGlyph = self.copyWithoutIterables()
        self._processMathTwo(copiedGlyph, factor, mulPt)
        copiedGlyph.width = self.width * factor[0]
        return copiedGlyph

    __rmul__ = __mul__

    def __div__(self, factor):
        if not isinstance(factor, tuple):
            factor = (factor, factor)
        copiedGlyph = self.copyWithoutIterables()
        self._processMathTwo(copiedGlyph, factor, divPt)
        copiedGlyph.width = self.width / factor[0]
        return copiedGlyph

    __rdiv__ = __div__

    def drawPoints(self, pointPen):
        """draw self using pointPen"""
        for contour in self.contours:
            pointPen.beginPath()
            for segmentType, pt, smooth, name in contour:
                pointPen.addPoint(pt=pt, segmentType=segmentType, smooth=smooth, name=name)
            pointPen.endPath()
        for baseName, transformation in self.components:
            pointPen.addComponent(baseName, transformation)
        for pt, name in self.anchors:
            pointPen.beginPath()
            pointPen.addPoint(pt=pt, segmentType="move", smooth=False, name=name)
            pointPen.endPath()

    def draw(self, pen):
        """draw self using pen"""
        from robofab.pens.adapterPens import PointToSegmentPen
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def extractGlyph(self, glyph, pointPen=None):
        """
        "rehydrate" to a glyph. this requires
        a glyph as an argument. if a point pen other
        than the type of pen returned by glyph.getPointPen()
        is required for drawing, send this the needed point pen.
        """
        if pointPen is None:
            pointPen = glyph.getPointPen()
        glyph.clearContours()
        glyph.clearComponents()
        glyph.clearAnchors()
        glyph.lib.clear()
        #
        cleanerPen = FilterRedundantPointPen(pointPen)
        self.drawPoints(cleanerPen)
        #
        glyph.name = self.name
        glyph.unicodes = self.unicodes
        glyph.width = self.width
        glyph.note = self.note
        #
        for k, v in self.lib.items():
            glyph.lib[k] = v
        return glyph

    def isCompatible(self, otherGlyph, testContours=True, testComponents=False, testAnchors=False):
        """
        returns a True if otherGlyph is compatible with self.

        because absolute compatibility is not required for
        anchors and components in glyph math operations
        this method does not test compatibility on that data
        by default. set the flags to True to test for that data.
        """
        other = otherGlyph
        selfContourStructure, selfComponentStructure, selfAnchorStructure = self.structure
        otherContourStructure, otherComponentStructure, otherAnchorStructure = other.structure
        result = True
        if testContours:
            if selfContourStructure != otherContourStructure:
                result = False
        if testComponents:
            if selfComponentStructure != otherComponentStructure:
                result = False
        if testAnchors:
            if selfAnchorStructure != otherAnchorStructure:
                result = False
        return result

    def skewX(self, a):
        a = radians(a)

        contours = self.contours
        anchors = self.anchors
        components = self.components

        for contour in contours:
            for i, (segment, (x, y), smooth, name) in enumerate(contour):
                x = self._skewXByAngle(x, y, a)
                contour[i] = (segment, (x, y), smooth, name)

        for j, (baseGlyph, matrix) in enumerate(components):
            xx, yx, xy, yy, x, y = matrix
            x = self._skewXByAngle(x, y, a)
            components[j] = (baseGlyph, (xx, yx, xy, yy, x, y))

        for k, ((x, y), name) in enumerate(anchors):
            x = self._skewXByAngle(x, y, a)
            anchors[k] = ((x, y), name)

        self.contours = contours
        self.anchors = anchors
        self.components = components

    def _skewXByAngle(self, x, y, angle):
        return x + (y * tan(angle))