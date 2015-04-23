#coding=utf-8
from __future__ import division
from fontTools.pens.basePen import BasePen
import math
import random

def distance((x1, y1), (x2, y2)):
    dx = x2 - x1
    dy = y2 - y1
    return math.hypot(dy, dx)

def interpolate((x1, y1), (x2, y2), factor):
    x = x1 + ((x2 - x1) * factor)
    y = y1 + ((y2 - y1) * factor)
    return x, y

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

def curveLength(pt1, pt2, pt3, pt4, precision=20):
    flatCurvePoints = [pointOnACurve(pt1, pt2, pt3, pt4, i/precision) for i in range(precision)]
    length = 0
    for i in range(1, len(flatCurvePoints)):
        previousPoint = flatCurvePoints[i-1]
        point = flatCurvePoints[i]
        length += distance(previousPoint, point)
    return length

class JitterPen(BasePen):

    def __init__(self, pen, jitterPace=10, deviation=10):
        self.pen = pen
        self.previousPoint = None
        self.pace = jitterPace
        if self.pace < 1:
            self.pace = 1
        self.deviation = deviation
        self.started = False

    def _moveTo(self, pt):
        self.previousPoint = pt
        self.started = True

    def _lineTo(self, pt):
        pt0 = self.previousPoint
        if self.started == True:
            self.pen.moveTo(pt0)
            self.started = False
        pt1 = pt
        d = distance(pt0, pt1)
        steps = int(d/self.pace)
        deviation = self.deviation
        for i in range(steps):
            x, y = interpolate(pt0, pt1, i/steps)
            nx = self.deviate(x)
            ny = self.deviate(y)
            self.pen.lineTo((nx, ny))
        self.previousPoint = pt1

    def _curveToOne(self, pt1, pt2, pt3):
        pt0 = self.previousPoint
        if self.started == True:
            self.pen.moveTo(pt0)
            self.started = False
        d = curveLength(pt0, pt1, pt2, pt3)
        steps = int(d/self.pace)
        deviation = self.deviation
        for i in range(steps):
            x, y = pointOnACurve(pt0, pt1, pt2, pt3, i/steps)
            nx = self.deviate(x)
            ny = self.deviate(y)
            self.pen.lineTo((nx, ny))
        self.previousPoint = pt3

    def endPath(self):
        if self.started == False:
            self.pen.endPath()

    def closePath(self):
        if self.started == False:
            self.pen.closePath()

    def addComponent(self, baseGlyphName, transformations):
        pass

    def deviate(self, value):
        return random.gauss(value, self.deviation)