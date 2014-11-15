#coding=utf-8

'''
v.0.4
ScaleFast is a script with a simple mission:
trying to maintain stem width while you transform a glyph.
To do that, the tool relies on masters (you need at least two),
analyses them and does its best to keep stems consistent
through interpolation, powered by Erik van Blokland’s MutatorMath.

Thanks to Frederik Berlaen for the inspiration (UFOStretch) & consent
'''

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator
from vanilla import *
from mojo.events import addObserver, removeObserver
from mojo.UI import MultiLineView
from mojo.tools import IntersectGlyphWithLine
from mojo.drawingTools import *
from fontMath.mathGlyph import MathGlyph
from defconAppKit.tools.textSplitter import splitText
from AppKit import NSColor, NSBoxCustom, NSDragOperationNone
from math import cos, sin, radians, pi
import re

def fontName(font):
    if isinstance(font, RFont):
        familyName = font.info.familyName
        styleName = font.info.styleName
        if familyName is None:
            familyName = font.info.familyName = 'Unnamed'
        if styleName is None:
            styleName = font.info.styleName = 'Unnamed'
        return ' > '.join([familyName, styleName])
    return ''

def errorGlyph():
    glyph = RGlyph()
    glyph.width = 330
    glyph.name = '_error_'
    pen = glyph.getPen()

    l = 50
    p = (130, 170)
    a = pi/4
    pen.moveTo(p)
    px, py = p
    for i in range(12):
        x = px+(l*cos(a))
        y = py+(l*sin(a))
        pen.lineTo((x, y))
        px = x
        py = y
        if i%3 == 0:
            a -= pi/2
        elif i%3 != 0:
            a += pi/2
    pen.closePath()
    return glyph

def decomposeGlyph(glyph, fixedWidth=False):
    if glyph is not None:
        components = glyph.components
        font = glyph.getParent()
        decomposedGlyph = RGlyph()

        if font is not None:
            for component in components:
                base = font[component.baseGlyph]
                if len(base.components) > 0:
                    base = makePreviewGlyph(base)
                decomponent = RGlyph()
                decomponent.appendGlyph(base)
                decomponent.scale((component.scale[0], component.scale[1]))
                decomponent.move((component.offset[0], component.offset[1]))
                decomposedGlyph.appendGlyph(decomponent)
            for contour in glyph.contours:
                decomposedGlyph.appendContour(contour)

            if fixedWidth:
                decomposedGlyph.width = 1000
                decomposedGlyph.leftMargin = decomposedGlyph.rightMargin = (decomposedGlyph.leftMargin + decomposedGlyph.rightMargin)/2
                decomposedGlyph.scale((.75, .75), (decomposedGlyph.width/2, 0))
                decomposedGlyph.move((0, -50))

            decomposedGlyph.name = glyph.name

        return decomposedGlyph
    return

def mapValue(value, (minValue1, maxValue1), (minValue2, maxValue2)):
    d1 = maxValue1 - minValue1
    d2 = maxValue2 - minValue2
    if d1:
        factor = (value-minValue1) / d1
        value = minValue2 + (d2 * factor)
    return value

class ScaleController:

    controllerDisplaySettings = {
        'showVerticalGuides': False,
        'showMetrics': False
    }

    def __init__(self):
        self.w = Window((900, 550), 'ScaleFast', minSize=(800, 550))
        self.w.controls = Group((15, 15, 250, -15))
        controls = self.w.controls
        allFontsNames = [fontName(font) for font in AllFonts()]
        controls.allfonts = PopUpButton((1, 0, -120, 22), allFontsNames)
        controls.addFont = GradientButton((-105, 0, -65, 22), title='Add', sizeStyle='small', callback=self.addMaster)
        controls.removeFont = GradientButton((-60, 0, -0, 22), title='Remove', sizeStyle='small', callback=self.removeMaster)
        dropSettings = {
            'type':'MyCustomPboardType',
            'operation': NSDragOperationNone,
            'allowDropOnRow':True,
            'callback': self.dropCallback }
        dragSettings = {
            'type':'MyCustomPboardType',
            'operation': NSDragOperationNone,
            'allowDropOnRow':True,
            'callback': self.dragCallback }
        controls.masters = List((0, 30, -0, -395),
            [],
            columnDescriptions= [
                {'title':'font', 'width':155},
                {'title':'vstem', 'editable':True, 'width':40},
                {'title':'hstem', 'editable':True, 'width':40}],
            editCallback=self.updateStems,
            selfDropSettings=dropSettings,
            dragSettings=dragSettings)
        controls.glyphSetTitle = TextBox((0, -122, 70, 22), 'Glyphset', sizeStyle='small')
        controls.glyphSet = ComboBox((70, -125, -0, 22),
            [
            'abcdefghijklmnopqrstuvwxyz',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            '0123456789',
            '/zero.LP/one.LP/two.LP/three.LP/four.LP/five.LP/six.LP/seven.LP/eight.LP/nine.LP',
            u'> Full glyphset',
            u'> Selected glyphs'
            ])
        controls.suffixTitle = TextBox((0, -92, 70, 22), 'Suffix', sizeStyle='small')
        controls.suffix = EditText((70, -95, -0, 22))
        controls.addToTitle = TextBox((0, -62, 70, 22), 'Add to', sizeStyle='small')
        allFontsNames.insert(0, 'New Font')
        controls.addTo = PopUpButton((70, -65, -0, 22), allFontsNames)

        scaleControls = [
            {'name':'width', 'title':'Width', 'unit':'%', 'value':'100.0'},
            {'name':'height', 'title':'Height', 'value':'750'},
            {'name':'keepSpacing', 'title':u'Don’t scale spacing', 'value':False},
            {'name':'stem', 'title':'Stem', 'value':'80'},
            {'name':'shift', 'title':'Shift', 'value':'0'},
            {'name':'tracking', 'title':'Tracking', 'unit':'%', 'value':'0'}
        ]
        controls.scaleGoalsTitle = TextBox((0, -380, -0, 19), 'Scale goals', sizeStyle='small')
        controls.scaleGoalsMode = TextBox((-140, -380, -0, 19), 'mode: Isotropic', sizeStyle='small', alignment='right')
        controls.scaleGoals = Box((0, -360, -0, (len(scaleControls)*32)+12))
        for i, control in enumerate(scaleControls):
            controlName = control['name']
            continuous = False
            if controlName in ['width','shift','tracking']:
                if controlName == 'shift': continuous = True
                setattr(controls.scaleGoals, '%s%s'%(controlName, 'Title'), TextBox((10, 10+(i*32), 200, 22), control['title'], sizeStyle='small'))
                setattr(controls.scaleGoals, controlName, EditText((65, 5+(i*32), 60, 22), control['value'], continuous=continuous, callback=self.scaleValueInput))
                inputControl = getattr(controls.scaleGoals, controlName)
                inputControl.name = controlName
            elif controlName == 'height':
                setattr(controls.scaleGoals, '%s%s'%(controlName, 'Title'), TextBox((10, 10+(i*32), 200, 22), control['title'], sizeStyle='small'))
                setattr(controls.scaleGoals, controlName, ComboBox((65, 5+(i*32), 60, 22), [], callback=self.scaleValueInput))
                inputControl = getattr(controls.scaleGoals, controlName)
                inputControl.name = controlName
            elif controlName == 'stem':
                setattr(controls.scaleGoals, '%s%s'%(controlName, 'Title'), TextBox((10, 10+(i*32), 200, 22), control['title'], sizeStyle='small'))
                setattr(controls.scaleGoals, '%s%s'%('v',controlName), ComboBox((65, 5+(i*32), 60, 22), [], callback=self.scaleValueInput))
                setattr(controls.scaleGoals, '%s%s'%('h',controlName), ComboBox((140, 5+(i*32), 60, 22), [], callback=self.scaleValueInput))
                setattr(controls.scaleGoals, 'mode', CheckBox((210, 5+(i*32), -0, 22), u'∞', value=True, callback=self.switchIsotropic, sizeStyle='small'))
                vInputControl = getattr(controls.scaleGoals, '%s%s'%('v',controlName))
                vInputControl.name = '%s%s'%('v',controlName)
                hInputControl = getattr(controls.scaleGoals, '%s%s'%('h',controlName))
                hInputControl.name = '%s%s'%('h',controlName)
                hInputControl.enable(False)
            if controlName == 'shift':
                controls.scaleGoals.shiftUp = SquareButton((140, 7+(i*32), 17, 17), u'⥘', sizeStyle='small', callback=self.scaleValueInput)
                controls.scaleGoals.shiftUp.name = 'shiftUp'
                controls.scaleGoals.shiftDown = SquareButton((160, 7+(i*32), 17, 17), u'⥕', sizeStyle='small', callback=self.scaleValueInput)
                controls.scaleGoals.shiftDown.name = 'shiftDown'
            if controlName == 'height':
                setattr(controls.scaleGoals, 'rel', TextBox((127, 5+(i*32), 15, 22), '/'))
                setattr(controls.scaleGoals, 'refHeight', PopUpButton((140, 5+(i*32), -10, 22), ['capHeight', 'xHeight', 'unitsPerEm', 'ascender', 'descender'], callback=self.scaleValueInput))
                refHeight = getattr(controls.scaleGoals, 'refHeight')
                refHeight.name = 'refHeight'
            if controlName == 'keepSpacing':
                setattr(controls.scaleGoals, controlName, CheckBox((65, 5+(i*32), -10, 22), control['title'], value=False, callback=self.scaleValueInput, sizeStyle='small'))
                spacingControl = getattr(controls.scaleGoals, controlName)
                spacingControl.name = controlName
            if controlName == 'tracking':
                setattr(controls.scaleGoals, 'trackingAbs', EditText((150, 5+(i*32), 60, 22), control['value'], continuous=False, callback=self.scaleValueInput))
                setattr(controls.scaleGoals, 'trackingAbsUnit', TextBox((215, 10+(i*32), -0, 22), 'upm', sizeStyle='mini'))
                inputControl = getattr(controls.scaleGoals, 'trackingAbs')
                inputControl.name = 'trackingAbs'
            if control.has_key('unit'):
                setattr(controls.scaleGoals, '%s%s'%(controlName, 'Unit'), TextBox((130, 8+(i*32), 40, 22), control['unit'], sizeStyle='small'))
        controls.apply = Button((0, -22, -0, 22), 'Generate glyphSet', callback=self.generateGlyphset)

        # self.glyphPreview = MultiLineView((280, 30, -0, -0), pointSize=176, selectionCallback=None)

        self.glyphPreview = Group((0, 0, -0, -0))
        glyphPreview = self.glyphPreview
        glyphPreview.glyphs = MultiLineView((0, 30, -0, -0), pointSize=176, lineHeight=264, hasVerticalScroller=False)
        self.displayStates = glyphPreview.glyphs.getDisplayStates()
        self.displayStates['Show Metrics'] = False
        self.displayStates['Upside Down'] = False
        self.displayStates['Stroke'] = False
        self.displayStates['Beam'] = False
        self.displayStates['Fill'] = True
        self.displayStates['Inverse'] = False
        self.displayStates['Multi Line'] = True
        self.displayStates['Water Fall'] = False
        self.displayStates['Single Line'] = False
        glyphPreview.glyphs.setDisplayStates(self.displayStates)
        glyphPreview.glyphs.setDisplayMode('Multi Line')
        self.displayModes = ['Multi Line', 'Water Fall']
        # glyphPreview.glyphs.setDisplayMode('Single Line')
        glyphPreview.vSep = VerticalLine((0, 0, 1, -0))
        glyphPreview.controls = Box((4, 0, -0, 30))
        glyphPreview.hSep = HorizontalLine((0, 32, -0, 1))
        previewControls = glyphPreview.controls
        previewControlsBox = previewControls.getNSBox()
        previewControlsBox.setBoxType_(NSBoxCustom)
        previewControlsBox.setFillColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(.85, .85, .85, 1))
        previewControlsBox.setBorderWidth_(0)
        previewControls.preGlyphInput = EditText((3, 3, 120, 22), callback=self.inputGlyphs)
        previewControls.glyphInput = EditText((126, 3, -183, 22), callback=self.inputGlyphs)
        previewControls.postGlyphInput = EditText((-180, 3, 100, 22), callback=self.inputGlyphs)
        previewControls.preGlyphInput.name = 'pre'
        previewControls.postGlyphInput.name = 'post'
        previewControls.pointSize = ComboBox((-73, 3, -10, 22), [str(p) for p in range(24,256, 8)], callback=self.pointSize)
        previewControls.pointSize.set(176)

        self.glyphPreviewSettings = Box((0, 0, -0, -0))
        previewSettings = self.glyphPreviewSettings.getNSBox()
        previewSettings.setBoxType_(NSBoxCustom)
        previewSettings.setFillColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(.85, .85, .85, 1))
        previewSettings.setBorderWidth_(0)
        self.glyphPreviewSettings.g = Group((10, 10, -0, -5))
        self.glyphPreviewSettings.g.displayModes = Box((0, 0, -0, 90))
        self.glyphPreviewSettings.g.displayModes.title = TextBox((10, 10, -10, 20), 'DISPLAY MODE', sizeStyle='mini')
        self.glyphPreviewSettings.g.displayModes.choice = RadioGroup((10, 30, -10, 40), self.displayModes, callback=self.changeDisplayMode, sizeStyle='small')
        self.glyphPreviewSettings.g.displayModes.choice.set(0)

        self.glyphPreviewSettings.g.showMetrics = CheckBox((0, 113, -0, 20), 'Show metrics', value=False, sizeStyle='small', callback=self.showMetrics)
        self.glyphPreviewSettings.g.showVerticalGuides = CheckBox((0, 133, -0, 20), 'Show vertical guides', value=False, sizeStyle='small', callback=self.showVerticalGuides)
        self.glyphPreviewSettings.g.verticalGuides = List((0, 160, -0, 175),
            [
            {'Line':'Descender', 'Height':-250 },
            {'Line':'Baseline', 'Height':0 },
            {'Line':'X height', 'Height':500 },
            {'Line':'Cap height', 'Height':750 },
            {'Line':'Ascender', 'Height':750 }
            ],
            columnDescriptions=[
                {'title':'Line', 'editable':True, 'width':100},
                {'title':'Height', 'editable':True}
            ],
            editCallback=self.editVerticalGuides
            )

        self.glyphPreviewSettings.g.addGuide = GradientButton((0, 340, 90, 20), title='Add guide', sizeStyle='small', callback=self.addVerticalGuide)
        self.glyphPreviewSettings.g.removeGuide = GradientButton((95, 340, 110, 20), title='Remove guide', sizeStyle='small', callback=self.removeVerticalGuide)

        panes = [
            dict(view=self.glyphPreview, identifier='glyphPreview'),
            dict(view=self.glyphPreviewSettings, identifier='glyphPreviewSettings', size=0)
        ]

        self.w.glyphSplitView = SplitView((280, 0, -0, -0), panes)

        self.scaleControlValues = {'width':1, 'height':750, 'vstem':None, 'hstem':None, 'shift': 0, 'tracking':(1, '%'), 'keepSpacing':False}
        self.vstemValues = []
        self.hstemValues = []
        self.masters = []
        self.preGlyphList = ''
        self.postGlyphList = ''
        self.glyphList = ''
        self.mode = 'isotropic'
        self.previousMode = None
        self.draggedIndex = None
        self.setGlyphs = []
        self.scaledGlyphs = []
        self.selectedGlyph = None
        self.verticalMetrics = {'descender':-250, 'baseline':0, 'xHeight':500, 'capHeight':750, 'ascender':750}
        self.multiLineRepresentations = {
            'verticalMetrics':{
                'Descender': -250,
                'Ascender': 750,
                'Baseline': 0,
                'X height': 500,
                'Cap height': 750
            },
            'colors': {
                'Descender': (0.8, 0.2, 0),
                'Ascender': (0.8, 0.2, 0),
                'Baseline': (0.3, 0.3, 0.3),
                'X height': (0.6, 0.6, 0.6),
                'Cap height': (0.6, 0.6, 0.6),
                'textColor': (0.6, 0.6, 0.6)
            },
            'selectedGlyph': None
        }
        self.stickyMetric = 'baseline'
        addObserver(self, 'drawMetrics', 'spaceCenterDraw')
        addObserver(self, 'updateFontList', 'fontDidOpen')
        addObserver(self, 'updateFontList', 'fontWillClose')
        self.w.bind('close', self.windowClose)
        self.w.open()

    # def glyphSelection(self, sender):
    #     selectedGlyph = sender.getSelectedGlyph()
    #     if selectedGlyph is not None:
    #         self.displayStates['Show metrics'] = True
    #         sender.setDisplayStates(self.displayStates)
    #         self.multiLineRepresentations['selectedGlyph'] = {
    #             'width': selectedGlyph.width,
    #             'left': selectedGlyph.leftMargin,
    #             'right': selectedGlyph.rightMargin
    #         }
    #         self.selectedGlyph = selectedGlyph

    #     if selectedGlyph is None:
    #         self.displayStates['Show metrics'] = False
    #         sender.setDisplayStates(self.displayStates)
    #         self.multiLineRepresentations['selectedGlyph'] = None
    #         self.selectedGlyph = None

    def drawMetrics(self, notification):
        glyphs = self.setGlyphs
        scaledGlyphs = self.scaledGlyphs
        selectedGlyph = self.selectedGlyph
        currentGlyph = notification['glyph']
        sc = notification['scale']
        showVerticalGuides = self.controllerDisplaySettings['showVerticalGuides']
        showMetrics = self.controllerDisplaySettings['showMetrics']
        verticalMetrics = self.multiLineRepresentations['verticalMetrics']
        colors = self.multiLineRepresentations['colors']
        if (currentGlyph.name is None) and showVerticalGuides:
            for key, value in verticalMetrics.items():
                save()
                width = currentGlyph.width
                if colors.has_key(key):
                    color = colors[key]
                elif not colors.has_key(key):
                    color = (.1, .1, .7, .75)
                # fill()
                stroke(*color)
                strokeWidth(0.5*sc)
                line((0, value), (100000, value))
                restore()

        if (currentGlyph in scaledGlyphs) and (currentGlyph.name != '_error_'):
            leftMargin = currentGlyph.leftMargin
            rightMargin = currentGlyph.rightMargin
            width = currentGlyph.width
            ascender = verticalMetrics['Ascender']
            descender = verticalMetrics['Descender']
            textColor = colors['textColor']
            metricsColor = colors['Descender']
            stroke()
            fontSize(8*sc)

    def generateGlyphset(self, sender):
        glyphString = self.w.controls.glyphSet.get()
        masters = self.masters
        if glyphString == u'> Full glyphset':
            glyphSet = masters[0]['font'].keys()
        elif glyphString == u'> Selected glyphs':
            glyphSet = CurrentFont().selection
        else:
            glyphSet = self.stringToGlyphNames(glyphString)
        if len(glyphSet):
            name, f = self.getSelectedFont(self.w.controls.addTo)
            suffix = glyphString = self.w.controls.suffix.get()
            scaleValues = self.scaleControlValues
            for glyphName in glyphSet:
                if glyphName == 'newLine': continue
                scaledGlyph = self.scaleGlyph(glyphName, masters, scaleValues)
                if scaledGlyph is not None:
                    f.insertGlyph(scaledGlyph, glyphName+suffix)
                    if scaledGlyph.name == '_error_':
                        f[glyphName+suffix].mark = (0.9, 0.2, 0, 0.9)
            f.round()
            f.autoUnicodes()
            f.showUI()

    def processGlyphs(self):
        masters = self.masters
        scaleValues = self.scaleControlValues
        stringToGlyphNames = self.stringToGlyphNames
        glyphNamesToGlyphs = self.glyphNamesToGlyphs
        glyphSet = stringToGlyphNames(self.glyphList)
        if len(masters) > 0:
            baseFont = masters[0]['font']
            preRefGlyph = [glyph for glyph in glyphNamesToGlyphs(baseFont, stringToGlyphNames(self.preGlyphList))]
            postRefGlyph = [glyph for glyph in glyphNamesToGlyphs(baseFont, stringToGlyphNames(self.postGlyphList))]
            marginGlyph = RGlyph()
            # marginGlyph.width = 300
            # marginGlyph.name = None
            preRefGlyph.insert(0, marginGlyph)
            scaledGlyphLine = []
            if len(masters) > 1 and len(glyphSet):
                for glyphName in glyphSet:
                    if glyphName == 'newLine':
                        scaledGlyph = self.glyphPreview.glyphs.createNewLineGlyph()
                    else:
                        scaledGlyph = self.scaleGlyph(glyphName, masters, scaleValues)
                    if scaledGlyph is not None:
                        scaledGlyphLine.append(scaledGlyph)
            self.scaledGlyphs = scaledGlyphLine
            scaledGlyphLine = preRefGlyph + scaledGlyphLine + postRefGlyph
            self.glyphPreview.glyphs.set(scaledGlyphLine)
            self.setGlyphs = scaledGlyphLine

    def scaleGlyph(self, glyphName, masters, scaleValues):
        width, height, wishedVStem, wishedHStem, shift, (trackingValue, trackingUnit), keepSpacing = scaleValues['width'], scaleValues['height'], scaleValues['vstem'], scaleValues['hstem'], scaleValues['shift'], scaleValues['tracking'], scaleValues['keepSpacing']
        mutatorMasters = []
        mode = self.mode
        isValid = self.isValidGlyph(glyphName, [master['font'] for master in masters])

        if isValid:

            refHeightName, refHeight = self.getScaleRefValue()
            baseMasterFont = masters[0]['font']
            italicAngle = baseMasterFont.info.italicAngle
            baseMasterGlyph = baseMasterFont[glyphName]
            baseMasterRefHeight = getattr(baseMasterFont.info, refHeightName)
            baseSc = height/baseMasterRefHeight
            requestedStemLocation = self.getInstanceLocation(masters[0], mode, wishedVStem, wishedHStem, baseSc)
            storedMargins = None

            if keepSpacing:
                if italicAngle and hasattr(baseMasterGlyph, 'angledLeftMargin') and hasattr(baseMasterGlyph, 'angledRightMargin'):
                    storedMargins = (baseMasterGlyph.angledLeftMargin, baseMasterGlyph.angledRightMargin)
                else:
                    storedMargins = (baseMasterGlyph.leftMargin, baseMasterGlyph.rightMargin)

                if (trackingUnit == '%'):
                    storedMargins = (storedMargins[0] * trackingValue, storedMargins[1] * trackingValue)
                elif trackingUnit == 'upm':
                    storedMargins = (storedMargins[0] + trackingValue, storedMargins[1] + trackingValue)

            for item in masters:
                masterFont = item['font']
                masterRefHeight = getattr(masterFont.info, refHeightName)
                sc = height/masterRefHeight
                baseGlyph = masterFont[glyphName]
                masterGlyph = decomposeGlyph(baseGlyph)
                masterGlyph.scale((sc*width, sc))
                if not keepSpacing or storedMargins is None:
                    masterGlyph.width = baseGlyph.width * sc * width

                if storedMargins is None:
                    if italicAngle and hasattr(masterGlyph, 'angledLeftMargin') and hasattr(masterGlyph, 'angledRightMargin'):
                        if (trackingUnit == '%'):
                            masterGlyph.angledLeftMargin *= trackingValue
                            masterGlyph.angledRightMargin *= trackingValue
                        elif trackingUnit == 'upm':
                            masterGlyph.angledLeftMargin += trackingValue
                            masterGlyph.angledRightMargin += trackingValue
                    else:
                        if trackingUnit == '%':
                            masterGlyph.leftMargin *= trackingValue
                            masterGlyph.rightMargin *= trackingValue
                        elif trackingUnit == 'upm':
                            masterGlyph.leftMargin += trackingValue
                            masterGlyph.rightMargin += trackingValue
                italicAngle = masterFont.info.italicAngle
                if italicAngle is not None:
                    xShift = shift * cos(radians(-italicAngle)+pi/2)
                    yShift = shift * sin(radians(-italicAngle)+pi/2)
                elif italicAngle is None:
                    xShift, yShift = 0, shift

                masterGlyph.move((xShift, yShift))
                if item.has_key('hstem') and (mode == 'bidimensionnal'):
                    axis = {'vstem':item['vstem']*sc*width, 'hstem':item['hstem']*sc}
                else:
                    axis = {'stem':item['vstem']*sc*width}
                mutatorMasters.append((Location(**axis), MathGlyph(masterGlyph)))

            instanceGlyph = self.getInstanceGlyph(requestedStemLocation, mutatorMasters)
            if keepSpacing and (storedMargins is not None) and (instanceGlyph.name != '_error_'):
                if italicAngle and hasattr(instanceGlyph, 'angledLeftMargin') and hasattr(instanceGlyph, 'angledRightMargin'):
                    instanceGlyph.angledLeftMargin = storedMargins[0]
                    instanceGlyph.angledRightMargin = storedMargins[1]
                else:
                    instanceGlyph.leftMargin = storedMargins[0]
                    instanceGlyph.rightMargin = storedMargins[1]
            return instanceGlyph
        return errorGlyph()

    def getInstanceGlyph(self, location, masters):
        I = self.getInstance(location, masters)
        if I is not None:
            return I.extractGlyph(RGlyph())
        else:
            return errorGlyph()

    def getInstance(self, location, masters):
        try:
            b, m = buildMutator(masters)
            if m is not None:
                instance = m.makeInstance(location)
                return instance
        except:
            return

    def switchIsotropic(self, sender):
        if len(self.masters):
            b = not bool(sender.get())
            if b == False: self.setMode('isotropic')
            elif b == True: self.setMode('anisotropic')
            self.processGlyphs()
        else:
            sender.set(not sender.get())

    def getInstanceLocation(self, master, mode, vstem, hstem, sc):
        if not master.has_key('hstem') and (mode == 'anisotropic'):
            mastersList = self.w.controls.masters.get()
            hStems = [item['hstem']*sc for item in mastersList]
            vStems = [item['vstem'] for item in mastersList]
            hStems = (min(hStems), max(hStems))
            vStems = (min(vStems), max(vStems))
            hstem = mapValue(hstem, hStems, vStems)
            hstem *= sc
            return Location(stem=(vstem, hstem))
        elif master.has_key('hstem'):
            return Location(vstem=vstem, hstem=hstem)
        else: return Location(stem=vstem)

    def scaleValueInput(self, sender):
        scaleValueName = sender.name
        if isinstance(sender, (EditText, ComboBox, PopUpButton, CheckBox)):
            value = sender.get()
        if scaleValueName == 'width':
            try: value = float(value)/100.0
            except: value = 1
        elif scaleValueName == 'tracking':
            try: value = (1 + float(value)/100.0, '%')
            except: value = (1, '%')
        elif scaleValueName == 'trackingAbs':
            try: value = (float(value), 'upm')
            except: value = (0, 'upm')
            scaleValueName = 'tracking'
        elif scaleValueName == 'height':
            try: value = float(value)
            except: value = 750
        elif scaleValueName == 'keepSpacing':
            value = bool(value)
        elif scaleValueName in ['vstem', 'hstem']:
            try: value = int(value)
            except: value = 80
        elif scaleValueName == 'shift':
            try: value = int(value)
            except: value = 0
        elif scaleValueName == 'shiftUp':
            shift = self.scaleControlValues['shift']
            height = int(self.w.controls.scaleGoals.height.get())
            verticalMetrics = self.verticalMetrics
            value = shift
            for metric in ['xHeight', 'capHeight', 'ascender']:
                if shift < 0:
                    value = 0
                    self.w.controls.scaleGoals.shift.set(str(value))
                    self.stickyMetric = 'baseline'
                    break
                elif shift >= 0:
                    if (shift + height) < verticalMetrics[metric]:
                        value = int(round(verticalMetrics[metric] - height))
                        self.w.controls.scaleGoals.shift.set(str(value))
                        self.stickyMetric = metric
                        break
                    else:
                        continue
            scaleValueName = 'shift'
        elif scaleValueName == 'shiftDown':
            shift = self.scaleControlValues['shift']
            height = int(self.w.controls.scaleGoals.height.get())
            verticalMetrics = self.verticalMetrics
            value = shift
            for metric in ['ascender', 'capHeight', 'xHeight', 'baseline', 'descender']:
                if shift > verticalMetrics[metric]:
                    value = int(round(verticalMetrics[metric]))
                    self.w.controls.scaleGoals.shift.set(str(value))
                    break
                else:
                    continue
            scaleValueName = 'shift'
        self.scaleControlValues[scaleValueName] = value
        self.processGlyphs()

    def getScaleRefValue(self):
        refValueIndex = self.w.controls.scaleGoals.refHeight.get()
        refValueName = self.w.controls.scaleGoals.refHeight.getItems()[refValueIndex]
        sourceFont = self.masters[0]['font']
        return refValueName, getattr(sourceFont.info, refValueName)

    def inputGlyphs(self, sender):
        inputString = sender.get()
        if hasattr(sender, 'name'):
            if sender.name == 'pre':
                self.preGlyphList = inputString
            elif sender.name == 'post':
                self.postGlyphList = inputString
        elif not hasattr(sender, 'name'):
            self.glyphList = inputString
        self.processGlyphs()

    def stringToGlyphNames(self, string):
        cmap = self.getCMap()
        if cmap is not None:
            glyphLines = []
            lines = string.split('\\n')
            l = len(lines)
            for i, line in enumerate(lines):
                glyphs = splitText(line, cmap)
                if 0 < i < l:
                    glyphs.append('newLine')
                glyphLines += glyphs
            return glyphLines
        return []

    def glyphNamesToGlyphs(self, font, glyphSet):
        glyphs = []
        for glyphName in glyphSet:
            if glyphName == 'newLine':
                glyph = self.glyphPreview.glyphs.createNewLineGlyph()
                glyphs.append(glyph)
            elif glyphName in font:
                glyph = font[glyphName]
                glyphs.append(glyph)
        return glyphs

    def getCMap(self):
        masters = self.masters
        if len(masters):
            sourceFont = masters[0]['font']
            return sourceFont.getCharacterMapping()
        return None

    def pointSize(self, sender):
        value = sender.get()
        try: value = float(value)
        except: value = 72
        self.glyphPreview.glyphs.setPointSize(value)
        self.glyphPreview.glyphs.setLineHeight(value*1.5)

    def isValidGlyph(self, glyph, fonts):
        isValid = True
        for font in fonts:
            isValid *= glyph in font
            if not isValid: break
        return bool(isValid)

    def approximateVStemWidth(self, font):
        if 'I' in font:
            testGlyph = font['I']
            xMin, yMin, xMax, yMax = testGlyph.box
            hCenter = (yMax - yMin)/2
            i = IntersectGlyphWithLine(testGlyph, ((-200, hCenter), (testGlyph.width+200, hCenter)))
            stemWidth = abs(i[1][0]-i[0][0])
            return int(round(stemWidth))
        return 0

    def approximateHStemWidth(self, font):
        if 'H' in font:
            testGlyph = font['H']
            xMin, yMin, xMax, yMax = testGlyph.box
            vCenter = xMin+(xMax - xMin)/2
            i = IntersectGlyphWithLine(testGlyph, ((vCenter, -500), (vCenter, 1200)))
            stemWidth = abs(i[1][1]-i[0][1])
            return int(round(stemWidth))
        return 0

    def updateStems(self, sender):
        mastersNameAndStem = sender.get()
        if len(mastersNameAndStem):
            inputStemValues = ['%s,%s'%(item['vstem'],item['hstem']) for item in mastersNameAndStem]
            stemValues = self.getStemValues(inputStemValues)
            for i, item in enumerate(stemValues):
                masterFont = self.masters[i]['font']
                self.masters[i] = item
                self.masters[i]['font'] = masterFont
            self.processGlyphs()

    def getStemValues(self, stems):
        previousMode = self.previousMode
        split = self.splitStemValue
        stemValues = [split(stem) for stem in stems]
        keepHStem = self.checkForSecondAxisCondition([item['hstem'] for item in stemValues])
        if (not keepHStem and len(stemValues) > 2) or (len(stemValues) <= 2):
            for stemValue in stemValues: stemValue.pop('hstem', None)
            if (previousMode is not None) and (self.mode not in ['isotropic', 'anisotropic']):
                self.setMode(previousMode)
                self.previousMode = None
            else:
                self.setMode('isotropic')
        else:
            self.setMode('bidimensionnal')
        return stemValues

    def splitStemValue(self, stem):
        s = re.search('(\d+)(,\s?(\d+))?', repr(stem))
        if s:
            if s.group(1) is not None:
                vstem = float(s.group(1))
            else:
                vstem = None
            if s.group(3) is not None:
                hstem = float(s.group(3))
            else:
                hstem = None
            return dict(vstem=vstem, hstem=hstem)
        return 0

    def checkForSecondAxisCondition(self, values):
        if len(values):
            eq = 0
            neq = 0
            l = len(values)
            for i,value in enumerate(values):
                n1value = values[(i+1)%l]
                if n1value == value: eq += 1
                if n1value != value: neq += 1
            return bool(eq) and bool(neq)
        return

    def checkSimilarity(self, values):
        if len(values):
            eq = 1
            for i, value in enumerate(values):
                if i > 0:
                    eq *= (value == prevValue)
                prevValue = value
            return bool(eq)

    def setMode(self, modeName):
        self.w.controls.scaleGoalsMode.set('mode: %s'%(modeName.capitalize()))
        if modeName == 'isotropic':
            self.w.controls.scaleGoals.mode.show(True)
            self.w.controls.scaleGoals.mode.set(True)
            self.w.controls.scaleGoals.hstem.set('')
            self.w.controls.scaleGoals.hstem.enable(False)
        elif modeName == 'anisotropic':
            self.w.controls.scaleGoals.mode.show(True)
            self.w.controls.scaleGoals.mode.set(False)
            # value = self.w.controls.scaleGoals.vstem.get()
            hValue = self.scaleControlValues['hstem']
            self.w.controls.scaleGoals.hstem.set(hValue)
            self.w.controls.scaleGoals.hstem.enable(True)
            # self.scaleControlValues['hstem'] = float(value)
        elif modeName == 'bidimensionnal':
            if self.mode == 'isotropic':
                self.previousMode = 'isotropic'
            elif self.mode == 'anisotropic':
                self.previousMode = 'anisotropic'
            self.w.controls.scaleGoals.mode.show(False)
            self.w.controls.scaleGoals.hstem.set(self.hstemValues[0])
            self.w.controls.scaleGoals.hstem.enable(True)
            self.scaleControlValues['hstem'] = self.hstemValues[0]
        self.mode = modeName

    def dropCallback(self, sender, dropInfo):
        if (self.draggedIndex is not None):
            sourceIndex = self.draggedIndex
            destinationIndex = dropInfo['rowIndex']
            mastersList = sender.get()
            masters = self.masters
            if (sourceIndex != 0) and (destinationIndex == 0):
                for itemsList in [mastersList, masters, self.vstemValues, self.hstemValues]:
                    draggedItem = itemsList.pop(sourceIndex)
                    itemsList.insert(0, draggedItem)
                font = masters[0]['font']
                for attribute in ['descender', 'xHeight', 'capHeight', 'ascender']:
                    self.verticalMetrics[attribute] = getattr(font.info, attribute)
                vstem, hstem = self.scaleControlValues['vstem'], self.scaleControlValues['hstem'] = mastersList[0]['vstem'], mastersList[0]['hstem']
                self.w.controls.scaleGoals.vstem.set(vstem)
                self.w.controls.scaleGoals.hstem.set(hstem)
                sender.set(mastersList)

    def dragCallback(self, sender, dropInfo):
        self.draggedIndex = dropInfo[0]

    def addMaster(self, sender):
        controls = self.w.controls
        masterNamesList = controls.masters
        selectedFontName, selectedFont = self.getSelectedFont(self.w.controls.allfonts)
        mastersList = masterNamesList.get()
        namesOnly = [item['font'] for item in mastersList]
        if selectedFontName not in namesOnly:
            vstem = self.approximateVStemWidth(selectedFont)
            hstem = self.approximateHStemWidth(selectedFont)
            mastersList.append({'font':selectedFontName, 'vstem':vstem, 'hstem':hstem})
            self.masters.append({'font':selectedFont, 'vstem':vstem, 'hstem':hstem})
            masterNamesList.set(mastersList)
            self.vstemValues.append(vstem)
            self.hstemValues.append(hstem)
            self.w.controls.scaleGoals.vstem.setItems(self.vstemValues)
            self.w.controls.scaleGoals.hstem.setItems(self.hstemValues)
            if len(mastersList) == 1:
                self.setMainFont(controls, selectedFont, vstem, hstem)
            self.updateStems(masterNamesList)
            self.processGlyphs()

    def removeMaster(self, sender):
        masterNamesList = self.w.controls.masters
        selectedFontName, selectedFont = self.getSelectedFont(self.w.controls.allfonts)
        mastersToRemove = masterNamesList.getSelection()
        mastersList = masterNamesList.get()
        for i in reversed(mastersToRemove):
            vstem = self.approximateVStemWidth(selectedFont)
            hstem = self.approximateHStemWidth(selectedFont)
            mastersList.pop(i)
            self.masters.pop(i)
            self.vstemValues.pop(i)
            self.hstemValues.pop(i)
            self.w.controls.scaleGoals.vstem.setItems(self.vstemValues)
            self.w.controls.scaleGoals.hstem.setItems(self.hstemValues)
        masterNamesList.set(mastersList)
        self.updateStems(masterNamesList)
        self.processGlyphs()

    def setMainFont(self, controls, font, vstem, hstem):
        self.glyphPreview.glyphs.setFont(font)
        controls.scaleGoals.vstem.set(vstem)
        controls.scaleGoals.hstem.set(hstem)
        controls.scaleGoals.height.setItems([str(getattr(font.info, height)) for height in ['capHeight', 'xHeight', 'unitsPerEm']])
        controls.scaleGoals.height.set(str(font.info.capHeight))
        self.scaleControlValues['vstem'] = vstem
        self.scaleControlValues['hstem'] = hstem
        for attribute in ['descender', 'xHeight', 'capHeight', 'ascender']:
            self.verticalMetrics[attribute] = getattr(font.info, attribute)
        self.scaleControlValues['height'] = self.verticalMetrics['capHeight']
        self.multiLineRepresentations['verticalMetrics'] = {
            'Descender': self.verticalMetrics['descender'],
            'Ascender': self.verticalMetrics['ascender'],
            'Baseline': 0,
            'X height': self.verticalMetrics['xHeight'],
            'Cap height': self.verticalMetrics['capHeight']
        }
        guides = self.glyphPreviewSettings.g.verticalGuides.get()
        addedGuides = []
        if len(guides) > 5:
            addedGuides = guides[5:]
        guides = [
            {'Line': 'Descender', 'Height':self.verticalMetrics['descender']},
            {'Line': 'Baseline', 'Height':0},
            {'Line': 'X height', 'Height':self.verticalMetrics['xHeight']},
            {'Line': 'Cap height', 'Height':self.verticalMetrics['capHeight']},
            {'Line': 'Ascender', 'Height':self.verticalMetrics['ascender']}
        ]
        guides += addedGuides
        self.glyphPreviewSettings.g.verticalGuides.set(guides)

    def getSelectedFont(self, popuplist):
        fontIndex = popuplist.get()
        fontName = popuplist.getItems()[fontIndex]
        if fontName == 'New Font':
            return fontName, RFont(showUI=False)
        else:
            try: return fontName, AllFonts().getFontsByFamilyNameStyleName(*fontName.split(' > '))
            except: return RFont()

    def updateFontList(self, notification):
        notifiedFont = notification['font']
        notifiedFontName = fontName(notifiedFont)
        for fontlist in [self.w.controls.allfonts, self.w.controls.addTo]:
            namesList = fontlist.getItems()
            if notification['notificationName'] == 'fontDidOpen':
                namesList.append(notifiedFontName)
            elif notification['notificationName'] == 'fontWillClose':
                if notifiedFontName in namesList:
                    namesList.remove(notifiedFontName)
                masterList = self.w.controls.masters.get()
                fontsToRemove = []
                for i,item in enumerate(masterList):
                    name = item['font']
                    if name == notifiedFontName:
                        fontsToRemove.append(i)
                for index in fontsToRemove:
                    masterList.pop(i)
                self.w.controls.masters.set(masterList)
            fontlist.setItems(namesList)

    def changeDisplayMode(self, sender):
        index = sender.get()
        for i, mode in enumerate(self.displayModes):
            if i == index:
                modeName =  mode
                self.displayStates[mode] = True
            else:
                self.displayStates[mode] = False
        self.glyphPreview.glyphs.setDisplayStates(self.displayStates)
        self.glyphPreview.glyphs.setDisplayMode(modeName)

    def editVerticalGuides(self, sender):
        guides = self.glyphPreviewSettings.g.verticalGuides.get()
        self.multiLineRepresentations['verticalMetrics'] = {}
        for guide in guides:
            guideName = guide['Line']
            guideHeight = guide['Height']
            self.multiLineRepresentations['verticalMetrics'][guideName] = float(guideHeight)
        self.processGlyphs()

    def addVerticalGuide(self, sender):
        guides = self.glyphPreviewSettings.g.verticalGuides.get()
        l = len(guides)
        newGuideName = 'New guide %s'%(l-4)
        guides.append({'Line': newGuideName, 'Height':0})
        self.glyphPreviewSettings.g.verticalGuides.set(guides)
        self.multiLineRepresentations['verticalMetrics'][newGuideName] = 0

    def removeVerticalGuide(self, sender):
        guides = self.glyphPreviewSettings.g.verticalGuides.get()
        selection = self.glyphPreviewSettings.g.verticalGuides.getSelection()
        for i in reversed(selection):
            if i > 4:
                guideName = guides[i]['Line']
                self.multiLineRepresentations['verticalMetrics'].pop(guideName, 0)
                guides.pop(i)
        self.glyphPreviewSettings.g.verticalGuides.set(guides)

    def showVerticalGuides(self, sender):
        value = bool(sender.get())
        self.controllerDisplaySettings['showVerticalGuides'] = value
        self.processGlyphs()

    def showMetrics(self, sender):
        value = bool(sender.get())
        self.displayStates['Show Metrics'] = value
        self.glyphPreview.glyphs.setDisplayStates(self.displayStates)
        self.glyphPreview.glyphs.setCanSelect(value)
        self.processGlyphs()

    def windowClose(self, notification):
        removeObserver(self, 'fontDidOpen')
        removeObserver(self, 'fontWillClose')
        removeObserver(self, 'spaceCenterDraw')

ScaleController()

