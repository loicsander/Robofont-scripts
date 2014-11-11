#coding=utf-8

from glyphObjects import IntelGlyph

from mojo.events import BaseEventTool, EditingTool, installTool
from mojo.drawingTools import *
from AppKit import NSColor, NSBezierPath, NSImage
from robofab.misc.arrayTools import pointInRect
from math import hypot, pi

import os
dirname = os.path.dirname(__file__)
toolbarIcon = NSImage.alloc().initWithContentsOfFile_(os.path.join(dirname, "RoundingToolIcon.pdf"))

class RoundingTool(BaseEventTool):

    def becomeActive(self):
        self.init()

    # def becomeInactive(self):
        # pass

    def init(self):
        self._sourceGlyph = None
        self._workingGlyph = None
        self._roundedGlyph = None
        self.roundablePoints = []
        self.snatchedPoint = None
        self.preview = False
        self.updateRoundablePoints()
        self.draggedRectangle = {'rect':[], 'bounds':[]}
        self.mouseDownPoint = None
        self.pointSelection = []

    def mouseDown(self, mousePoint, clickCount):
        self.mouseDownPoint = mousePoint
        self.pointSelection = []
        if clickCount == 2:
            if self.commandDown and self._sourceGlyph is not None:
                for point in self.roundablePoints:
                    point.labels['cornerRadius'] = 0
                    point.labels['cut'] = False
                    self.writePointLabels(self._sourceGlyph, point)
            elif not self.commandDown:
                self.makeRoundedGlyph()
        elif clickCount == 1:
            controlZoneRadius = 8
            roundablePoints = self.roundablePoints
            for point in roundablePoints:
                controlPoint, r = self.getControlPoint(point)
                if abs(controlPoint[0]-mousePoint[0]) <= controlZoneRadius and abs(controlPoint[1]-mousePoint[1]) <= controlZoneRadius:
                    self.snatchedPoint = point
                    break

    def mouseDragged(self, mousePoint, delta):
        if self.snatchedPoint is not None:
            snatchedPoint = self.snatchedPoint
            cut = False
            self._roundedGlyph = IntelGlyph(self._sourceGlyph)
            i1, i2 = self.getRoundedPointIndices(snatchedPoint)
            dx = snatchedPoint[0]-mousePoint[0]
            dy = snatchedPoint[1]-mousePoint[1]
            d = hypot(dx, dy)
            if self.shiftDown:
                d = round(d/5)*5
            d = int(d)
            limit = self.getLimit(snatchedPoint)
            if d > limit:
                d = limit
            if self.shiftDown and self.commandDown:
                d = 0
            if self.optionDown:
                cut = True
            self._roundedGlyph[i1][i2].labels['cornerRadius'] = d
            self._roundedGlyph[i1][i2].labels['cut'] = cut
            self._roundedGlyph.drawCornersByLabels()
            snatchedPoint.labels['cornerRadius'] = d
            snatchedPoint.labels['cut'] = cut
            self.snatchedPoint = snatchedPoint

    # def rightMouseDown(self, point, event):
    #     print "rightMouseDown"

    # def rightMouseDragged(self, point, delta):
    #     print "rightMouseDragged"

    def mouseUp(self, point):
        # if self.snatchedPoint is None:
        #     mouseDownPoint = self.mouseDownPoint
        #     if (self._sourceGlyph is not None) and (mouseDownPoint is not None):
        #         currentGlyph = self._sourceGlyph
        #         xMin = min(mouseDownPoint[0], point[0])
        #         xMax = max(mouseDownPoint[0], point[0])
        #         yMin = min(mouseDownPoint[1], point[1])
        #         yMax = max(mouseDownPoint[1], point[1])
        #         for contour in currentGlyph.contours:
        #             for point in contour.points:
        #                 if pointInRect((point.x, point.y), [xMin, yMin, xMax, yMax]):
        #                     point.selected = True
        #                     self.pointSelection.append(point)
        #         currentGlyph.update()
        #         self.updateRoundablePoints()
        if (self._roundedGlyph is not None) and (self.snatchedPoint is not None):
            snatchedPoint = self.snatchedPoint
            self._roundedGlyph.drawCornersByLabels()
            self.writePointLabels(self._sourceGlyph, snatchedPoint)
            self.snatchedPoint = None
        self.mouseDownPoint = None

    def updateRoundablePoints(self):
        glyph = self._sourceGlyph = self.getGlyph()
        if glyph is not None:
            workingGlyph = IntelGlyph(glyph)
            self._roundedGlyph = IntelGlyph(glyph)
            self._roundedGlyph.drawCornersByLabels()
            roundablePoints = []
            for contour in workingGlyph:
                closed = contour.isClosed()
                for point in contour:
                    nextPoint = point.next()
                    previousPoint = point.previous()
                    turnLimit = abs(point.turn()) < (10/180)*pi
                    if (point.segmentType is not None) and \
                        (self.getLimit(point) > 0) and \
                       (closed or (not closed and (not point.isFirst()) and (not point.isLast()))) and \
                       (((previousPoint.segmentType is not None) and (nextPoint.segmentType is not None)) or \
                        ((previousPoint.segmentType is None) and (nextPoint.segmentType is not None) and not turnLimit and not point.smooth) or \
                        ((previousPoint.segmentType is not None) and (nextPoint.segmentType is None) and not turnLimit and not point.smooth)):
                        roundablePoints.append(point)
            self.roundablePoints = roundablePoints
            self._workingGlyph = workingGlyph

    def getControlPoint(self, point):
        direction = point.direction()
        radius = self.getRadius(point)
        return point.polarCoord(direction, radius), radius

    def getRoundedPointIndices(self, point):
        pointIndex = point.index
        contourIndex = point.getParentContour().index
        return contourIndex, pointIndex

    def getRadius(self, point):
        radius = 0
        if point.labels['cornerRadius']:
            radius = int(point.labels['cornerRadius'])
        return radius

    def getLimit(self, point):
        previousPoint = point.previous()
        nextPoint = point.next()
        d = -1
        if previousPoint is not None and nextPoint is not None:
            d1 = point.distance(previousPoint)-float(self.getRadius(previousPoint))
            d2 = point.distance(nextPoint)-float(self.getRadius(nextPoint))
            d = int(min(d1, d2))
        if d < 0: d = 0
        return d

    def writePointLabels(self, glyph, iPoint):
        i1, i2 = self.getRoundedPointIndices(iPoint)
        RPoint = glyph.contours[i1].points[i2]
        RPoint.name = iPoint.labels.write(RPoint.name)

    controlSoftColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.8, .6, 0, .25)
    controlStrongColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.8, .6, 0, 0.85)

    def draw(self, scale):
        controlSoftColor = self.controlSoftColor
        controlStrongColor = self.controlStrongColor
        if self._roundedGlyph is not None:
            self._roundedGlyph.drawPreview(scale, styleFill=False, showNodes=False, strokeWidth=2, strokeColor=controlStrongColor)
        for point in self.roundablePoints:
            x, y = point.x, point.y
            (cx, cy), r = self.getControlPoint(point)
            controlSoftColor.set()
            controlStrongColor.setStroke()
            radiusCircle = NSBezierPath.bezierPathWithOvalInRect_(((x-r, y-r), (r*2, r*2)))
            radiusCircle.fill()
            radiusCircle.setLineWidth_(scale)
            radiusCircle.stroke()
            controlStrongColor.set()
            cor = 12*scale
            controlDot = NSBezierPath.bezierPathWithOvalInRect_(((cx-cor, cy-cor), (cor*2, cor*2)))
            controlDot.fill()
            if point.labels['cornerRadius']:
                fill(1)
                fontSize(9*scale)
                _r = str(r)
                textBox(_r, (cx-cor, cy-(cor*1.5), cor*2, cor*2), align='center')
        # if self.isDragging and (self.currentPoint is not None) and (self.mouseDownPoint is not None) and (self.snatchedPoint is None):
        #     fill(.25, .25, .25, .25)
        #     mouseDownPoint = self.mouseDownPoint
        #     currentPoint = self.currentPoint
        #     rect(mouseDownPoint[0], mouseDownPoint[1], currentPoint[0]-mouseDownPoint[0], currentPoint[1]-mouseDownPoint[1])


    def makeRoundedGlyph(self):
        if self._roundedGlyph is not None:
            self._sourceGlyph.prepareUndo('round')
            self._sourceGlyph = self.stripContours(self._sourceGlyph)
            pen = self._sourceGlyph.getPointPen()
            self._roundedGlyph.drawPoints(pen)
            self._sourceGlyph.performUndo()
            self._sourceGlyph.update()
            self.updateRoundablePoints()

    def stripContours(self, glyph):
        for contour in glyph.contours:
            glyph.removeContour(contour)
        return glyph

    def didUndo(self, notification):
        self.updateRoundablePoints()

    # def keyUp(self, event):
    #     print "keyUp"

    # def modifiersChanged(self):
    #     pass

    # def drawBackground(self, scale):
    #     print "drawBackground here"

    #def getDefaultCursor(self):
    #   this will be the cursor default is an arrow
    #   return aNSCursor

    def getToolbarIcon(self):
        return toolbarIcon

    def getToolbarTip(self):
        return "Rounding Tool"

    #notifications

    def viewDidChangeGlyph(self):
        self.init()

    # def preferencesChanged(self):
    #     print "prefs changed"

installTool(RoundingTool())