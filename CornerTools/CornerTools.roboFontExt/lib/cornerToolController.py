from glyphObjects import IntelGlyph
from vanilla import FloatingWindow, GradientButton, EditText, TextBox
from mojo.events import addObserver, removeObserver
from mojo.UI import UpdateCurrentGlyphView
from AppKit import NSColor

class CornerController:

    def __init__(self):
        self.modifiedGlyph = None
        self.w = FloatingWindow((300, 90), 'Corner Tool')
        self.w.getNSWindow().setBackgroundColor_(NSColor.whiteColor())
        self.w.unroundButt = GradientButton((15, 15, -15, 22), title='Rebuild', callback=self.buildCorner, sizeStyle='small')
        self.w.roundButt = GradientButton((225, 50, -15, 22), title='Round', callback=self.wearCorner, sizeStyle='small')
        self.w.roundButt.name = 'round'
        self.w.cutButt = GradientButton((180, 50, 45, 22), title='Cut', callback=self.wearCorner, sizeStyle='small')
        self.w.cutButt.name = 'cut'
        self.w.overlapButt = GradientButton((110, 50, 70, 22), title='Overlap', callback=self.wearCorner, sizeStyle='small')
        self.w.overlapButt.name = 'overlap'
        self.w.roundRadiusTitle = TextBox((15, 53, 40, 20), 'Radius', sizeStyle='small')
        self.w.roundRadius = EditText((55, 50, 40, 21), '20')
        self.w.open()

    def buildCorner(self, sender):
        g = CurrentGlyph()
        iG = IntelGlyph(g)
        L = 0
        for contour in iG:
            segments = contour.collectSegments()['selection']
            l = len(segments)
            L += l
            lines, curves = self.checkComposition(segments)
            if l > 1 and lines and curves:
                segments = [segment for segment in segments if len(segment) == 4]
            elif l > 1 and lines and not curves:
                segments = segments[:1] + segments[-1:]
            for segment in reversed(segments):
                contour.buildCorner(segment)
        if L:
            self.apply(g, iG)

    def wearCorner(self, sender):
        mode = sender.name
        g = CurrentGlyph()
        try: radius = int(self.w.roundRadius.get())
        except: radius = 20
        iG = IntelGlyph(g)
        L = 0
        for contour in iG:
            selection = contour.getSelection()
            l = len(selection)
            L += l
            for point in selection:
                if mode == 'round':
                    contour.breakCorner(point, radius, guess=True)
                elif mode == 'cut':
                    contour.breakCorner(point, radius, velocity=0)
                elif mode == 'overlap':
                    contour.breakCorner(point, radius, velocity=0, insideOut=True)
            contour.correctSmoothness()
        if L:
            self.apply(g, iG)

    def apply(self, targetGlyph, modifiedGlyph):
        targetGlyph.prepareUndo('un.round')
        targetGlyph.clearContours()
        for p in targetGlyph.selection:
            p.selected = False
        pen = targetGlyph.getPointPen()
        modifiedGlyph.drawPoints(pen)
        targetGlyph.performUndo()
        targetGlyph.update()

    def checkComposition(self, segmentsList):
        lines = 0
        curves = 0
        for segment in segmentsList:
            if len(segment) == 2:
                lines += 1
            elif len(segment) == 4:
                curves += 1
        return lines, curves

CornerController()