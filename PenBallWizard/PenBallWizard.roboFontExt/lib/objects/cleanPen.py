from fontTools.pens.basePen import BasePen
from robofab.pens.pointPen import AbstractPointPen

class CleanPointPen(AbstractPointPen):

    def __init__(self):
        self.contours = []

    def beginPath(self):
        self.currentContour = []

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, *args, **kwargs):
        point = {
            'pt': pt,
            'segmentType': segmentType,
            'smooth': smooth,
            'name': name
        }
        self.currentContour.append(point)

    def endPath(self):
        onCurves = [1 for point in self.currentContour if point['segmentType'] is not None]
        if len(onCurves) >= 2:
            self.contours.append(self.currentContour)

    def extract(self, pointPen):
        for contour in self.contours:
            pointPen.beginPath()
            for point in contour:
                pointPen.addPoint(**point)
            pointPen.endPath()

class CleanPen(BasePen):

    def __init__(self, pen):
        self.pen = pen
        self.startPoint = False
        self.previousPoint = None

    def _moveTo(self, pt):
        self.startPoint = True

    def _lineTo(self, pt):

        if self.startPoint == True:
            self.pen.moveTo(self.previousPoint)
            self.startPoint = False

        if self.previousPoint is not None:
            self.pen.lineTo(pt)
            self.previousPoint = pt

    def _curveToOne(self, pt1, pt2, pt3):

        if self.startPoint == True:
            self.pen.moveTo(self.previousPoint)
            self.startPoint = False

        if self.previousPoint is not None:
            self.pen.curveTo(pt1, pt2, pt3)
            self.previousPoint = pt3

    def endPath(self):
        self.previousPoint = None
        self.pen.endPath()

    def closePath(self):
        self.previousPoint = None
        self.pen.closePath()
