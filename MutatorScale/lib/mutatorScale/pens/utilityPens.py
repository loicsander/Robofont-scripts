#coding=utf-8
from fontTools.pens.basePen import BasePen

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