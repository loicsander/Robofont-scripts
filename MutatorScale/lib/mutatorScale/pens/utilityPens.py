#coding=utf-8
from fontTools.pens.basePen import BasePen
from robofab.pens.pointPen import AbstractPointPen

class ClockwiseTestPointPen(AbstractPointPen):

    def __init__(self):
        self._points = []

    def beginPath(self):
        pass

    def endPath(self):
        pass

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        if segmentType:
            # overlapping points can give false results, so filter them out
            if self._points and self._points[-1] == pt:
                return
            self._points.append(pt)

    def getIsClockwise(self):
        points = self._points
        pointCount = len(points)
        # overlapping moves can give false results, so filter them out
        if points[0] == points[-1]:
            del points[-1]
        total = 0

        for index1 in xrange(pointCount):
            index2 = (index1 + 1) % pointCount
            x1, y1 = points[index1]
            x2, y2 = points[index2]
            total += (x1*y2)-(x2*y1)

        return total < 0

class CollectSegmentsPen(BasePen):

    def __init__(self):
        self.contours = []

    def _moveTo(self, pt):
        self.segments = []
        self.previousPoint = pt

    def _lineTo(self, pt):
        self.segments.append((self.previousPoint, pt))
        self.previousPoint = pt

    def _curveToOne(self, pt1, pt2, pt3):
        self.segments.append((self.previousPoint, pt1, pt2, pt3))
        self.previousPoint = pt3

    def endPath(self):
        self.contours.append(self.segments)

    closePath = endPath

    def getSegments(self):
        return self.contours