#coding=utf-8
from __future__ import division

'''
Custom CocoaPen that displays a glyph with OnCurve & OffCurve points
'''

from fontTools.pens.basePen import BasePen
from fontTools.pens.cocoaPen import CocoaPen
from robofab.pens.pointPen import AbstractPointPen

class CocoaGlyphPen(BasePen):

    def __init__(self, onCurveSize, offCurveSize, selection=[]):
        self.glyphPen = CocoaPen(None)
        self.glyphPath = self.glyphPen.path
        self.onCurvePen = CocoaPen(None)
        self.onCurvePoints = self.onCurvePen.path
        self.offCurvePen = CocoaPen(None)
        self.offCurvePoints = self.offCurvePen.path
        self.handleLinePen = CocoaPen(None)
        self.handleLines = self.handleLinePen.path
        self.selectedPen = CocoaPen(None)
        self.selectedPoints = self.selectedPen.path
        self.onCurveSize = onCurveSize
        self.offCurveSize = offCurveSize
        self.selection = selection

    def _moveTo(self, pt):
        self.glyphPen.moveTo(pt)
        self.drawOnCurve(pt)
        self.previousPoint = pt

    def _lineTo(self, pt):
        self.glyphPen.lineTo(pt)
        self.drawOnCurve(pt)
        self.previousPoint = pt

    def _curveToOne(self, pt1, pt2, pt3):
        self.glyphPen.curveTo(pt1, pt2, pt3)
        self.drawOffCurve(pt1)
        self.drawOffCurve(pt2)
        self.drawHandleLine(pt1, self.previousPoint)
        self.drawHandleLine(pt2, pt3)
        self.drawOnCurve(pt3)
        self.previousPoint = pt3

    def endPath(self):
        self.glyphPen.endPath()

    def closePath(self):
        self.glyphPen.closePath()

    def addComponent(self, baseName, transform):
        pass

    def drawOnCurve(self, pt, selection=False):
        if pt in self.selection:
            cocoaPen = self.selectedPen
        else:
            cocoaPen = self.onCurvePen
        size = self.onCurveSize
        x, y = pt
        cocoaPen.moveTo((x - size, y - size))
        cocoaPen.lineTo((x + size, y - size))
        cocoaPen.lineTo((x + size, y + size))
        cocoaPen.lineTo((x - size, y + size))
        cocoaPen.lineTo((x - size, y - size))
        cocoaPen.closePath()

    def drawOffCurve(self, pt, selection=False):
        if pt in self.selection:
            cocoaPen = self.selectedPen
        else:
            cocoaPen = self.offCurvePen
        size = self.offCurveSize
        x, y = pt
        cocoaPen.moveTo((x, y - size))
        cocoaPen.lineTo((x + size, y ))
        cocoaPen.lineTo((x, y + size))
        cocoaPen.lineTo((x - size, y ))
        cocoaPen.lineTo((x, y - size))
        cocoaPen.closePath()
        cocoaPen.closePath()

    def drawHandleLine(self, pt1, pt2):
        cocoaPen = self.handleLinePen
        x, y = pt1
        xa, ya = pt2
        cocoaPen.moveTo((xa, ya))
        cocoaPen.lineTo((x, y))

from math import floor, cos, sin, hypot, pi, atan2, degrees
from robofab.pens.filterPen import thresholdGlyph
from robofab.objects.objectsRF import RGlyph, RPoint
from mojo.drawingTools import fill, stroke, rect, oval, save, restore, text, scale, fontSize
from mojo.UI import CurrentGlyphWindow
from AppKit import NSColor
from lib.tools.bezierTools import intersectCubicCubic, intersectCubicLine, intersectLineLine
from robofab.misc.bezierTools import solveCubic
from time import time
from copy import deepcopy

'''
Two utility methods borrowed from Frederik Berlaen’s Outliner
'''

def roundFloat(f):
    error = 1000000.
    return round(f*error)/error

def pointOnACurve((x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2), value):
    dx = x1
    cx = (cx1 - dx) * 3.0
    bx = (cx2 - cx1) * 3.0 - cx
    ax = x2 - dx - cx - bx
    dy = y1
    cy = (cy1 - dy) * 3.0
    by = (cy2 - cy1) * 3.0 - cy
    ay = y2 - dy - cy - by
    mx = ax*(value)**3 + bx*(value)**2 + cx*(value) + dx
    my = ay*(value)**3 + by*(value)**2 + cy*(value) + dy
    return mx, my

'''
Other custom utility methods
'''

def flattenAngle(a, threshold=3, mode='both'):
    th = threshold
    if mode in ['horizontal', 'both']:
        if (cos(a)) > cos(th/180*pi):
            a = 0
        elif (cos(a)) < cos((180-th)/180*pi):
            a = pi
    if mode in ['vertical', 'both']:
        if (sin(a)) > sin((90-th)/180*pi):
            a = pi/2
        elif (sin(a)) < sin((270-th)/180*pi):
            a = 3*pi/2
    return a

# Used mostly for testing purposes
def highlight(point):
    from mojo.UI import CurrentGlyphWindow
    s = CurrentGlyphWindow().getGlyphViewScale()
    save()
    scale(s)
    fill(0, .8, 0, 0.5)
    oval(point.x-(10/s), point.y-(10/s), 20/s, 20/s)
    restore()

# Used mostly for testing purposes
def screenPrint(string, (x, y)):
    from mojo.UI import CurrentGlyphWindow
    s = CurrentGlyphWindow().getGlyphViewScale()
    save()
    fill(0, .8, 0, 0.75)
    stroke()
    fontSize(12/s)
    text(string, (x+(5/s), y+(5/s)))
    restore()

'''
Custom Point object implementation to ease point contour manipulation.
Those IntelPoints are meant to be children of an IntelContour.
'''

from pointLabelDict import PointLabelDict

class IntelPoint(object):

    def __init__(self, pt, segmentType=None, smooth=False, name=None, index=0, onCurveIndex=None, selected=False):
        self.x, self.y = pt
        if segmentType == 'offCurve': self.segmentType = None
        else: self.segmentType = segmentType
        self.smooth = smooth
        self.name = name
        self.index = index
        self.onCurveIndex = None
        self.parentContour = None
        self.parentPoint = None
        self.toRemove = False
        self.selected = selected
        self.labels = PointLabelDict(name)

    def __repr__(self): #### print p
        return "<IntelPoint x:%s y:%s %s>" %(self.x, self.y, self.segmentType)

    def __setitem__(self, index, value):
        if index == 0:
            if isinstance(value, (int, float)):
                self.x = value
            else: raise ValueError
        elif index == 1:
            if isinstance(value, (int, float)):
                self.y = value
            else: raise ValueError
        raise IndexError

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError

    def __iter__(self):
        for value in [self.x, self.y]:
            yield value

    def __add__(self, p): # p+ p
        return self.mathOperate(p, 'add')

    __radd__ = __add__

    def __sub__(self, p): #p - p
        return self.mathOperate(p, 'sub')

    __rsub__ = __sub__

    def __mul__(self, p): ## p * p
        return self.mathOperate(p, 'mul')

    __rmul__ = __mul__

    def __div__(self, p):
        return self.mathOperate(p, 'div')

    __rdiv__ = __truediv__ = __rtruediv__ = __div__

    def __eq__(self, p): ## if p == p
        if not isinstance(p, self.__class__):
            return False
        return (int(p.x-1) < int(self.x) < int(p.x+1)) and (int(p.y-1) < int(self.y) < int(p.y+1)) and (self.segmentType == p.segmentType)

    def __ne__(self, p): ## if p != p
        return not self.__eq__(p)

    def __lt__(self, p): ## if p < p
        return self.index < p.index

    def __gt__(self, p): ## if p < p
        return self.index > p.index

    def mathOperate(self, p, operation):
        newX, newY = 0, 0
        x, y = None, None
        if isinstance(p, (float, int)):
            x, y = p, p
        elif isinstance(p, (self.__class__, tuple, list)):
            x, y = p[0], p[1]
        if (x, y) != (None, None):
            if operation == 'add':
                newX = self.x + x
                newY = self.y + y
            elif operation == 'sub':
                newX = self.x - x
                newY = self.y - y
            elif operation == 'mul':
                newX = self.x * x
                newY = self.y * y
            elif operation == 'div':
                newX = self.x / x
                newY = self.y / y
            return self.__class__((newX, newY), self.segmentType, self.smooth)
        raise ValueError

    def move(self, (mx, my)):
        self.x += mx
        self.y += my

    def rotate(self, angle, (rx, ry)):
        xDelta = self.x - rx
        yDelta = self.y - ry
        d = hypot(xDelta, yDelta)
        a = atan2(yDelta, xDelta)
        nx = rx + (d * cos(a-angle))
        ny = ry + (d * sin(a-angle))
        self.x, self.y = nx, ny

    def asRPoint(self):
        return RPoint(self.x, self.y, self.segmentType)

    def coords(self):
        return (self.x, self.y)

    def copy(self):
        return self.__class__((self.x, self.y), self.segmentType, self.smooth, self.name, self.index)

    def round(self):
        x, y = int(round(self.x)), int(round(self.y))
        self.x, self.y = x, y
        return x, y

    '''
    Return two points on each side of this one, following the outline’s path.
    Can be useful for a number of applications.
    '''
    def split(self, radius, angle1=None, angle2=None):
        if angle1 is None:
            angle1 = self.incomingDirection()
        if angle2 is None:
            angle2 = self.direction()
        a1 = self.derive(angle1, -radius)
        a2 = self.derive(angle2, radius)
        return a1, a2

    '''
    making it easy to modify length of an anchor-offCurve distance (e.g point.lengthen(2) = x2)
    '''
    def lengthen(self, value):
        if (self.segmentType is None):
            anchor = self.anchor()
            d = self.distance(anchor)
            direction = None
            if anchor > self:
                d = -d
                direction = self.direction()
            elif anchor < self:
                direction = self.incomingDirection()
            if direction is not None:
                self.x, self.y = self.polarCoord(direction, d*value, anchor)

    def setParentContour(self, contour):
        self.parentContour = contour

    def getParentContour(self):
        return self.parentContour

    def setParentPoint(self, point):
        self.parentPoint = point

    def getParentPoint(self):
        return self.parentPoint

    def overlap(self, point, margin=2):
        m = margin
        return (floor(point.x) - m <= floor(self.x) <= floor(point.x) + m) and (floor(point.y) - m <= floor(self.y) <= floor(point.y) + m)

    # measure distance with another point
    def distance(self, p):
        ox, oy = p
        return hypot(ox - self.x, oy - self.y)

    # get new coordinates in a ‘polar’ manner, from this point with given distance & angle
    def polarCoord(self, angle, distance, pt=None):
        if pt is None:
            x, y = self.x, self.y
        elif pt is not None:
            x, y = pt
        return x + (distance*cos(angle)), y + (distance*sin(angle))

    # return a new Point translated by distance + angle
    def derive(self, angle, distance):
        derivedPoint = self.__class__(self.polarCoord(angle, distance), self.segmentType, self.smooth, None)
        derivedPoint.setParentPoint(self)
        derivedPoint.setParentContour(self.parentContour)
        return derivedPoint

    # interpolate x,y coordinates
    def interpolate(self, otherPoint, f):
        x1, y1 = self.x, self.y
        x2, y2 = otherPoint[0], otherPoint[1]
        nx = x1 + (x2-x1)*f
        ny = y1 + (y2-y1)*f
        return (nx, ny)

    # interpolate point coordinates and return a new IntelPoint with new coordinates
    def interpolatePoint(self, otherPoint, f, segmentType=None, smooth=False):
        return self.__class__(self.interpolate(otherPoint, f), segmentType=segmentType, smooth=smooth)

    # measure angle of the line formed with another point, radians
    def angle(self, other):
        x = other.x - self.x
        y = other.y - self.y
        return atan2(y, x)

    def velocity(self):
        if self.segmentType is None:
            anchor = self.anchor()
            anchors = self.curveAnchors()
            d = anchors[0].distance(anchors[1])
            a = self.handleAngle()
            if a is not None:
                if abs(cos(a)) != cos(pi/2):
                    velocity = (3 * (self.x-anchor.x)) / (d * cos(a))
                elif abs(sin(a)) != cos(pi/2):
                    velocity = (3 * (self.y-anchor.y)) / (d * sin(a))
                return velocity
        elif self.segmentType is not None:
            handles = self.handles()
            velocity = ()
            if len(handles) > 0:
                for handle in handles:
                    velocity += (handle.velocity(),)
                return velocity
        return 0

    def previous(self):
        assert self.parentContour is not None
        return self.parentContour.getPrevious(self)

    def previousOnCurve(self):
        assert self.parentContour is not None
        return self.parentContour.getPreviousOncurve(self)

    def next(self):
        assert self.parentContour is not None
        return self.parentContour.getNext(self)

    def nextOnCurve(self):
        assert self.parentContour is not None
        return self.parentContour.getNextOncurve(self)

    def direction(self):
        assert self.parentContour is not None
        return self.parentContour.getForwardDirection(self)

    def incomingDirection(self):
        assert self.parentContour is not None
        return self.parentContour.getBackwardDirection(self)

    def offCurveDistAngle(self):
        assert self.parentContour is not None
        if self.segmentType is None:
            anchor = self.anchor()
            d = self.distance(anchor)
            a = 0
            if anchor > self:
                a = self.direction()
            elif anchor < self:
                a = self.incomingDirection()
            return (anchor, d, a)
        return

    # def pivotAngle(self):
    #     assert self.parentContour is not None
    #     turn = self.turn()
    #     direction = self.incomingDirection()
    #     pivotAngle = direction + (turn/2) + (pi/2)

    #     return

    def pivotAngle(self):
        assert self.parentContour is not None
        turn = self.turn()
        direction = self.incomingDirection()
        return direction + (turn/2) + (pi/2)

    def turn(self):
        assert self.parentContour is not None
        return self.parentContour.getTurn(self)

    def anchor(self):
        assert self.parentContour is not None
        if self.segmentType is None:
            return self.parentContour.getAnchor(self)
        return

    def curveAnchors(self):
        assert self.parentContour is not None
        if self.segmentType is None:
            return self.parentContour.getCurveAnchors(self)
        return

    def curve(self):
        assert self.parentContour is not None
        return self.parentContour.getCurve(self)

    def arc(self):
        assert self.parentContour is not None
        if self.segmentType is not None:
            return self.parentContour.getArc(self)
        return

    def handles(self):
        assert self.parentContour is not None
        if self.segmentType is not None:
            return self.parentContour.getHandles(self)
        return

    def handleAngle(self):
        assert self.parentContour is not None
        return self.parentContour.getHandleAngle(self)

    def isFirst(self):
        assert self.parentContour is not None
        return self == self.parentContour.getFirst()

    def isLast(self):
        assert self.parentContour is not None
        return self == self.parentContour.getLast()

'''
Custom Contour object implementation
to ease point manipulation based on their attributes
and those of their surroundings.
An IntelContour is the object informing IntelPoints
of their context, through methods like self.getNext(point).

Once operations on the points of a contour are done,
the IntelContour can send back a usual path
through the use of the draw(pen) method,
working in the same way it does for robofab Glyphs & contours.
'''

class IntelContour(object):

    _pointClass = IntelPoint

    def __init__(self, baseContour=None, index=0):
        super(IntelContour, self).__init__()
        self.points = []
        self._source = baseContour
        if baseContour is not None:
            self.processContour(baseContour)
        self.index = index
        self.clockwise = self.isClockwise()

    def __repr__(self): #### print p
        return "<IntelContour points:%s>" %(len(self.points))

    def __len__(self):
        return len(self.points)

    def __setitem__(self, index, point):
        if index < self.length():
            if isinstance(point, self._pointClass):
                self.points[index] = point
            else: raise ValueError
        else:
            raise IndexError

    def __getitem__(self, index):
        if index < self.length():
            return self.points[index]
        raise IndexError

    def __iter__(self):
        for value in self.points:
            yield value

    def __add__(self, otherOutline):
        if isinstance(otherOutline, self.__class__):
            newContour = self.__class__()
            if otherOutline.points[0].segmentType == 'move':
                if self.points[-1].segmentType is None:
                    otherOutline.points[0].segmentType = 'curve'
                else:
                    otherOutline.points[0].segmentType = 'line'
            newContour.points = self.points + otherOutline.points
            newContour.checkSanity()
            return newContour
        if not isinstance(otherOutline, self.__class__):
            return

    def move(self, (mx, my)):
        for point in self.points:
            point.move((mx, my))

    def rotate(self, angle, origin=(0, 0)):
        for point in self.points:
            point.rotate(angle, origin)

    def round(self):

        self.updateIndices()

        for point in self.points:
            if point.segmentType is None:
                anchor, distance, angle = point.offCurveDistAngle()
                angle = flattenAngle(angle)
                x, y = anchor.round()
                if abs(sin(angle)) == sin(pi/2):
                    point.x = x
                elif abs(sin(angle)) == sin(0):
                    point.y = y
            point.round()

    def asList(self):
        return [{'x':point[0], 'y':point[1], 'type':point.segmentType, 'smooth':point.smooth} for point in self.points]

    '''
    Method use in case the IntelContour object is iniated with a RContour directly
    '''
    def processContour(self, contour):
        length = len(contour)
        if length:
            anchors = []
            for point in contour.points:
                # filter out anchors
                if (length == 1) and (point.name is not None):
                    pointLabels = point.name.split(',')
                    anchors = list(set(pointLabels) & set(['top', 'bottom', 'right', 'mid', 'left', 'circum']))
                if (length > 1) and len(anchors) == 0:
                    self.append(point)

            self.cleanCurves()

    def append(self, point):

        PointClass = self._pointClass

        if isinstance(point, PointClass):
            iPoint = point
            iPoint.setParentContour(self)
            iPoint.index = self.length()
            self.points.append(iPoint)
        else:
            selected = False
            if hasattr(point, 'selected'):
                selected = point.selected
            try:
                iPoint = PointClass(point['pt'], point['segmentType'], point['smooth'], point['name'], index=self.length(), onCurveIndex=self.shortLength(), selected=selected)
            except:
                try:
                    iPoint = PointClass((point.x, point.y), point.type, point.smooth, point.name, index=self.length(), onCurveIndex=self.shortLength(), selected=selected)
                except:
                    return

            iPoint.setParentContour(self)
            self.points.append(iPoint)

    def insert(self, index, point):

        PointClass = self._pointClass

        if isinstance(point, PointClass):
            iPoint = point
        else:
            try:
                iPoint = PointClass(point['pt'], point['segmentType'], point['smooth'], point['name'], self.length())
            except:
                try:
                    iPoint = PointClass((point.x, point.y), point.type, point.smooth, point.name, self.length())
                except:
                    return
        iPoint.setParentContour(self)
        self.points.insert(index, point)

        self.updateIndices(index)

    def pop(self, index=None):
        if index is None:
            return self.points.pop()
        poppedPoint = self.points.pop(index)
        self.updateIndices(index)
        return poppedPoint

    def remove(self, point):
        if point in self.points:
            self.points.remove(point)

    def reverse(self):
        self.points.reverse()
        self.clockwise = not self.clockwise
        self.checkSanity()

    def length(self):
        return len(self.points)

    def shortLength(self):
        points = self.points
        return len([point for point in points if point.segmentType is not None])

    def orderDelta(self, point1, point2, ignoreOffcurves=False):
        if ignoreOffcurves:
            l = self.shortLength()
            p1i = point1.onCurveIndex
            p2i = point2.onCurveIndex
        elif not ignoreOffcurves:
            l = self.length()
            p1i = point1.index
            p2i = point2.index
        d = abs((p2i%l)-(p1i%l))
        if p1i+d > l:
            d = abs(d-l)
        return d

    def isClosed(self):
        if self.length() == 0:
            return False
        return not self.points[0].segmentType == 'move'

    def close(self):
        if (not self.isClosed()) and (self.length() > 0):
            if self.points[-1].segmentType is None:
                self.points[0].segmentType = 'curve'
            elif self.points[-1].segmentType is not None:
                self.points[0].segmentType = 'line'

    def isClockwise(self):
        points = self.points
        if len(points):
            # overlapping moves can give false results, so filter them out
            if points[0] == points[-1]:
                del points[-1]
            angles = []
            total = 0
            pointCount = len(points)

            for index1 in xrange(pointCount):
                index2 = (index1 + 1) % pointCount
                x1, y1 = points[index1]
                x2, y2 = points[index2]
                total += (x1*y2)-(x2*y1)

            return total < 0

    def getSelection(self):
        return [point for point in self.points if point.selected]

    def getPrevious(self, point):
        if (point.index == 0) and (not self.isClosed()):
            return
        else:
            index = (point.index - 1) % self.length()
            return self.points[index]

    def getNext(self, point):
        if (point.index == self.length()-1) and (not self.isClosed()):
            return
        else:
            index = (point.index + 1) % self.length()
            return self.points[index]

    def getLast(self):
        return self.points[-1]

    def getFirst(self):
        return self.points[0]

    def getPreviousOncurve(self, point):
        for i in range(self.length()):
            previousPoint = self.getPrevious(point)
            if previousPoint is None:
                return
            if previousPoint.segmentType is not None:
                return previousPoint
            point = previousPoint

    def getNextOncurve(self, point):
        for i in range(self.length()):
            nextPoint = self.getNext(point)
            if nextPoint is None:
                return
            if nextPoint.segmentType is not None:
                return nextPoint
            point = nextPoint

    def getAnchor(self, point):
        if point.segmentType is None:
            previousPoint = self.getPrevious(point)
            nextPoint = self.getNext(point)
            if (previousPoint is not None) and (previousPoint.segmentType is not None):
                return previousPoint
            elif (nextPoint is not None) and (nextPoint.segmentType is not None):
                return nextPoint
        return point

    def getHandles(self, point):
        if point.segmentType is not None:
            handles = []
            previousPoint = self.getPrevious(point)
            nextPoint = self.getNext(point)
            for p in [previousPoint, nextPoint]:
                if (p is not None) and (p.segmentType is None):
                    handles.append(p)
            return handles
        return

    def getCurveAnchors(self, point):
        if point.segmentType is None:
            firstAnchor = self.getPreviousOncurve(point)
            secondAnchor = self.getNextOncurve(point)
            return [p for p in [firstAnchor, secondAnchor] if p is not None]
        return

    def getCurve(self, point):
        segment = []
        firstAnchor = None
        secondAnchor = None

        if point.segmentType is None:
            firstAnchor = self.getPreviousOncurve(point)
            secondAnchor = self.getNextOncurve(point)
        elif (point.segmentType is not None) and (self.getNext(point) is not None) and (self.getNext(point).segmentType is None):
            firstAnchor = point
            secondAnchor = self.getNextOncurve(point)
        segment.append(firstAnchor)

        if firstAnchor is not None:
            firstAnchorHandles = self.getHandles(firstAnchor)
            if firstAnchorHandles is not None:
                for handle in firstAnchorHandles:
                    if (handle > firstAnchor) and (handle != self.getLast()):
                        segment.append(handle)
                    elif (handle == self.getFirst()) and (firstAnchor == self.getLast()):
                        segment.append(handle)

        if secondAnchor is not None:
            secondAnchorHandles = self.getHandles(secondAnchor)
            if secondAnchorHandles is not None:
                for handle in secondAnchorHandles:
                    if (handle < secondAnchor) and (handle != self.getFirst()):
                        segment.append(handle)
                    elif (handle == self.getLast()) and (secondAnchor == self.getFirst()):
                        segment.append(handle)

        segment.append(secondAnchor)

        return [p for p in segment if p is not None]

    def getArc(self, point):
        if point.segmentType is not None:
            handles = self.getHandles(point)
            if (len(handles) == 2) and ((self.getNextOncurve(point) is not None) and (self.getPreviousOncurve(point) is not None)):
                segment1 = self.getCurve(handles[0])
                segment2 = self.getCurve(handles[1])
                return segment1[:3] + segment2
        return

    def getForwardDirection(self, point):
        referencePoint = self.getNext(point)
        if referencePoint is None:
            referencePoint = self.getPrevious(point)
            if referencePoint is not None:
                return referencePoint.angle(point)
        elif referencePoint is not None:
            return point.angle(referencePoint)
        return

    def getBackwardDirection(self, point):
        referencePoint = self.getPrevious(point)
        if referencePoint is None:
            referencePoint = self.getNext(point)
            if referencePoint is not None:
                return point.angle(referencePoint)
        elif referencePoint is not None:
            return referencePoint.angle(point)
        return

    def getTurn(self, point):
        inAngle = self.getBackwardDirection(point)
        outAngle = self.getForwardDirection(point)
        if (inAngle is not None) and (outAngle is not None):
            return self.delta(inAngle, outAngle)
        return 0

    def getHandleAngle(self, point):
        if point.segmentType is None:
            anchor = self.getAnchor(point)
            if anchor != point:
                return anchor.angle(point)
        elif point.segmentType is not None:
            handles = self.getHandles(point)
            handleAngles = []
            if len(handles) == 0:
                return
            elif len(handles) > 0:
                for handle in handles:
                    if handle > point:
                        handleAngles.append(point.angle(handles[1]))
                    elif handle < point:
                        handleAngles.append(point.angle(handles[0]))
                return handleAngles
        return

    def delta(self, angle1, angle2):
        delta = angle2 - angle1
        if delta > pi: delta -= 2*pi
        elif delta < -pi: delta += 2*pi
        return delta

    def midAngle(self, angle1, angle2):
        delta = self.delta(angle1, angle2)
        return delta / 2

    # Source: Frederik Berlaen, Outliner
    @classmethod
    def intersectLineLine(self, seg1s, seg1e, seg2s, seg2e):
        denom = (seg2e[1] - seg2s[1]) * (seg1e[0] - seg1s[0]) - (seg2e[0] - seg2s[0]) * (seg1e[1] - seg1s[1])
        if roundFloat(denom) == 0:
            #print 'parallel: %s' % denom
            return None, None
        uanum = (seg2e[0] - seg2s[0])*(seg1s[1] - seg2s[1]) - (seg2e[1] - seg2s[1])*(seg1s[0] - seg2s[0])
        ubnum = (seg1e[0] - seg1s[0])*(seg1s[1] - seg2s[1]) - (seg1e[1] - seg1s[1])*(seg1s[0] - seg2s[0])
        ua = uanum/denom
        ub = ubnum/denom
        x = seg1s[0] + ua*(seg1e[0] - seg1s[0])
        y = seg1s[1] + ua*(seg1e[1] - seg1s[1])
        return x, y

    def collectSegments(self, points=None):

        if points is None:
            points = self.points

        segments = {'all':[], 'curves':[], 'lines':[], 'selection':[]}

        for point in points:

            if (point.segmentType is None): continue

            nextPoint = self.getNext(point)

            if nextPoint is not None:
                if nextPoint.segmentType is None:
                    segment = self.getCurve(point)
                    if len(segment) == 4:
                        segments['curves'].append(segment)
                elif nextPoint.segmentType is not None:
                    segment = [point, nextPoint]
                    segments['lines'].append(segment)
                segments['all'].append(segment)
                if segment[0].selected and segment[-1].selected:
                    segments['selection'].append(segment)

        return segments

    def cleanCurves(self):

        self.updateIndices()
        curveSegments = self.collectSegments()['curves']
        offCurvesToPop = []
        offCurvesToReplace = []

        for segment in curveSegments:
            cleanSegment = self.cleanCurveSegment(segment)
            if len(cleanSegment) == 2:
                offCurvesToPop.append(segment[1])
                offCurvesToPop.append(segment[2])
                self.points[segment[3].index].segmentType = 'line'
            elif len(cleanSegment) == 4:
                offCurvesToReplace.append(cleanSegment[1])
                offCurvesToReplace.append(cleanSegment[2])

        for offCurve in offCurvesToReplace:
            self.points[offCurve.index] = offCurve

        for i, offCurve in enumerate(offCurvesToPop):
            if offCurve in self.points:
                self.points.remove(offCurve)

        self.checkSanity()

    '''
    Method that limits potential handle-crossing. Changes outline, obviously.
    '''

    def constrainOffcurves(self):

        curveSegments = self.collectSegments()['curves']

        for segment in curveSegments:
            h1, h2 = segment[1], segment[2]
            i1, i2 = h1.index, h2.index
            (h1.x, h1.y), (h2.x, h2.y) = self.constrainSegmentOffcurves(*segment)
            self.points[i1] = h1
            self.points[i2] = h2

    def constrainSegmentOffcurves(self, a1, h1, h2, a2):
        ax1, ay1 = a1
        hx1, hy1 = h1
        hx2, hy2 = h2
        ax2, ay2 = a2

        ix, iy = self.intersectLineLine(a1, h1, h2, a2)

        if (ix != None) and (iy != None):

            d1 = hypot(hx1-ax1, hy1-ay1)
            di1 = hypot(ix-ax1, iy-ay1)
            if d1 >= di1:
                t1 = atan2(hy1-ay1, hx1-ax1)
                hx1 = ax1 + 0.99*di1*cos(t1)
                hy1 = ay1 + 0.99*di1*sin(t1)

            d2 = hypot(hx2-ax2, hy2-ay2)
            di2 = hypot(ix-ax2, iy-ay2)
            if d2 >= di2:
                t2 = atan2(hy2-ay2, hx2-ax2)
                hx2 = ax2 + 0.99*di2*cos(t2)
                hy2 = ay2 + 0.99*di2*sin(t2)

        return (round(hx1), round(hy1)), (round(hx2), round(hy2))

    '''
    Checks for contour sanity, no illegal segmentTypes and such.
    '''

    def checkSanity(self):

        self.updateIndices()

        points = self.points
        closed = self.isClosed()

        if len(points) > 0:

            # check closed contour starts with a OnCurve point
            if closed:
                if points[0].segmentType is None:
                    points.insert(0, points.pop())
                if points[-1].segmentType is None:
                    points[0].segmentType = 'curve'

            if not closed:
                points[0].segmentType = 'move'

            for i, point in enumerate(points):

                previousPoint = points[(i-1)%len(points)]
                nextPoint = points[(i+1)%len(points)]

                # segmentType legality
                if i == 0:
                    if (not closed and (point.segmentType == 'curve')) or \
                       (closed and (point.segmentType == 'curve') and (self.getLast().segmentType is not None)):
                        point.segmentType = 'line'
                if i > 0:
                    if point.segmentType in ['curve', 'move'] and previousPoint.segmentType is not None:
                        point.segmentType = 'line'
                    elif point.segmentType in ['line','move'] and previousPoint.segmentType is None:
                        point.segmentType = 'curve'
                    elif point.segmentType is None and previousPoint.segmentType is not None and nextPoint.segmentType is not None:
                        point.segmentType = 'line'

        self.points = points
        self.updateIndices()

    def correctSmoothness(self):

        points = self.points
        length = len(points)
        closed = self.isClosed()

        for i, point in enumerate(points):

            previousPoint = points[(i-1)%length]
            nextPoint = points[(i+1)%length]

            # if (point.smooth) and (abs(round(point.turn()*100)/100) > 0.07) and (abs(point.turn()) < (3*pi/8)):

            if (abs(point.turn()) < (10/180*pi)) or (point.smooth and abs(point.turn()) < (60/180*pi)):

                if (point.segmentType in ['curve', 'line']) and ((not closed and (not point.isFirst()) and (not point.isLast())) or closed):

                    if (previousPoint.segmentType is None) and (nextPoint.segmentType is not None):

                        d = point.distance(previousPoint)
                        a = point.direction()
                        # a = flattenAngle(a)
                        previousPoint.x, previousPoint.y = point.polarCoord(a, -d)

                    elif (previousPoint.segmentType is not None) and (nextPoint.segmentType is None):

                        d = point.distance(nextPoint)
                        a = point.incomingDirection()
                        # a = flattenAngle(a)
                        nextPoint.x, nextPoint.y = point.polarCoord(a, d)

                    elif (previousPoint.segmentType is None) and (nextPoint.segmentType is None):

                        d0 = point.distance(previousPoint)
                        a0 = flattenAngle(point.incomingDirection())
                        d1 = point.distance(nextPoint)
                        a1 = flattenAngle(point.direction())
                        a = flattenAngle((a0+a1)/2)

                        previousPoint.x, previousPoint.y = point.polarCoord(a, -d0)
                        nextPoint.x, nextPoint.y = point.polarCoord(a, d1)

                    point.smooth = True

        self.points = points

    def removeOverlappingPoints(self):

        self.updateIndices()
        points = self.points
        length = len(points)
        pointsToRemove = []

        for i, point in enumerate(points):

            previousPoint = points[(i-1)%length]
            nextPoint = points[(i+1)%length]

            if point.segmentType is None:
                anchor = point.anchor()
                if anchor.overlap(point):
                    nextOffCurve = nextPoint
                    nextAnchor = nextOffCurve.anchor()
                    if (nextAnchor is not None) and (nextAnchor.overlap(nextOffCurve)):
                        pointsToRemove.append(point)
                        pointsToRemove.append(nextOffCurve)
                        nextAnchor.segmentType = 'line'

            elif point.segmentType is not None:
                if point.overlap(nextPoint) and (nextPoint.segmentType is not None):
                    pointsToRemove.append(nextPoint)

        for point in reversed(pointsToRemove):
            points.remove(point)

        self.points = points
        self.cleanCurves()

    '''
    Method of crucial importance.
    As this set of objects is meant to help outline manipulation,
    indices, order of contours/points that is, are essential.
    Most intervention that will alter the outline will also mess with indices,
    hence the need for this method to reorder objects before the next operation.
    I suppose there could be a cleaner way to do this, but if there is I’m not there yet.
    '''

    def updateIndices(self, index=None):
        if index is None:
            points = self.points
        elif index is not None:
            points = self.points[index:]

        offCurveCount = 0

        for i, point in enumerate(points):
            point.index = i
            if point.segmentType is None:
                offCurveCount += 1
            elif point.segmentType is not None:
                point.onCurveIndex = i-offCurveCount

    '''
    The following methods do what it says on the bottle.
    Beware though, mostly costly operations.
    '''

    def getExtrema(self):

        curveSegments = self.collectSegments()['curves']
        extrema = []

        for segment in curveSegments:
            pt0, pt1, pt2, pt3 = segment
            segmentExtrema = self.findSegmentExtrema(pt0, pt1, pt2, pt3)
            extrema += segmentExtrema

        return extrema


# for a quadratic curve
# need to find/deduce the equivalent for cubic
# c10 = (x - x1)*(y - y0) - (x - x0)*(y - y1)
# c20 = (x - x2)*(y - y0) - (x - x0)*(y - y2)
# t = c10/(c10 - 0.5*c20)

# found here: http://math.stackexchange.com/questions/889996/finding-parametric-distance-on-quadratic-curve-from-given-x-y-point

    def addExtrema(self):

        curveSegments = self.collectSegments()['curves']
        segmentsToAdd = []

        for segment in curveSegments:
            startIndex, newSegment = self.addExtremaOnSegment(segment)
            if newSegment is not None:
                segmentsToAdd.append((startIndex, newSegment))

        addedPointsCount = 0

        for start, newSegment in segmentsToAdd:
            index = start + 1 + addedPointsCount
            for i in range(2):
                self.pop(index)
            for p in reversed(newSegment):
                p.round()
                self.insert(index, p)
                addedPointsCount += 1
            addedPointsCount -= 2

        self.updateIndices()


    # def addExtrema(self):

    #     curveSegments = self.collectSegments()['curves']
    #     segmentsToAdd = []

    #     for segment in curveSegments:
    #         pt0, pt1, pt2, pt3 = segment
    #         startPoint, endPoint = pt0, pt3
    #         segmentExtrema = self.findSegmentExtrema(pt0, pt1, pt2, pt3)
    #         newSegment = [startPoint]
    #         startIndex = startPoint.index

    #         if len(segmentExtrema) > 0:
    #             for i, ((x, y), t) in enumerate(segmentExtrema):

    #                 if i == 0:
    #                     newSegment += self.splitSegmentAtT(pt0, pt1, pt2, pt3, (x,y), t)

    #                 elif i > 0:
    #                     segmentExtrema = self.findSegmentExtrema(*previousModifiedSegment)
    #                     (x, y), t = segmentExtrema[0]

    #                     pt0, pt1, pt2, pt3 = previousModifiedSegment
    #                     newSegment = newSegment[:-2] + self.splitSegmentAtT(pt0, pt1, pt2, pt3, (x,y), t)

    #                 previousModifiedSegment = newSegment[-3:] + [endPoint]

    #             newSegment.pop(0)
    #             if len(newSegment):
    #                 segmentsToAdd.append((startIndex, newSegment))

    #     addedPointsCount = 0

    #     for start, newSegment in segmentsToAdd:
    #         index = start + 1 + addedPointsCount
    #         for i in range(2):
    #             self.pop(index)
    #         for p in reversed(newSegment):
    #             p.round()
    #             self.insert(index, p)
    #             addedPointsCount += 1
    #         addedPointsCount -= 2

    #     self.updateIndices()

    def addExtremaOnSegment(self, segment):
        pt0, pt1, pt2, pt3 = segment
        startPoint, endPoint = pt0, pt3
        segmentExtrema = self.findSegmentExtrema(pt0, pt1, pt2, pt3)
        newSegment = [startPoint]
        startIndex = startPoint.index

        if len(segmentExtrema) > 0:
            for i, ((x, y), t) in enumerate(segmentExtrema):

                if i == 0:
                    newSegment += self.splitSegmentAtT(pt0, pt1, pt2, pt3, (x,y), t)

                elif i > 0:
                    segmentExtrema = self.findSegmentExtrema(*previousModifiedSegment)
                    (x, y), t = segmentExtrema[0]

                    pt0, pt1, pt2, pt3 = previousModifiedSegment
                    newSegment = newSegment[:-2] + self.splitSegmentAtT(pt0, pt1, pt2, pt3, (x,y), t)

                previousModifiedSegment = newSegment[-3:] + [endPoint]

            newSegment.pop(0)
            if len(newSegment):
                return startIndex, newSegment
        return None, None

    def splitSegmentAtT(self, pt0, pt1, pt2, pt3, (x, y), t):
        PointClass = self._pointClass
        m1 = pt0.interpolatePoint(pt1, t)
        m2 = pt1.interpolatePoint(pt2, t)
        m3 = pt2.interpolatePoint(pt3, t)
        h1 = m1.interpolatePoint(m2, t)
        h2 = m2.interpolatePoint(m3, t)
        a = PointClass((x, y), segmentType='curve', smooth=True)
        return [m1, h1, a, h2, m3]

    def findSegmentExtrema(self, pt0, pt1, pt2, pt3):

        z = pt0.distance(pt1) + pt1.distance(pt2) + pt2.distance(pt3)

        extrema = []
        prevBx = pt0[0]
        prevBy = pt0[1]
        xMove = None
        yMove = None
        moves = []

        for i in range(0, int(z)):

            t = i / z
            bx, by = pointOnACurve(pt0, pt1, pt2, pt3, t)

            if 0 < t < 1:
                if ((xMove is not None) and (xMove != (prevBx - bx > 0))) or ((yMove is not None) and (yMove != (prevBy - by > 0))):
                    if pt0.distance((bx,by)) > 5 and pt3.distance((bx,by)) > 5:
                        extrema.append(((bx, by), t))
                xMove = prevBx - bx > 0
                yMove = prevBy - by > 0
            prevBx = bx
            prevBy = by
        return extrema

    '''
    THIS METHOD IS BAD… DON’T USE IT, NEEDS TO BE REWRITTEN

    def removeUnecessaryOnCurves(self):

        points = self.points
        pointsToRemove = []
        pointsToRedefine = []
        le = len(points)

        for i, point in enumerate(points):

            previousPoint = points[(i-1)%le]
            nextPoint = points[(i+1)%le]

            if (point.segmentType == 'curve') and (point.toRemove) and (nextPoint.segmentType is None) and (previousPoint.segmentType is None):

                direction = point.direction()
                previousTurn = previousPoint.turn()
                nextTurn = nextPoint.turn()

                highlight(point)

                # if sin(5/180*pi) <= abs(sin(direction)) <= sin(85/180*pi) and (previousTurn*nextTurn > 0):
                if (previousTurn*nextTurn > 0):

                    nextNextOffcurve = points[i+2]
                    prevPrevOffcurve = points[i-2]

                    d1 = previousPoint.distance(nextPoint)
                    d2 = previousPoint.distance(point)

                    if d1 != 0:
                        t = d2/d1

                        pointsToRemove.append(point)
                        pointsToRedefine.append((nextNextOffcurve, 1-t))
                        pointsToRedefine.append((prevPrevOffcurve, t))

        for point, t in pointsToRedefine:
            if t > 0:
                self.points[point.index].lengthen(1/t)

        removedPointsCount = 0

        for point in pointsToRemove:
            if point == self.points[0]:
                for i in range(-1, 1):
                    self.points.pop(i)
                self.points.pop(0)
                removedPointsCount += 2
            else:
                index = point.index - 1 - removedPointsCount
                for i in range(3):
                    self.points.pop(index)
                    removedPointsCount += 1

        self.updateIndices()
    '''

    '''
    Get rid of retracted offcurves (overlapping with their anchors),
    or redefine cubic curve with two proper offcurves if either one of them is retracted.
    '''

    def cleanCurveSegment(self, segment):
        a1, h1, h2, a2 = segment
        redefineT = .4
        if a1.overlap(h1) and a2.overlap(h2):
            a2.segmentType = 'line'
            return (a1, a2), (h1, h2)
        elif (a1.overlap(h1) and not a2.overlap(h2)):
            h1.x, h1.y = h2.interpolate(a1, redefineT)
            h2.x, h2.y = h2.interpolate(a2, redefineT)
        elif not a1.overlap(h1) and a2.overlap(h2):
            h2.x, h2.y = h1.interpolate(a2, redefineT)
            h1.x, h1.y = h1.interpolate(a1, redefineT)
        h1.round()
        h2.round()
        return a1, h1, h2, a2

    '''
    Definition of offcurve position based on anchor position and velocity values.
    Based on a formula found in a book by D. Knuth about Metafont. Forgot which one exactly.
    '''

    def defineOffcurvesByVelocity(self, pt1, angle1, velocity1, pt2, angle2, velocity2, constrain=False):

        x1, y1 = pt1.x, pt1.y
        x2, y2 = pt2.x, pt2.y
        dist = pt1.distance(pt2)

        hx1 = round(x1 + ((1/3 * (velocity1 * cos(angle1))) * dist))
        hy1 = round(y1 + ((1/3 * (velocity1 * sin(angle1))) * dist))
        hx2 = round(x2 - ((1/3 * (velocity2 * cos(angle2))) * dist))
        hy2 = round(y2 - ((1/3 * (velocity2 * sin(angle2))) * dist))

        if constrain:
            return self.constrainSegmentOffcurves((x1,y1), (hx1, hy1), (hx2, hy2), (x2,y2))
        elif not constrain:
            return (hx1, hy1), (hx2, hy2)

    '''
    Build an acute corner from a round or flat one.
    Needs either 2 or 4 points (line or curve segment).
    The method doesn’t guess much about context,
    so if you feed a bunch of line segments,
    the result might not be what you want.
    I should try to find a sorting algorithm
    to work a series of connected segments in such a way
    that the form of the outline isn’t blown to pieces.
    Works well for most normal cases (on segment selected),
    or several of them not sitting next to each other.
    '''

    def buildCorner(self, points, minPoints=2, maxPoints=4):
        if minPoints <= len(points) <= maxPoints:
            PointClass = self._pointClass
            closed = self.isClosed()
            pointsToRemove = points[1:-1]
            firstPoint, lastPoint = points[0], points[-1]
            beforeFirst, afterLast = self.getPrevious(firstPoint), self.getNext(lastPoint)
            distance = firstPoint.distance(lastPoint)
            length = self.orderDelta(firstPoint, lastPoint)
            if (closed or ((not closed) and (not firstPoint.isFirst()) and (not lastPoint.isLast()))) and \
               (firstPoint.segmentType is not None) and (lastPoint.segmentType is not None):
                startIndex = firstPoint.index
                endIndex = lastPoint.index
                cornerPoint = PointClass((0, 0))
                ix, iy = self.intersectLineLine(beforeFirst, firstPoint, lastPoint, afterLast)
                if (ix, iy) != (None, None):
                    cornerPoint.x, cornerPoint.y = ix, iy
                    cornerPoint.round()
                    cornerDistance = (firstPoint.distance(cornerPoint) + lastPoint.distance(cornerPoint))/2
                    if (beforeFirst.segmentType is not None) or (beforeFirst.segmentType is None and firstPoint.distance(cornerPoint) < 10):
                        pointsToRemove.insert(0, firstPoint)
                    if (afterLast.segmentType is not None) or (afterLast.segmentType is None and lastPoint.distance(cornerPoint) < 10):
                        pointsToRemove.append(lastPoint)
                    if (beforeFirst.segmentType is None) and (firstPoint in pointsToRemove):
                        cornerPoint.segmentType = 'curve'
                    elif (beforeFirst.segmentType is not None) or ((beforeFirst.segmentType is None) and (firstPoint not in pointsToRemove)):
                        cornerPoint.segmentType = 'line'
                    if lastPoint not in pointsToRemove:
                        lastPoint.segmentType = 'line'
                    self.insert(startIndex+1, cornerPoint)
                    for point in pointsToRemove:
                        if point in self.points:
                            self.points.remove(point)
                    self.updateIndices()

    '''
    The other corner method, one that breaks an acute corner into a round or flat one (and more).
    Just needs a point from this contour and does the rest (even inserting the newly formed segment).
    You can define velocity for offcurve points, or let the method guess velocity values (good results).
    If you give a 0 velocity, you get a flat corner. The _insideOut_ variable allows you to ‘add overlap’ to the corner.
    You might get a better idea of this by looking at the breakCornersByLabels() method, below.
    '''

    def breakCorner(self, point, radius, velocity=1.25, guess=False, insideOut=False):
        turn = point.turn()
        if (point.segmentType is not None) and (abs(turn) >= (20/180)*pi) and \
        (self.isClosed() or (not self.isClosed() and (not point.isFirst()) and (not point.isLast()))):
            startIndex = point.index
            PointClass = self._pointClass
            if not insideOut:
                radius = -radius
            angle1 = point.direction()
            angle2 = point.incomingDirection()
            a1, a2 = point.split(radius, angle1, angle2)
            if self.getPrevious(point).segmentType is None:
                a1.segmentType = 'line'
            if abs(turn) > pi/2 and guess:
                velocity += 1.5 * ((abs(turn)-(pi/2))/(pi/2))
            h1, h2 = self.defineOffcurvesByVelocity(a1, angle1, -velocity, a2, angle2, -velocity)
            h1 = PointClass(h1)
            h2 = PointClass(h2)
            if h1 != a1 and h2 != a2:
                cornerSegment = [a1, h1, h2, a2]
            elif velocity == 0:
                cornerSegment = [a1, a2]
            self.points.pop(startIndex)
            for newPoint in cornerSegment:
                newPoint.round()
                self.insert(startIndex, newPoint)
            # self.cleanCurves()
            self.removeOverlappingPoints()

    def pitCorner(self, cornerPoint, depth=40, breadth=40, bottom=5, velocity=1.25):

        previousPoint = cornerPoint.previous()
        nextPoint = cornerPoint.next()
        turn = cornerPoint.turn()

        if (cornerPoint.segmentType is not None) and (previousPoint is not None) and (nextPoint is not None) and (abs(turn) > pi/8):

            pitAngle = cornerPoint.pivotAngle()
            if not self.clockwise:
                pitAngle = pi+pitAngle
            elif self.clockwise:
                pitAngle = pitAngle-pi

            incomingSegment = []
            outGoingSegment = []
            PointClass = self._pointClass

            deepCornerPoint = cornerPoint.derive(pitAngle, -depth)
            b1, b2 = deepCornerPoint.split(bottom/2, pitAngle+(pi/2), pitAngle+(pi/2))

            if previousPoint.segmentType is not None:
                angle1 = cornerPoint.incomingDirection()
                a1 = cornerPoint.derive(angle1, -breadth)

                if depth >= 0: h1, h2 = self.defineOffcurvesByVelocity(a1, angle1, velocity, b1, pitAngle, -velocity)
                elif depth < 0: h1, h2 = self.defineOffcurvesByVelocity(a1, angle1, velocity, b1, pi+pitAngle, -velocity)
                h1, h2 = self.constrainSegmentOffcurves(a1, h1, h2, b1)
                h1, h2 = PointClass(h1), PointClass(h2)
                h1.setParentContour(self)
                h2.setParentContour(self)
                b1.segmentType = 'curve'
                incomingSegment += [h2, h1, a1]

            elif previousPoint.segmentType is None:
                angle1 = b1.angle(previousPoint)
                d1 = previousPoint.distance(b1)
                previousPoint.x, previousPoint.y = b1.polarCoord(pitAngle+self.midAngle(pitAngle, angle1), d1)

            if nextPoint.segmentType is not None:
                angle2 = cornerPoint.direction()
                a2 = cornerPoint.derive(angle2, breadth)

                if depth >= 0: h3, h4 = self.defineOffcurvesByVelocity(b2, pitAngle, velocity, a2, angle2, velocity)
                elif depth < 0: h3, h4 = self.defineOffcurvesByVelocity(b2, pi+pitAngle, velocity, a2, angle2, velocity)
                h3, h4 = self.constrainSegmentOffcurves(b2, h3, h4, a2)
                h3, h4 = PointClass(h3), PointClass(h4)
                h3.setParentContour(self)
                h4.setParentContour(self)
                a2.segmentType = 'curve'
                outGoingSegment += [a2, h4, h3, b2, b1]

            elif nextPoint.segmentType is None:
                angle2 = b2.angle(nextPoint)
                d2 = nextPoint.distance(b2)
                nextPoint.x, nextPoint.y = b2.polarCoord(pitAngle+self.midAngle(pitAngle, angle2), d2)
                outGoingSegment += [b2, b1]

            for point in outGoingSegment:
                point.round()
                self.points.insert(cornerPoint.index+1, point)

            for point in incomingSegment:
                point.round()
                self.points.insert(cornerPoint.index, point)

            self.points.remove(cornerPoint)

            self.checkSanity()

    # def pitCorner(self, cornerPoint, depth=40, breadth=40, bottom=5, velocity=1.25):
    #     if cornerPoint.segmentType is not None:
    #         angle1 = cornerPoint.incomingDirection()
    #         angle2 = cornerPoint.direction()
    #         a1, a2 = cornerPoint.split(breadth, angle1, angle2)
    #         pitAngle = cornerPoint.pivotAngle()
    #         turn = cornerPoint.turn()
    #         if not self.clockwise:
    #             pitAngle = pi+pitAngle
    #         elif self.clockwise:
    #             pitAngle = pitAngle-pi
    #         cornerPoint.x, cornerPoint.y = cornerPoint.polarCoord(pitAngle, -depth)
    #         b1, b2 = cornerPoint.split(bottom/2, pitAngle+(pi/2), pitAngle+(pi/2))
    #         if depth >= 0: h1, h2 = self.defineOffcurvesByVelocity(a1, angle1, velocity, b1, pitAngle, -velocity)
    #         elif depth < 0: h1, h2 = self.defineOffcurvesByVelocity(a1, angle1, velocity, b1, pi+pitAngle, -velocity)
    #         h1, h2 = self.constrainSegmentOffcurves(a1, h1, h2, b1)
    #         if depth >= 0: h3, h4 = self.defineOffcurvesByVelocity(b2, pitAngle, velocity, a2, angle2, velocity)
    #         elif depth < 0: h3, h4 = self.defineOffcurvesByVelocity(b2, pi+pitAngle, velocity, a2, angle2, velocity)
    #         h3, h4 = self.constrainSegmentOffcurves(b2, h3, h4, a2)
    #         offcurves = [h1, h2, h3, h4]
    #         for i, offcurve in enumerate(offcurves):
    #             offcurve = IntelPoint(offcurve)
    #             offcurve.setParentContour(self)
    #             offcurves[i] = offcurve
    #         a2.segmentType = b1.segmentType = 'curve'
    #         a1.round()
    #         a2.round()
    #         b1.round()
    #         b2.round()
    #         for point in [a2, offcurves[3], offcurves[2], b2, b1]:
    #             self.points.insert(cornerPoint.index+1, point)
    #         for point in [offcurves[1], offcurves[0], a1]:
    #             self.points.insert(cornerPoint.index, point)
    #         self.points.remove(cornerPoint)
    #         self.checkSanity()

    '''
    General method that goes over all points and makes corners based on point label values.
    '''

    def drawCornersByLabels(self):
        for point in self.points:
            if point.labels['cornerRadius']:
                if not point.labels['cut'] and not point.labels['overlap']:
                    self.breakCorner(point, point.labels['cornerRadius'], guess=True)
                elif point.labels['cut']:
                    self.breakCorner(point, point.labels['cornerRadius'], velocity=0)
                elif point.labels['overlap']:
                    self.breakCorner(point, point.labels['cornerRadius'], velocity=0, insideOut=True)
        self.correctSmoothness()

    def drawPoints(self, pointPen):

        points = self.points

        pointPen.beginPath()
        for point in points:
            pointPen.addPoint((point[0], point[1]), point.segmentType, point.smooth, point.name)
        pointPen.endPath()

    def draw(self, pen):
        from robofab.pens.adapterPens import PointToSegmentPen
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def digest(self):
        digest = []
        points = self.points
        for point in points:
            pointView = '%s  %s  %s' % (point.x, point.y, point.segmentType)
            digest.append(pointView)
        print len(digest)
        print '\n'.join(digest)
        print '-'
        print '\n'

'''
Pen that makes conversion to IntelContours a bit faster that the basic IntelGlyph method.
Isn’t much use if one needs to keep point selection info though.
'''

class IntelOutlinePen(AbstractPointPen):

    def __init__(self, contourClass, pointClass):
        self.contourClass = contourClass
        self.pointClass = pointClass
        self.contours = []
        self.contourCount = 0

    def beginPath(self):
        self.currentContour = self.contourClass(index=self.contourCount)
        self.pointCount = 0

    def addPoint(self, pt, segmentType, smooth, name, *args, **kwargs):
        anchors = []
        if (self.pointCount == 0) and (name is not None):
            pointLabels = name.split(',')
            anchors = list(set(pointLabels) & set(['top', 'bottom', 'right', 'mid', 'left', 'circum']))
        if not len(anchors):
            point = self.pointClass(pt, segmentType, smooth, name, index=self.pointCount)
            self.currentContour.append(point)
            self.pointCount += 1

    def endPath(self):
        self.currentContour.clockwise = self.currentContour.isClockwise()
        self.contours.append(self.currentContour)
        self.contourCount += 1
        self.currentContour = []
        self.pointCount = 0

    def get(self):
        return self.contours

'''
Convenience glyph object simply there to group IntelContours
and ease operations on a bunch of them.
'''

class IntelGlyph(object):

    _contourClass = IntelContour

    def __init__(self, glyph=None):
        self._sourceGlyph = glyph
        if glyph is not None:
            if not len(glyph.selection):
                '''
                If there’s no points selection to get
                go through the IntelOutlinePen (faster)
                '''
                pen = IntelOutlinePen(self._contourClass, self._contourClass._pointClass)
                glyph.drawPoints(pen)
                self.contours = pen.get()
                for contour in self.contours:
                    contour.cleanCurves()
            elif len(glyph.selection):
                '''
                If there are selected points
                go through appendContour to gather selection info
                '''
                self.contours = []
                for c in glyph.contours:
                    self.appendContour(c)
            self.name = glyph.name
        elif glyph is None:
            self.contours = []
            self.name = None

    def __iter__(self):
        for value in self.contours:
            yield value

    def __getitem__(self, index):
        if index < len(self.contours):
            return self.contours[index]
        raise IndexError

    def move(self, (mx, my)):
        for contour in self.contours:
            contour.move((mx, my))

    def rotate(self, angle, origin=(0, 0)):
        for contour in self.contours:
            contour.rotate(angle, origin)

    def appendContour(self, c):
        if not isinstance(c, self._contourClass):
            contour = self._contourClass(c, index=len(self.contours))
        elif isinstance(c, self._contourClass):
            contour = c
            contour.index = len(self.contours)
            contour.cleanCurves()
        self.contours.append(contour)

    def getSelection(self, withSegments=False):
        selectedSegments = []
        if not withSegments:
            for contour in self.contours:
                selection = contour.getSelection()
                selectedSegments += selection
        elif withSegments:
            for contour in self.contours:
                selection = contour.collectSegments()
                selectedSegments += selection['selection']
        return selectedSegments

    def round(self):
        for contour in self.contours:
            contour.round()

    def drawCornersByLabels(self):
        for contour in self.contours:
            contour.drawCornersByLabels()

    def extractGlyph(self, glyph, replace=True):
        if glyph is not None:
            glyph.prepareUndo('extractIntelGlyph')
            pen = glyph.getPointPen()
            if replace:
                glyph.clearContours()
            self.drawPoints(pen)
            glyph.performUndo()
            return glyph

    def drawPoints(self, pointPen):
        if pointPen is not None:
            for contour in self.contours:
                contour.drawPoints(pointPen)

    def draw(self, pen):
        if pen is not None:
            for contour in self.contours:
                contour.draw(pen)

    '''
    The drawPreview() method draws a glyph rendering
    with a CocoaPen (ideally used in link with a draw Observer)

    it draws a preview glyph consisting of a half-transparent fill color
    as well as the a stroked outline and points.

    If the plain boolean is set to True,
    the rendered outline is simply a plain black glyph

    Note: I should try to work something out with representation factories, ’d be better I guess.
    '''

    def drawPreview(self,
        scale=None,
        plain=False,
        styleFill=True,
        styleStroke=True,
        showNodes=True,
        fillColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.3, .6, .2, .2),
        strokeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.3, .6, .2, .5),
        strokeWidth = 1):
        if scale is None:
            scale = 1
        previewPen = CocoaGlyphPen(4*scale, 3*scale)
        self.draw(previewPen)

        # glyph contour
        if not plain:
            # fillColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.3, .6, .2, .2)
            # strokeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.3, .6, .2, .5)
            fillColor.set()
            strokeColor.setStroke()
            previewPen.glyphPath.setLineWidth_(scale*strokeWidth)
            if styleStroke:
                previewPen.glyphPath.stroke()
            if styleFill:
                previewPen.glyphPath.fill()

        elif plain:
            save()
            fill(1)
            rect(-5000, -5000, 10000, 10000)
            fillColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
            fillColor.set()
            previewPen.glyphPath.fill()
            restore()

        if not plain and showNodes:
            # handleLine
            handleLineColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.2, .6, .1, .5)
            previewPen.handleLines.setLineWidth_(scale)
            handleLineColor.setStroke()
            previewPen.handleLines.stroke()

            # offCurve
            offCurveColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.2, .6, .1, 1)
            white = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 1)
            previewPen.offCurvePoints.setLineWidth_(scale)
            white.set()
            offCurveColor.setStroke()
            previewPen.offCurvePoints.fill()
            previewPen.offCurvePoints.stroke()

            # onCurve
            onCurveColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.2, .6, .1, 1)
            previewPen.onCurvePoints.setLineWidth_(scale)
            onCurveColor.set()
            previewPen.onCurvePoints.fill()

    def digest(self):
        allContours = []
        for i, contour in enumerate(self.contours):
            thisContour = []
            for point in contour:
                pointView = '%s  %s  %s' % (point.x, point.y, point.segmentType)
                thisContour.append(pointView)
            thisContour.insert(0, u'#%s(%s) Points: %s\n—'%(i,contour.index,len(thisContour)))
            thisContour.append(u'—\n')
            allContours.append('\n'.join(thisContour))
        return '\n'.join(allContours)


# Used mostly for testing purposes
from mojo.events import addObserver, removeObserver

class BaseIntelGlyphPreview:

    def __init__(self, intelGlyph=None):
        addObserver(self, 'drawPreviewGlyph', 'draw')
        addObserver(self, 'drawPreviewGlyph', 'drawInactive')
        self.glyph = intelGlyph

    def setGlyph(self, glyph):
        self.glyph = glyph

    def drawPreviewGlyph(self, notification):
        if self.glyph is not None:
            sc = notification['scale']
            glyph = self.glyph
            glyph.drawPreview(sc)
        removeObserver(self, 'draw')
        removeObserver(self, 'drawInactive')
