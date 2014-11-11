from glyphObjects import IntelGlyph
from vanillaParameterObjects import VanillaSingleValueParameter, ParameterSliderTextInput
from vanilla import FloatingWindow, GradientButton, EditText, TextBox, RadioGroup, Group, Box
from mojo.events import addObserver, removeObserver
from mojo.UI import UpdateCurrentGlyphView
from math import pi
from AppKit import NSColor

cornerOutlineSoftColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.8, .6, 0, .2)
cornerOutlineStrongColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.8, .6, 0, 0.85)

class CornerController:

    def __init__(self):
        self.modifiedGlyph = None
        self.w = FloatingWindow((400, 170), 'Corner Tool')
        self.w.getNSWindow().setBackgroundColor_(NSColor.whiteColor())
        self.modes = ['Build', 'Break','Pit']
        self.objectTypes = {'Build':'Segment', 'Break':'Corner point', 'Pit':'Corner point'}
        self.parameters = {
            'radius': VanillaSingleValueParameter('radius', 20, (-200, 200), numType='int'),
            'roundness': VanillaSingleValueParameter('roundness', 1.25, (0, 4), numType='float'),
            'depth': VanillaSingleValueParameter('depth', 30, (-100, 100), numType='int'),
            'breadth': VanillaSingleValueParameter('breadth', 30, (0, 150), numType='int'),
            'bottom': VanillaSingleValueParameter('bottom', 5, (0, 40), numType='int')
        }
        self.currentMode = 'Build'
        self.previewGlyph = None

        self.w.modes = RadioGroup((15, 15, 70, -15), self.modes, callback=self.changeMode)
        for i, mode in enumerate(self.modes):
            setattr(self.w, mode, Group((120, 15, -15, -15)))
            modeGroup = getattr(self.w, mode)
            modeGroup.apply = GradientButton((-35, 0, -0, -0), title=u'>', callback=self.apply)
            modeGroup.infoBox = Box((0, 0, -50, 35))
            modeGroup.info = TextBox((10, 8, -50, 20), 'No selection')
            if i > 0: modeGroup.show(False)

        self.w.Break.radius = ParameterSliderTextInput(self.parameters['radius'], (0, 60, -25, 25), title='Radius', callback=self.makePreviewGlyph)
        self.w.Break.roundness = ParameterSliderTextInput(self.parameters['roundness'], (0, 95, -25, 25), title='Roundness', callback=self.makePreviewGlyph)

        self.w.Pit.depth = ParameterSliderTextInput(self.parameters['depth'], (0, 50, -25, 25), title='Depth', callback=self.makePreviewGlyph)
        self.w.Pit.breadth = ParameterSliderTextInput(self.parameters['breadth'], (0, 80, -25, 25), title='Breadth', callback=self.makePreviewGlyph)
        self.w.Pit.bottom = ParameterSliderTextInput(self.parameters['bottom'], (0, 110, -25, 25), title='bottom', callback=self.makePreviewGlyph)

        addObserver(self, 'preview', 'draw')
        addObserver(self, 'preview', 'drawInactive')
        addObserver(self, 'setControls', 'mouseUp')
        addObserver(self, 'setControls', 'selectAll')
        addObserver(self, 'setControls', 'deselectAll')
        addObserver(self, 'setControls', 'currentGlyphChanged')
        self.w.bind('close', self.windowClose)
        self.setControls()
        self.w.open()

    def changeMode(self, sender):
        index = sender.get()
        previousModeGroup = getattr(self.w, self.currentMode)
        previousModeGroup.show(False)
        self.currentMode = self.modes[index]
        modeGroup = getattr(self.w, self.currentMode)
        modeGroup.show(True)
        self.setControls()

    def setControls(self, notification=None):
        mode = self.currentMode
        selection = self.getSelection()
        modeGroup = getattr(self.w, mode)
        if not len(selection):
            modeGroup.apply.enable(False)
            modeGroup.info.set('No selection (%ss)'%(self.objectTypes[mode].lower()))
        elif len(selection):
            modeGroup.apply.enable(True)
            info = '%s valid %s'%(len(selection), self.objectTypes[mode].lower())
            if len(selection) > 1: info += 's'
            modeGroup.info.set(info)
        self.makePreviewGlyph()

    def getSelection(self, notification=None):
        glyph = CurrentGlyph()
        if len(glyph.selection) == 0:
            return []
        elif len(glyph.selection) > 0:
            iG = IntelGlyph(glyph)
            if self.currentMode == 'Build':
                selection = iG.getSelection(True)
            elif self.currentMode in ['Break', 'Pit']:
                selection = [point for point in iG.getSelection() if (point.segmentType is not None) and (abs(point.turn()) > pi/18)]
            return selection

    def preview(self, notification):
        sc = notification['scale']
        if self.previewGlyph is not None:
            self.previewGlyph.drawPreview(sc, styleFill=True, showNodes=False, strokeWidth=2, fillColor=cornerOutlineSoftColor, strokeColor=cornerOutlineStrongColor)

    def makePreviewGlyph(self, sender=None):
        self.previewGlyph = self.makeCornerGlyph()
        UpdateCurrentGlyphView()

    def makeCornerGlyph(self, sender=None):
        mode = self.currentMode
        if mode == 'Build':
            cornerGlyph = self.buildCorners()
        elif mode == 'Break':
            cornerGlyph = self.breakCorners()
        elif mode == 'Pit':
            cornerGlyph = self.pitCorners()
        return cornerGlyph

    def buildCorners(self):
        g = CurrentGlyph()
        iG = IntelGlyph(g)
        for contour in iG:
            segments = contour.collectSegments()['selection']
            l = len(segments)
            lines, curves = self.checkComposition(segments)
            if l > 1 and lines and curves:
                segments = [segment for segment in segments if len(segment) == 4]
            elif l > 1 and lines and not curves:
                segments = segments[:1] + segments[-1:]
            for segment in reversed(segments):
                contour.buildCorner(segment)
        return iG

    def breakCorners(self):
        g = CurrentGlyph()
        iG = IntelGlyph(g)
        radius = self.parameters['radius'].get()
        roundness = self.parameters['roundness'].get()
        for contour in iG:
            selection = contour.getSelection()
            for point in selection:
                contour.breakCorner(point, radius, velocity=roundness)
            contour.correctSmoothness()
        return iG

    def pitCorners(self):
        g = CurrentGlyph()
        iG = IntelGlyph(g)
        depth = self.parameters['depth'].get()
        breadth = self.parameters['breadth'].get()
        bottom = self.parameters['bottom'].get()
        for contour in iG:
            selection = contour.getSelection()
            for point in selection:
                contour.pitCorner(point, depth, breadth, bottom)
            contour.removeOverlappingPoints()
            contour.correctSmoothness()
        return iG

    def apply(self, sender):
        targetGlyph = CurrentGlyph()
        modifiedGlyph = self.makeCornerGlyph()
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

    def windowClose(self, notification):
        removeObserver(self, 'draw')
        removeObserver(self, 'drawInactive')
        removeObserver(self, 'mouseUp')
        removeObserver(self, 'selectAll')
        removeObserver(self, 'deselectAll')
        removeObserver(self, 'currentGlyphChanged')

CornerController()