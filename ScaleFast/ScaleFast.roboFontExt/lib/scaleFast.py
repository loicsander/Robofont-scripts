#coding=utf-8
from __future__ import division

__version__ = 0.93

"""
Written by Loïc Sander
–
Version history
1. novembre 2014
2. march 2015
3. june 2015
—
ScaleFast is a Robofont extension with a simple mission:
trying to maintain stem width while you transform a glyph.
To do that, the tool relies on masters (you need at least two),
analyses them and does its best to keep stems consistent
through interpolation, powered by Erik van Blokland’s MutatorMath.

Thanks to Frederik Berlaen for the inspiration.
"""
from mutatorScale.objects.scaler import MutatorScaleEngine
from mutatorScale.utilities.fontUtils import makeListFontName, getRefStems

import parameters.vanillaParameterObjects
from parameters.vanillaParameterObjects import VanillaSingleValueParameter, ParameterTextInput
from parameters.baseParameter import SingleValueParameter

from vanilla import *
from mojo.events import addObserver, removeObserver
from mojo.UI import MultiLineView
from mojo.drawingTools import *

from AppKit import NSColor, NSBoxCustom
# NSTableViewAnimationSlideLeft, NSIndexSet, NSAnimationTriggerOrderOut
from defconAppKit.tools.textSplitter import splitText
from math import cos, sin, radians, pi


def parsesToNumber(string):
    try:
        a = float(string)
        return True
    except:
        return False


def extractSelectedItem(popUpButton):
    index = popUpButton.get()
    return popUpButton.getItems()[index]



class ScaleFastPreset(object):


    def __init__(self, preset, obsolete=False):
        if obsolete == True:
            self.initWithOldPreset(preset)
        else:
            name, settings = preset
            self.init(name, **settings)


    def init(self, name, vstem, hstem, stemRapport, isotropic, referenceHeight, targetHeight, width, posX=0, posY=0, stickyPos=('bottom','baseline'), tracking=(0, 'upm'), keepSidebearings=False):
        self.name = name
        self.settings = {
            'vstem': vstem,
            'hstem': hstem,
            'stemRapport': stemRapport,
            'referenceHeight': referenceHeight,
            'targetHeight': targetHeight,
            'width': width,
            'posX': posX,
            'posY': posY,
            'stickyPos': stickyPos,
            'keepSidebearings': keepSidebearings,
            'tracking': tracking,
            'isotropic': isotropic
        }


    def initWithOldPreset(self, oldPreset):
        name, oldSettings = oldPreset

        settings = {}

        value, units = oldSettings['tracking']
        if units == 'upm':
            settings['tracking'] = oldSettings['tracking']
        elif units == '%':
            settings['tracking'] = ((value-1)*100, '%')

        settings['stemRapport'] = 'absolute'
        settings['referenceHeight'] = 'capHeight'
        settings['posY'] = oldSettings['shift']
        settings['isotropic'] = True if oldSettings['mode'] == 'isotropic' else False

        for key1, key2 in [('targetHeight','height'), ('keepSidebearings','keepSpacing')]:
            settings[key1] = oldSettings[key2]

        for key in ['vstem','hstem','width']:
            settings[key] = oldSettings[key]

        self.init(name, **settings)


    def setName(self, newName):
        self.name = newName


    def set(self, settings):
        for key in settings:
            self.settings[key] = settings[key]



class ScaleFastController(object):

    includedGlyph = u'↳'

    def __init__(self):

        if CurrentFont() is None:
            print u'ScaleFast — No open font.'
            return

        self.availableFonts = {makeListFontName(font):{'font':font, 'selected':False, 'vstem':None, 'hstem':None, 'familyName':font.info.familyName, 'styleName':font.info.styleName} for font in AllFonts()}

        self.scalingMasters = MutatorScaleEngine()

        # initiating window
        self.w = Window((1100, 650), 'ScaleFast %s' % (__version__), minSize=(800, 550))
        self.controlsBox = Box((0, 0, -0, -0))
        self.controlsBox.settings = Group((20, -412, -10, -15))
        controls = self.controlsBox.settings

        # Masters’ list
        masterFontsItems = [{self.includedGlyph:False, 'font':fontName} for fontName in self.availableFonts]

        masterFontsListColumnDescription = [
            {'title':self.includedGlyph, 'width': 20, 'editable':True, 'cell':CheckBoxListCell()},
            {'title':'vstem', 'editable':True, 'width':40},
            {'title':'hstem', 'editable':True, 'width':40},
            {'title':'font', 'editable':False}
        ]

        self.w.titles = Group((6, 15, 12, -15))
        self.w.titles.masters = TextBox((0, 32, -0, -412), 'MASTERS', sizeStyle='mini', alignment='center')
        self.w.titles.stems = TextBox((0, -402, -0, 88), 'STEMS', sizeStyle='mini', alignment='center')
        self.w.titles.height = TextBox((0, -314, -0, 62), 'HEIGHT', sizeStyle='mini', alignment='center')
        self.w.titles.width = TextBox((0, -252, -0, 62), 'WIDTH', sizeStyle='mini', alignment='center')
        self.w.titles.position = TextBox((0, -190, -0, 94), 'POSITION', sizeStyle='mini', alignment='center')
        self.w.titles.tracking = TextBox((0, -96, -0, 62), 'TRACKING', sizeStyle='mini', alignment='center')

        for key in ['masters','stems','height','width','position','tracking']:
            titleField = getattr(self.w.titles, key)
            titleField.getNSTextField().rotateByAngle_(-90)
            titleField.getNSTextField().setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.5, 0.5, 1))

        self.controlsBox.selectedFont = PopUpButton((20, 15, -10, 22), self.availableFonts, callback=self._selectedFontChanged)

        self.controlsBox.masterFonts = List((20, 42, -10, -427),
            masterFontsItems,
            columnDescriptions= masterFontsListColumnDescription,
            editCallback=self._editMasterFontsList,
            allowsMultipleSelection=False,
            rowHeight=20,
            drawVerticalLines=True)

        self.currentStems = {
            'vstem': SingleValueParameter('currentVstem', 0),
            'hstem': SingleValueParameter('currentHstem', 0)
        }
        self.definedStems = {
            'vstem': VanillaSingleValueParameter('definedVstem', master=self.currentStems['vstem'], mode='offset'),
            'hstem': VanillaSingleValueParameter('definedHstem', master=self.currentStems['hstem'], mode='offset')
        }

        controls.stemBox = Box((0, 0, -0, 78))
        controls.stemBox.switch = RadioGroup((10, 5, 90, -5), ['Offset','Ratio','Absolute'], isVertical=True, callback=self._switchParameterModeCallback, sizeStyle='small')
        controls.stemBox.switch.set(0)
        controls.stemBox.vTitle = TextBox((-210, 15, 60, 22), 'Vertical', sizeStyle='small')
        controls.stemBox.hTitle = TextBox((-210, 40, 60, 22), 'Horizontal', sizeStyle='small')
        controls.stemBox.vstem = ParameterTextInput(self.definedStems['vstem'], (-140, 10, 95, 22), callback=self._stemsUpdated, showRelativeValue=True)
        controls.stemBox.hstem = ParameterTextInput(self.definedStems['hstem'], (-140, 35, 95, 22), callback=self._stemsUpdated, showRelativeValue=True)
        controls.stemBox.hstem.enable(False)
        controls.stemBox.isotropic = CheckBox((-40, 22, -0, 22), u'∞', value=True, callback=self._switchIsotropicCallback)

        # Scale

        self.scalingGoals = {
            'referenceHeight': 'capHeight',
            'targetHeight': 'capHeight',
            'width': 1
        }
        self.transformations = {
            'posX': 0,
            'posY': 0,
            'tracking': (0, 'upm'),
            'stickyPos': ('bottom','baseline'),
            'keepSidebearings': False
        }
        self.heightReferences = ['capHeight','xHeight','ascender','descender','unitsPerEm']

        # Vertical scale
        controls.verticalScaleBox = Box((0, 88, -0, 52))
        controls.verticalScaleBox.referenceHeight = ComboBox((10, 10, 100, 22), self.heightReferences, callback=self._setReferenceHeight)
        controls.verticalScaleBox.referenceHeight.set('capHeight')
        controls.verticalScaleBox.toSize = TextBox((110, 10, 20, 22), u'▹', alignment='center')
        controls.verticalScaleBox.targetHeightSlider = Slider((130, 10, -70, 22), value=1, minValue=0.1, maxValue=2, callback=self._setTargetHeight)
        controls.verticalScaleBox.targetHeightInput = EditText((-60, 10, -10, 22), continuous=False, callback=self._setTargetHeight)

        # Horizontal scale
        controls.horizontalScaleBox = Box((0, 150, -0, 52))
        controls.horizontalScaleBox.widthSlider = Slider((10, 10, -100, 22), value=1, minValue=0, maxValue=3, callback=self._setWidth)
        controls.horizontalScaleBox.widthInput = EditText((-90, 10, -40, 22), continuous=False, callback=self._setWidth)
        controls.horizontalScaleBox.unit = TextBox((-30, 10, -10, 22), '%')

        # Position shift
        controls.posShift = Box((0, 212, 85, 84))
        controls.posShift.xShiftTitle = TextBox((5, 15, 10, 17), 'X', sizeStyle='small')
        controls.posShift.xShift = EditText((20, 10, 50, 22), self.transformations['posX'], self._changePosition, continuous=False)
        controls.posShift.xShift.key = 'posX'
        controls.posShift.yShiftTitle = TextBox((5, 47, 10, 17), 'Y', sizeStyle='small')
        controls.posShift.yShift = EditText((20, 42, 50, 22), self.transformations['posY'], self._changePosition, continuous=False)
        controls.posShift.yShift.key = 'posY'

        # Sticky
        stickyParts = ['bottom','center','top']
        self.alignmentGuides = ['baseline','capHeight','ascender','descender','xHeight']


        controls.stickyTitle = TextBox((95, 220, -0, 17), 'Sticky', sizeStyle='small')
        controls.sticky = Box((95, 244, -0, 52))
        controls.sticky.zone = ComboBox((10, 10, 90, 22), stickyParts, callback=self._changeStickyPos)
        controls.sticky.zone.set('bottom')
        controls.sticky.zone.name = 'zone'
        controls.sticky.alignment = ComboBox((-120, 10, -10, 22), self.alignmentGuides, callback=self._changeStickyPos)
        controls.sticky.alignment.set('baseline')
        controls.sticky.alignment.name = 'alignment'

        # Tracking
        controls.tracking = Box((0, 306, -0, 52))
        controls.tracking.input = EditText((10, 10, 50, 22), '0', self._changeTracking)
        controls.tracking.units = PopUpButton((70, 10, 60, 22), ['upm','%'], self._changeTrackingUnits)
        controls.tracking.dontScaleSpacing = CheckBox((145, 13, -10, 17), u'Keep initial sidebearings', value=self.transformations['keepSidebearings'], sizeStyle='small', callback=self._keepSidebearings)

        # Generate
        controls.generate = Button((0, 373, -0, 22), 'Generate', callback=self._buildGenerationSheet)

        # MultilineView = glyph preview
        self.glyphPreviewBox = Group((0, 0, -0, -0))
        self.glyphPreviewBox.preview = MultiLineView((0, 30, -0, -0), pointSize=176, lineHeight=264, hasVerticalScroller=False)
        self.multiLineViewDisplayStates = self.glyphPreviewBox.preview.getDisplayStates()
        reset = {
            'Show Metrics': False,
            'Upside Down': False,
            'Stroke': False,
            'Beam': False,
            'Fill': True,
            'Inverse': False,
            'Multi Line': True,
            'Water Fall': False,
            'Single Line': False
            }
        for setting, value in reset.items():
            self.multiLineViewDisplayStates[setting] = value

        self.glyphPreviewBox.preview.setDisplayStates(self.multiLineViewDisplayStates)
        self.glyphPreviewBox.preview.setDisplayMode('Multi Line')
        self.glyphPreviewBox.preview.setCanSelect(True)

        # Mode display
        self.glyphPreviewBox.mode = TextBox((-200, -25, -15, 20), 'mode: Isotropic', alignment='right', sizeStyle='small')
        self.glyphPreviewBox.mode.getNSTextField().setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.5, 0.5, 1))

        # String inputs
        inputList = [
            ('pre', (0, 3, 120, 22)),
            ('scaled', (123, 3, -186, 22)),
            ('post', (-183, 3, -83, 22))
        ]

        for itemBaseName, posSize in inputList:
            itemName = '%sStringInput' % (itemBaseName)
            setattr(self.glyphPreviewBox, itemName, EditText(posSize, callback=self._inputGlyphs))
            inputItem = getattr(self.glyphPreviewBox, itemName)
            inputItem.name = itemBaseName

        # Point size setting
        self.glyphPreviewBox.pointSize = ComboBox((-73, 3, -10, 22), [str(p) for p in range(24,256, 8)], callback=self._pointSize)
        self.glyphPreviewBox.pointSize.set(176)

        self.previewSettings = {
            'displayModes': ['Multi Line', 'Water Fall'],
            'drawVerticalMetrics': False,
            'selectedGlyph': None,
        }
        self.displayModes = ['Multi Line', 'Water Fall']
        self.guideColor = (0.75, 0.5, 0.5, 0.75)
        self.presets = []
        self.batchGenerationList = []

        self.scaleFastSettings = Box((0, 0, -0, -0))
        previewSettings = self.scaleFastSettings.getNSBox()
        previewSettings.setBoxType_(NSBoxCustom)
        previewSettings.setFillColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(.85, .85, .85, 1))
        previewSettings.setBorderWidth_(0)
        self.scaleFastSettings.g = Group((10, 10, -0, -0))
        self.scaleFastSettings.g.displayModes = Box((0, 0, -0, 90))
        self.scaleFastSettings.g.displayModes.title = TextBox((10, 10, -10, 20), 'DISPLAY MODE', sizeStyle='mini')
        self.scaleFastSettings.g.displayModes.choice = RadioGroup((10, 30, -10, 40), self.previewSettings['displayModes'], callback=self.changeDisplayMode, sizeStyle='small')
        self.scaleFastSettings.g.displayModes.choice.set(0)

        self.scaleFastSettings.g.showMetrics = CheckBox((0, 113, -0, 20), 'Show metrics', value=False, sizeStyle='small', callback=self.showMetrics)
        self.scaleFastSettings.g.showVerticalGuides = CheckBox((0, 133, -0, 20), 'Show vertical guides', value=False, sizeStyle='small', callback=self.showVerticalGuides)
        self.scaleFastSettings.g.verticalGuides = List((0, 160, -0, 155),
            [],
            columnDescriptions=[
                {'title':'Name', 'editable':True, 'width':100},
                {'title':'Height', 'editable':True}
            ],
            editCallback=self._editVerticalGuides
            )

        self.scaleFastSettings.g.addGuide = GradientButton((0, 320, 90, 20), title='Add guide', sizeStyle='small', callback=self._addVerticalGuide)
        self.scaleFastSettings.g.removeGuide = GradientButton((95, 320, 110, 20), title='Remove guide', sizeStyle='small', callback=self._removeVerticalGuide)

        self.scaleFastSettings.g.presets = Box((0, 365, -10, 210))
        self.scaleFastSettings.g.presets.g = Group((10, 10, -10, -10))
        self.scaleFastSettings.g.presets.g.title = TextBox((28, 0, -0, 20), 'PRESETS', sizeStyle='mini')
        self.scaleFastSettings.g.presets.g.presetsList = List((28, 20, -0, 135), [], allowsMultipleSelection=False, editCallback=self._editPresetNames)
        self.scaleFastSettings.g.presets.g.addPreset = GradientButton((28, 160, 60, 20), title='Add', sizeStyle='small', callback=self._addPreset)
        self.scaleFastSettings.g.presets.g.updatePreset = GradientButton((88, 160, 70, 20), title='Update', sizeStyle='small', callback=self._updatePreset)
        self.scaleFastSettings.g.presets.g.removePreset = GradientButton((158, 160, 70, 20), title='Remove', sizeStyle='small', callback=self._removePreset)
        self.scaleFastSettings.g.presets.g.loadPreset = Button((0, 72, 20, 25), '<', sizeStyle='small', callback=self._applyPresetCallback)

        # SplitView: glyph preview and settings hidden from view on the right
        panes = [
            dict(view=self.controlsBox, identifier='controls', minSize=375, maxSize=375),
            dict(view=self.glyphPreviewBox, identifier='glyphPreview'),
            dict(view=self.scaleFastSettings, identifier='glyphPreviewSettings', size=0)
        ]

        self.w.glyphSplitView = SplitView((0, 0, -0, -0), panes)

        # global variables

        self.currentFontName = None
        self.currentFont = None

        self.cachedFonts = {}
        self.previewStrings = {'pre':'', 'scaled':'', 'post':''}
        self.newLineGlyph = self.preview.createNewLineGlyph()

        self.observers = [
            ('_addAvailableFont','fontDidOpen'),
            ('_removeAvailableFont','fontWillClose'),
            ('_drawMetrics', 'spaceCenterDraw'),
        ]
        for method, event in self.observers:
            addObserver(self, method, event)

        self._selectedFontChanged(self.controlsBox.selectedFont)
        self._updatePreview()

        self.w.bind('close', self._killObservers)
        self.w.open()




    """ Shortcuts to vanilla objects """

    @property
    def preview(self):
        return self.glyphPreviewBox.preview


    @property
    def controls(self):
        return self.controlsBox.settings


    @property
    def masterFontsList(self):
        return self.controlsBox.masterFonts




    """ MultiLineView settings and alterations """

    def _pointSize(self, sender):
        value = sender.get()
        try: value = float(value)
        except: value = 72
        self.preview.setPointSize(value)
        self.preview.setLineHeight(value*1.5)




    """ MutatorScaleEngine settings """

    @property
    def isotropic(self):
        return self.controls.stemBox.isotropic.get()


    @isotropic.setter
    def isotropic(self, value):
        self.controls.stemBox.isotropic.set(value)



    """ UI building """

    def _buildGenerationSheet(self, sender):
        self.sheet = Sheet((500, 400), self.w)
        self.sheet.title = TextBox((10, 10, -10, 22), 'Generate'.upper(), alignment='center')
        self.sheet.title.getNSTextField().setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.5, 0.5, 1))
        self.sheet.inner = Box((10, 37, -10, -10))
        self.sheet.inner.destinationFontTitle = TextBox((10, 13, 130, 22), 'Destination font')
        self.sheet.inner.destinationFont = PopUpButton((140, 13, -10, 22), ['New font'] + self.availableFonts.keys())
        self.sheet.inner.options = Tabs((5, 52, -5, -37), ['Current', 'Batch'])

        current = self.sheet.inner.options[0]
        batch = self.sheet.inner.options[1]

        current.glyphsetTitle = TextBox((10, 10, 100, 22), 'Glyphset')
        current.glyphset = ComboBox((110, 10, -10, 22), ['','All glyphs'])

        current.suffixTitle = TextBox((10, 42, 100, 22), 'Suffix')
        current.suffix = EditText((110, 42, -10, 22))

        batch.list = List((10, 10, -10, -32),
            self.batchGenerationList,
            columnDescriptions=[
                {'title': self.includedGlyph, 'cell': CheckBoxListCell(), 'width': 20},
                {'title': 'preset', 'editable': True, 'width': 140},
                {'title': 'glyphset', 'editable': True, 'width': 180},
                {'title': 'suffix', 'editable': True, 'width': 80},
            ],
            editCallback=self._editBatchGenerationLine,
            allowsMultipleSelection=False)
        batch.addLine = Button((10, -22, 50, 22), 'Add', sizeStyle='small', callback=self._addBatchGenerationLine)
        batch.removeLine = Button((65, -22, 60, 22), 'Remove', sizeStyle='small', callback=self._removeBatchGenerationLine)

        self.sheet.inner.generate = Button((-125, -27, 120, 22), 'Generate', callback=self._generationCallback)
        self.sheet.inner.cancel = Button((-215, -27, 80, 22), 'Cancel', callback=self._closeGenerationSheet)
        self.sheet.open()


    def _closeGenerationSheet(self, sender=None):
        self.sheet.close()


    """ Interface Callbacks """

    def _editBatchGenerationLine(self, sender):
        self.batchGenerationList = [dict(**item) for item in sender.get()]
        self._saveBatchGenerationList()

    def _addBatchGenerationLine(self, sender):
        batchList = self.sheet.inner.options[1].list
        newLine = {
            self.includedGlyph: False,
            'preset': 'Preset name',
            'glyphset': '',
            'suffix': ''
        }
        self.batchGenerationList.append(newLine)
        self.sheet.inner.options[1].list.set(self.batchGenerationList)
        self._saveBatchGenerationList()


    def _removeBatchGenerationLine(self, sender):
        batchList = self.sheet.inner.options[1].list
        selection = batchList.getSelection()
        if len(selection):
            index = selection[0]
            self.batchGenerationList.pop(index)
            self.sheet.inner.options[1].list.set(self.batchGenerationList)
            self._saveBatchGenerationList()


    def _generationCallback(self, sender):
        destinationFontName = extractSelectedItem(self.sheet.inner.destinationFont)
        selectedTabIndex = self.sheet.inner.options.get()
        newFont = not destinationFontName in self.availableFonts
        initialSettings = self._getCurrentSettings()

        font = self.availableFonts[destinationFontName]['font'] if not newFont else RFont(showUI=False)

        self.sheet.progress = ProgressBar((15, 11, 190, 16), isIndeterminate=True)
        self.sheet.progress.start()

        if newFont:
            self._copyFontProperties(font, self.currentFont, extensive=True)

        if selectedTabIndex == 0:
            rawGlyphNames = self.sheet.inner.options[0].glyphset.get()
            if rawGlyphNames == 'All glyphs' and self.currentFont is not None:
                glyphset = self.currentFont.keys()
            else:
                glyphset = self._stringToGlyphNames(rawGlyphNames)

            suffix = self.sheet.inner.options[0].suffix.get()
            font = self.generateGlyphsToFont(font, glyphset, initialSettings, suffix)

        elif selectedTabIndex == 1:
            batchGenerationList = self.batchGenerationList

            for generationItem in batchGenerationList:
                presetName = generationItem['preset']
                presetsKeys = [preset.name for preset in self.presets]
                if presetName in presetsKeys and generationItem[self.includedGlyph] == True:
                    preset = self.presets[presetsKeys.index(presetName)]
                    self._applySettingsWithUI(preset.settings)
                    settings = self._getCurrentSettings()
                    rawGlyphNames = generationItem['glyphset']
                    glyphset = self._stringToGlyphNames(rawGlyphNames)
                    suffix = generationItem['suffix']
                    font = self.generateGlyphsToFont(font, glyphset, settings, suffix)

        if newFont:
            font.showUI()
        font.update()

        self._applySettingsWithUI(initialSettings)

        self.sheet.progress.stop()
        self._closeGenerationSheet()


    def _setScalingGoals(self):
        self.scalingMasters.set(self.scalingGoals)
        self._updatePreview(True)


    def _setReferenceHeight(self, sender):
        referenceHeight = sender.get()
        isNumber = parsesToNumber(referenceHeight)
        if referenceHeight in self.heightReferences or isNumber:
            if isNumber == True:
                referenceHeight = int(round(float(referenceHeight)))
            self.scalingGoals['referenceHeight'] = referenceHeight
        else:
            sender.set('capHeight')
        self._setScalingGoals()


    def _setTargetHeight(self, sender):
        targetHeight = sender.get()

        if self.currentFont is not None:

            referenceHeight = self.scalingGoals['referenceHeight']
            if referenceHeight in self.heightReferences:
                height_referenceValue = getattr(self.currentFont.info, referenceHeight)
            else:
                try:
                    height_referenceValue = float(referenceHeight)
                except:
                    height_referenceValue = 1

            height_targetValue = None

            if isinstance(sender, Slider):
                height_targetValue = height_referenceValue * float(targetHeight)
                self.controls.verticalScaleBox.targetHeightInput.set(int(round(height_targetValue)))

            elif isinstance(sender, EditText) and len(targetHeight):
                try:
                    height_targetValue = float(targetHeight)
                    ratio = height_targetValue / height_referenceValue
                    self.controls.verticalScaleBox.targetHeightSlider.set(ratio)
                except:
                    pass

            if height_targetValue is not None:
                self.scalingGoals['targetHeight'] = height_targetValue

        self._setScalingGoals()


    def _setWidth(self, sender):
        width = sender.get()

        if self.currentFont is not None:

            if isinstance(sender, Slider):
                self.controls.horizontalScaleBox.widthInput.set(round(width*100, 1))

            elif isinstance(sender, EditText):
                try:
                    width = float(width)
                    width /= 100
                except:
                    width = 1
                self.controls.horizontalScaleBox.widthSlider.set(width)

            self.scalingGoals['width'] = width

            self._setScalingGoals()


    def _changePosition(self, sender):
        key = sender.key
        try:
            value = int(sender.get())
            self.transformations[key] = value
            self._updatePreview(True)
        except:
            pass


    def _changeStickyPos(self, sender):
        name = sender.name
        zone, alignment = self.transformations['stickyPos']
        if name == 'zone':
            control = self.controls.sticky.zone
            zone = control.get()
        elif name == 'alignment':
            control = self.controls.sticky.alignment
            alignment = control.get()

        if alignment in self.alignmentGuides:
            self.transformations['stickyPos'] = (zone, alignment)
            self._updatePreview(True)


    def _changeTracking(self, sender):
        trackingValue = sender.get()
        try:
            trackingValue = int(trackingValue)
        except:
            trackingValue = 0
        _, trackingUnits = self.transformations['tracking']
        self.transformations['tracking'] = (trackingValue, trackingUnits)
        self._updatePreview(True)


    def _changeTrackingUnits(self, sender):
        trackingUnits = extractSelectedItem(sender)
        trackingValue, _ = self.transformations['tracking']
        self.transformations['tracking'] = (trackingValue, trackingUnits)
        self._updatePreview(True)


    def _keepSidebearings(self, sender):
        value = sender.get()
        self.transformations['keepSidebearings'] = value
        self._updatePreview(True)


    def _switchIsotropicCallback(self, sender):
        value = not bool(sender.get())
        self._switchIsotropic(value)


    def _switchIsotropic(self, value):
        self.controls.stemBox.hstem.enable(value)
        self._updatePreview(True)


    def _switchParameterModeCallback(self, sender):
        index = sender.get()
        parameterMode = ['offset','ratio','absolute'][index]
        self._switchParameterMode_(parameterMode)


    def _switchParameterMode_(self, parameterMode):
        for key in ['vstem','hstem']:
            parameter = self.definedStems[key]
            masterParameter = self.currentStems[key]
            control = getattr(self.controls.stemBox, key)
            if parameterMode in ['offset','ratio']:
                parameter.setFree(False)
                parameter.setMode(parameterMode)
                control.showRelativeValue(True)
            elif parameterMode == 'absolute':
                parameter.setFree(True)
                control.showRelativeValue(False)


    def _inputGlyphs(self, sender):
        inputString = sender.get()
        name = sender.name
        self.previewStrings[name] = inputString
        self._updatePreview()


    def _stemsUpdated(self, sender):
        self._updatePreview(True)


    """ Generation """

    def generateGlyphsToFont(self, font, glyphset, settings, suffix):
        self._applyScalingSettings(settings)
        font = self._buildScaledGlyphs(font, glyphset, suffix)
        return font


    def _getBatchGenerationList(self):
        if (self.currentFont is not None) and ('com.loicsander.scaleFast' in self.currentFont.lib) and ('batchGenerationList' in self.currentFont.lib['com.loicsander.scaleFast']):
            return self.currentFont.lib['com.loicsander.scaleFast']['batchGenerationList']
        return []


    def _saveBatchGenerationList(self):
        if self.currentFont is not None and 'com.loicsander.scaleFast' in self.currentFont.lib:
            self.currentFont.lib['com.loicsander.scaleFast']['batchGenerationList'] = self.batchGenerationList



    """ Glyph scaling """

    def _buildScaledGlyphs(self, font, glyphNames, suffix=None, useCachedGlyphs=False):

        if self.isotropic == True and self.scalingMasters.hasTwoAxes() == False:
            stems = self.definedStems['vstem'].get()
        else:
            stems = tuple([self.definedStems['vstem'].get(), self.definedStems['hstem'].get()])

        self.trackingOffsets = {}

        for name in glyphNames:

            if (useCachedGlyphs) == False or (name not in font and useCachedGlyphs == True):
                font = self._retrieveScaledGlyph(font, name, stems, suffix)

        return font


    def _retrieveScaledGlyph(self, font, glyphName, stems, suffix=None):

        scaledGlyph = self.scalingMasters.getScaledGlyph(glyphName, stems)

        if scaledGlyph is not None:

            outputGlyphName = glyphName

            if suffix:
                outputGlyphName = '{0}{1}'.format(glyphName, suffix)
            font.insertGlyph(scaledGlyph, outputGlyphName)

            scaledGlyph = font[outputGlyphName]

            if len(scaledGlyph.components):
                for component in scaledGlyph.components:
                    baseGlyphName = component.baseGlyph

                    if baseGlyphName not in font:
                        font = self._retrieveScaledGlyph(font, baseGlyphName, stems, suffix)

            # neutralizing the scaling of sidebearings
            if (self.transformations['keepSidebearings'] == True) and (self.currentFont is not None):
                sourceGlyph = self.currentFont[glyphName]
                scaledGlyph.angledLeftMargin = sourceGlyph.angledLeftMargin
                scaledGlyph.angledRightMargin = sourceGlyph.angledRightMargin

            scaledGlyph = self._transformGlyph(scaledGlyph, self.transformations, font.info.italicAngle if font.info.italicAngle is not None else 0)

        return font


    def _transformGlyph(self, glyph, transformations, angle=0):

        # tracking
        trackingValue, trackingUnits = transformations['tracking']
        if trackingUnits == 'upm':
            for items in ['contours', 'anchors','components']:
                if items in ['contours', 'anchors'] or (items == 'components' and transformations['keepSidebearings'] == True):
                    for item in getattr(glyph, items):
                        item.move((trackingValue, 0))
            glyph.width += (trackingValue * 2)

        elif trackingUnits == '%':
            leftMargin = round(glyph.angledLeftMargin)
            glyph.angledLeftMargin = round(glyph.angledLeftMargin) * (1 + (trackingValue / 100))
            glyph.angledRightMargin = round(glyph.angledRightMargin) * (1 + (trackingValue / 100))
            delta = glyph.angledLeftMargin - leftMargin
            # if self.transformations['keepSidebearings'] == False:
            for component in glyph.components:
                component.move((-delta, 0))

        yDelta = 0
        xDelta = 0

        # sticky position
        stickyPos = transformations['stickyPos']
        if stickyPos != ('bottom','baseline'):
            zone, alignment = stickyPos
            targetHeight = self.scalingGoals['targetHeight']

            if targetHeight in self.heightReferences and self.currentFont is not None:
                targetHeight = getattr(self.currentFont.info, targetHeight)
            elif targetHeight == 'baseline':
                targetHeight = 0

            referenceHeights = self._getReferenceHeights()
            try:
                guides = self.currentFont.lib['com.loicsander.scaleFast']['guides']
            except:
                guides = []
            guideNames = [guide['Name'] for guide in guides]

            if alignment in referenceHeights:
                alignmentHeight = referenceHeights[alignment]
            elif alignment in guideNames:
                index = guideNames.index(alignment)
                try:
                    alignmentHeight = guides[index]['Height']
                    alignmentHeight = int(alignmentHeight)
                except:
                    alignmentHeight = 0
            else:
                alignmentHeight = 0

            if zone == 'bottom':
                yDelta = alignmentHeight
            elif zone == 'top':
                yDelta = alignmentHeight - targetHeight
            elif zone == 'center':
                yDelta = alignmentHeight - (targetHeight / 2)


        # additional (x, y) offset
        posX, posY = transformations['posX'], transformations['posY']
        xDelta = round((yDelta + posY) * cos(radians(angle)+pi/2))

        posX += xDelta
        posY += yDelta

        if posX or posY:
            for contour in glyph.contours:
                contour.move((posX, posY))
            for anchor in glyph.anchors:
                anchor.move((posX, posY))

        return glyph




    """ Interactions """

    def _updateControls(self, mode):
        if mode == 'Two-axes':
            self.controls.stemBox.isotropic.show(False)
            self.controls.stemBox.vstem.enable(True)
            self.controls.stemBox.hstem.enable(True)

        elif self.scalingMasters.getCurrentStemBase() == 'vstem':
            self.controls.stemBox.isotropic.show(True)
            self.controls.stemBox.vstem.enable(True)
            if mode == 'Isotropic':
                self.controls.stemBox.hstem.enable(False)

        elif self.scalingMasters.getCurrentStemBase() == 'hstem':
            self.controls.stemBox.vstem.enable(False)
            self.controls.stemBox.hstem.enable(True)

        transformations = self.transformations

        controlsToPopulate = [
            (self.controls.verticalScaleBox.targetHeightInput, self.scalingGoals['targetHeight'], self.scalingGoals['referenceHeightValue']),
            (self.controls.horizontalScaleBox.widthInput, round(self.scalingGoals['width']*100, 1), None),
            (self.controls.horizontalScaleBox.widthSlider, self.scalingGoals['width'], 1),
        ]

        for control, normalValue, fallbackValue in controlsToPopulate:
            controlValue = control.get()
            if not controlValue:
                control.set(fallbackValue if fallbackValue is not None else normalValue)
            else:
                control.set(normalValue)


    def _selectedFontChanged(self, sender):
        """ Selected master(s) changed, change preview """
        selectedFontName = extractSelectedItem(sender)

        if (selectedFontName is not None) and (selectedFontName in self.availableFonts):
            self.currentFontName = selectedFontName
            self.currentFont = self.availableFonts[selectedFontName]['font']

            if selectedFontName in self.scalingMasters:
                vstem, hstem = self.scalingMasters[selectedFontName].getStems()
            else:
                vstem, hstem = getRefStems(self.currentFont)

            self.setCurrentStems(vstem, hstem)

            referenceHeight = self.scalingGoals['referenceHeight']
            if referenceHeight in ['capHeight','ascender','descender','xHeight','unitsPerEm']:
                self.scalingGoals['referenceHeightValue'] = getattr(self.currentFont.info, referenceHeight)

            targetHeight = self.scalingGoals['targetHeight']
            if targetHeight in ['capHeight','ascender','descender','xHeight','unitsPerEm']:
                self.scalingGoals['targetHeight'] = getattr(self.currentFont.info, targetHeight)

            if 'com.loicsander.scaleFast' not in self.currentFont.lib:
                self.currentFont.lib['com.loicsander.scaleFast'] = {}

            guides = self._collectVerticalGuides(self.currentFont)
            self.scaleFastSettings.g.verticalGuides.set(guides)
            self.alignmentGuides += [guide['Name'] for guide in guides]
            self.controls.sticky.alignment.setItems(self.alignmentGuides)

            self.batchGenerationList = self._getBatchGenerationList()
            self.presets = self._collectPresets(self.currentFont)
            self.scaleFastSettings.g.presets.g.presetsList.set([preset.name for preset in self.presets])
            self._savePresets()


        elif selectedFontName is None:
            self.currentFontName = None
            self.currentFont = None

        for fontName in self.availableFonts:
            selected = self.availableFonts[fontName]['selected']
            if selected == False and fontName in self.scalingMasters:
                font = self.availableFonts[fontName]['font']
                self.scalingMasters.removeMaster(font)

        self._updatePreview()


    def _editMasterFontsList(self, sender):
        """ Something was edited in the list:
        – update master status: included or not included
        – if stem values were modified and font is included among masters, update stem values
        """
        masterFontsItems = sender.get()
        availableFonts = self.availableFonts
        listValuesToChange = []

        # updating the scaler

        for i, listItem in enumerate(masterFontsItems):
            fontName = listItem['font']
            selected = listItem[self.includedGlyph]

            if selected == True and availableFonts[fontName]['selected'] == False:

                # if stem values are already extant, use them
                fontToAdd = availableFonts[fontName]['font']
                vstem = availableFonts[fontName]['vstem']
                hstem = availableFonts[fontName]['hstem']
                stems = (vstem, hstem)

                if stems != (None, None):
                    # initiate new MutatorScale master with existing stems
                    self.scalingMasters.addMaster(fontToAdd, stems)
                else:
                    # initiate new MutatorScale master, scaler will measure stem values
                    self.scalingMasters.addMaster(fontToAdd)

                # update stored stem values in available fonts in case they changed on master initiation (= were None and were calculated on master instantiation)
                for key in ['vstem','hstem']:
                    stemValue = getattr(self.scalingMasters[fontName], key)
                    if stemValue is None:
                        stemValue = 0
                    availableFonts[fontName][key] = stemValue
                    listValuesToChange.append((i, 'replace', (key, int(stemValue))))

                availableFonts[fontName]['selected'] = True

            elif selected == False and availableFonts[fontName]['selected'] == True:

                # remove MutatorScale master
                fontToRemove = availableFonts[fontName]['font']
                self.scalingMasters.removeMaster(fontToRemove)

                availableFonts[fontName]['selected'] = False

                if len(self.scalingMasters) == 0:
                    self.isotropic = True


            # editing the masters list

            for key in ['vstem', 'hstem']:

                # if a vstem or hstem value is present in the list
                if key in listItem:

                    value = None
                    previousValue = availableFonts[fontName][key]
                    strValue = listItem[key]

                    # try parsing it to a number value
                    try:
                        value = int(strValue)

                    # if this fails, try to revert to a previous value if there is one
                    # otherwise, remove the faulty value from the list
                    except:

                        if previousValue is not None:
                            listValuesToChange.append((i, 'replace', (key, previousValue)))

                        elif previousValue is None:
                            listValuesToChange.append((i, 'pop', key))

                    # eventually, if there is new valid value, store it for update
                    if value is not None:

                        availableFonts[fontName][key] = value

                        if fontName in self.scalingMasters:
                            setattr(self.scalingMasters[fontName], key, value)

        if len(listValuesToChange):

            for index, action, item in listValuesToChange:

                if action == 'replace':
                    key, value = item
                    self.masterFontsList[index][key] = value

                elif action == 'pop':
                    key = item
                    self.masterFontsList[index].pop(key, 0)

        self.scalingMasters.update()

        self.availableFonts = availableFonts
        self._updatePreview(True)


    def _addAvailableFont(self, notification):
        """ On notification, add font to the various font lists. """
        font = notification['font']
        name = makeListFontName(font)
        masterFontsItems = self.masterFontsList.get()

        if not self.availableFonts.has_key(name):
            self.availableFonts[name] = {'font':font, 'selected':False, 'vstem':None, 'hstem':None, 'familyName':font.info.familyName, 'styleName':font.info.styleName}
            newListItem = {
                self.includedGlyph:False,
                'font':name,
                'vstem': None,
                'hstem': None
                }
            masterFontsItems.append(newListItem)

        self.masterFontsList.set(masterFontsItems)


    def _removeAvailableFont(self, notification):
        """ On notification, remove font from the various font lists. """
        fontToRemove = notification['font']
        name = makeListFontName(fontToRemove)
        masterFontsItems = self.masterFontsList.get()

        # remove font from available fonts
        if self.availableFonts.has_key(name):
            selected = self.availableFonts[name]['selected']
            self.availableFonts.pop(name, 0)
            if selected == True:
                self.scalingMasters.removeMaster(fontToRemove)

        # remove corresponding master in the UI list
        for i in range(len(masterFontsItems)-1, -1, -1):
            listItem = masterFontsItems[i]
            if listItem['font'] == name:
                break

        # masterFontsList = self.masterFontsList.getNSTableView()
        # index = NSIndexSet.alloc().initWithIndex_(i)
        # masterFontsList.beginUpdates()
        # masterFontsList.removeRowsAtIndexes_withAnimation_(index, NSTableViewAnimationSlideLeft)
        # masterFontsList.endUpdates()

        masterFontsItems.pop(i)
        self.masterFontsList.set(masterFontsItems)




    """ Helpers """

    def _applyScalingSettings(self, settings):

        self.scalingGoals = {
            'width': settings['width'],
            'targetHeight': settings['targetHeight'],
            'referenceHeight': settings['referenceHeight'],
            'referenceHeightValue': getattr(self.currentFont.info, settings['referenceHeight']) if settings['referenceHeight'] in self.heightReferences and self.currentFont is not None else settings['targetHeight']
        }

        for key in self.transformations:
            self.transformations[key] = settings[key]

        self._setScalingGoals()


    def _stringToGlyphNames(self, string):
        if self.currentFont is not None:
            cmap = self._getCMap(self.currentFont)
            if cmap is not None:
                glyphLines = []
                lines = string.split('\\n')
                l = len(lines)
                for i, line in enumerate(lines):
                    glyphs = splitText(line, cmap)
                    if 0 < i < l:
                        glyphs.insert(0, 'newLine')
                    glyphLines += glyphs
                return glyphLines
        return []


    def _getReferenceHeights(self):
        heights = {}
        if self.currentFont is not None:
            for key in self.heightReferences:
                heights[key] = getattr(self.currentFont.info, key)
        return heights


    def _getCMap(self, sourceFont):
        return sourceFont.getCharacterMapping()


    def _copyFontProperties(self, font, fontToCopy, extensive=False):
        """ Copy some elements of font info from one font to another, for proper rendering in preview """

        for dimension in ['xHeight','capHeight','ascender','descender','italicAngle','unitsPerEm']:
            setattr(font.info, dimension, getattr(fontToCopy.info, dimension))

        if fontToCopy.lib.has_key('com.typemytype.robofont.italicSlantOffset'):
            font.lib['com.typemytype.robofont.italicSlantOffset'] = fontToCopy.lib['com.typemytype.robofont.italicSlantOffset']


    def setCurrentStems(self, vstem=None, hstem=None):
        if vstem is not None:
            self.currentStems['vstem'].set(vstem)
        if hstem is not None:
            self.currentStems['hstem'].set(hstem)



    """ Preview business """

    def _updatePreview(self, reset=False):

        if self.currentFont is not None:

            if reset == True:
                self.cachedFonts = {}

            currentFont = self.currentFont
            twoAxes = self.scalingMasters.hasTwoAxes()

            if twoAxes == True:
                mode = 'Two-axes'
            elif twoAxes == False:
                mode = 'Anisotropic' if self.isotropic == False else 'Isotropic'

            modeString = 'mode: %s' % (mode)
            self.glyphPreviewBox.mode.set(modeString)

            self._updateControls(mode)

            if self.currentFontName in self.cachedFonts:
                previewFont = self.cachedFonts[self.currentFontName]
            else:
                previewFont = RFont(showUI=False)
                self._copyFontProperties(previewFont, currentFont)

            glyphNames = {}

            for key in self.previewStrings:
                glyphNames[key] = self._stringToGlyphNames(self.previewStrings[key])

            previewFont = self._buildScaledGlyphs(previewFont, glyphNames['scaled'], useCachedGlyphs=True)

            glyphs = []

            for key, font in [('pre', currentFont), ('scaled', previewFont), ('post', currentFont)]:
                for name in glyphNames[key]:
                    g = None
                    if name == 'newLine':
                        g = self.newLineGlyph
                    elif name in font:
                        g = font[name]
                    if g is not None:
                        glyphs.append(g)

            self.preview.setFont(previewFont)
            self.preview.set(glyphs)

            self.cachedFonts[self.currentFontName] = previewFont


    def _drawMetrics(self, notification):
        sc = notification['scale']
        guides = self.scaleFastSettings.g.verticalGuides.get()
        color = self.guideColor
        save()
        fill()
        stroke(*color)
        strokeWidth(0.5*sc)

        if self.previewSettings['drawVerticalMetrics'] == True:

            for guide in guides:
                try:
                    h = int(guide['Height'])
                    line((-100000, h), (100000, h))
                except:
                    pass

        restore()


    def changeDisplayMode(self, sender):
        index = sender.get()
        mode = self.previewSettings['displayModes'][index]
        self.glyphPreviewBox.preview.setDisplayMode(mode)


    def changeDisplayStates(self, states):
        displayStates = self.glyphPreviewBox.preview.getDisplayStates()
        for key, value in states.items():
            displayStates[key] = value
        self.glyphPreviewBox.preview.setDisplayStates(displayStates)


    def showMetrics(self, sender):
        value = bool(sender.get())
        self.changeDisplayStates({'Show Metrics': value})


    def addAlignmentGuide(self, name):
        alignmentGuideNames = self.alignmentGuides
        alignmentGuideNames.append(name)
        selectedName = self.controls.sticky.alignment.get()
        self.controls.sticky.alignment.setItems(alignmentGuideNames)
        self.controls.sticky.alignment.set(selectedName)


    def removeAlignmentGuide(self, name):
        alignmentGuideNames = self.alignmentGuides
        alignmentGuideNames.remove(name)
        selectedName = self.controls.sticky.alignment.get()
        self.controls.sticky.alignment.setItems(alignmentGuideNames)
        if selectedName == name:
            self.controls.sticky.alignment.set('baseline')
        else:
            self.controls.sticky.alignment.set(selectedName)


    def renameAlignmentGuide(self, oldName, newName):
        alignmentGuideNames = self.alignmentGuides
        index = alignmentGuideNames.index(oldName)
        selectedName = self.controls.sticky.alignment.get()
        alignmentGuideNames[index] = newName
        self.controls.sticky.alignment.setItems(alignmentGuideNames)
        self.alignmentGuides = alignmentGuideNames
        if selectedName == oldName:
            self.controls.sticky.alignment.set(newName)
            zone, alignment = self.transformations['stickyPos']
            self.transformations['stickyPos'] = (zone, newName)
        else:
            self.controls.sticky.alignment.set(selectedName)


    def _collectVerticalGuides(self, font):
        guides = []
        if 'com.loicsander.scaleFast' in self.currentFont.lib and 'guides' in self.currentFont.lib['com.loicsander.scaleFast']:
            guides += self.currentFont.lib['com.loicsander.scaleFast']['guides']
        return guides


    def _addVerticalGuide(self, sender):
        guides = self.scaleFastSettings.g.verticalGuides.get()
        l = len(guides)
        newGuideName = 'New guide %s'%(l+1)
        guides.append({'Name': newGuideName, 'Height':0})
        self.addAlignmentGuide(newGuideName)
        self.scaleFastSettings.g.verticalGuides.set(guides)
        self._saveVerticalGuides()


    def _removeVerticalGuide(self, sender):
        guides = self.scaleFastSettings.g.verticalGuides.get()
        selection = self.scaleFastSettings.g.verticalGuides.getSelection()
        for i in reversed(selection):
            guideName = guides[i]['Name']
            self.removeAlignmentGuide(guideName)
            guides.pop(i)
        self.scaleFastSettings.g.verticalGuides.set(guides)
        self._saveVerticalGuides()
        self._updatePreview(True)


    def _editVerticalGuides(self, sender):
        newGuides = sender.get()
        if len(newGuides) + 5 == len(self.alignmentGuides):
            oldGuideNames = self.alignmentGuides[5:]

            for i, (newGuide, oldGuideName) in enumerate(zip(newGuides, oldGuideNames)):
                if newGuide['Name'] != oldGuideName:
                    self.renameAlignmentGuide(oldGuideName, newGuide['Name'])

            self._saveVerticalGuides()
        self._updatePreview(True)


    def _saveVerticalGuides(self):
        if self.currentFont is not None:
            guides = self.scaleFastSettings.g.verticalGuides.get()
            self.currentFont.lib['com.loicsander.scaleFast']['guides'] = guides


    def showVerticalGuides(self, sender):
        value = bool(sender.get())
        self.previewSettings['drawVerticalMetrics'] = value
        self._updatePreview()


    def getPresetsList(self, font):
        # if font is not None and font.lib.has_key('com.loicsander.scaleFast.presets'):
        #     return font.lib['com.loicsander.scaleFast.presets']
        # return []
        pass


    def _collectPresets(self, font):

        if self.currentFont is not None:
            presets = []
            old = False
            if 'com.loicsander.scaleFast.presets' in self.currentFont.lib:
                oldPresets = self.currentFont.lib['com.loicsander.scaleFast.presets']
                for name, settings in oldPresets:
                    preset = ScaleFastPreset((name, settings), True)
                    presets.append(preset)
                del self.currentFont.lib['com.loicsander.scaleFast.presets']

            if 'com.loicsander.scaleFast' in self.currentFont.lib:
                if 'presets' in self.currentFont.lib['com.loicsander.scaleFast']:
                    for name, settings in self.currentFont.lib['com.loicsander.scaleFast']['presets'].items():
                        preset = ScaleFastPreset((name, settings))
                        presets.append(preset)

            presets.sort(key=lambda a: a.name)

        return presets


    def _savePresets(self):
        if self.currentFont is not None:
            self.currentFont.lib['com.loicsander.scaleFast']['presets'] = {
                preset.name: preset.settings for preset in self.presets
            }


    def _editPresetNames(self, sender):
        presetNames = sender.get()
        renamedPresets = []
        for i, presetName in enumerate(presetNames):
            self.presets[i].setName(presetName)
        self._savePresets()


    def _updatePreset(self, sender):
        selection = self.scaleFastSettings.g.presets.g.presetsList.getSelection()
        if len(selection):
            index = selection[0]
            updatedSettings = self._getCurrentSettings()
            self.presets[index].set(updatedSettings)


    def updatePresetsList(self):
        presetNames = [preset.name for preset in self.presets]
        self.scaleFastSettings.g.presets.g.presetsList.set(presetNames)


    def _getCurrentSettings(self):
        settings = {
            'vstem': self.definedStems['vstem'].get(),
            'hstem': self.definedStems['hstem'].get(),
            'stemRapport': ['offset','ratio','absolute'][self.controls.stemBox.switch.get()],
            'referenceHeight': self.scalingGoals['referenceHeight'],
            'targetHeight': self.scalingGoals['targetHeight'],
            'width': self.scalingGoals['width'],
            'posX': self.transformations['posX'],
            'posY': self.transformations['posY'],
            'stickyPos': self.transformations['stickyPos'],
            'keepSidebearings': self.transformations['keepSidebearings'],
            'tracking': self.transformations['tracking'],
            'isotropic': self.isotropic
        }
        return settings


    def _addPreset(self, sender):
        presetName = 'Preset %s' % (len(self.presets)+1)
        settings = self._getCurrentSettings()
        newPreset = ScaleFastPreset((presetName, settings))
        self.presets.append(newPreset)
        self.updatePresetsList()
        self._savePresets()


    def _removePreset(self, sender):
        selection = self.scaleFastSettings.g.presets.g.presetsList.getSelection()
        if len(selection):
            index = selection[0]
            self.presets.pop(index)
            self.updatePresetsList()
            self._savePresets()


    def _applyPresetCallback(self, sender):
        selection = self.scaleFastSettings.g.presets.g.presetsList.getSelection()
        if len(selection):
            selectedPreset = self.presets[selection[0]]
            self._applySettingsWithUI(selectedPreset.settings)


    def _applySettingsWithUI(self, settings):
        self._applyScalingSettings(settings)

        controlsToPopulate = [
            (self.controls.verticalScaleBox.referenceHeight, self.scalingGoals['referenceHeight']),
            (self.controls.stemBox.switch, ['offset','ratio','absolute'].index(settings['stemRapport'])),
            (self.controls.stemBox.vstem, settings['vstem']),
            (self.controls.stemBox.hstem, settings['hstem']),
            (self.controls.stemBox.isotropic, settings['isotropic']),
            (self.controls.tracking.input, settings['tracking'][0]),
            (self.controls.tracking.units, ['upm','%'].index(settings['tracking'][1])),
            (self.controls.posShift.xShift, settings['posX']),
            (self.controls.posShift.yShift, settings['posY']),
            (self.controls.sticky.zone, settings['stickyPos'][0],),
            (self.controls.sticky.alignment, settings['stickyPos'][1]),
            (self.controls.tracking.dontScaleSpacing, settings['keepSidebearings']),
        ]

        self.controls.stemBox.hstem.enable(not settings['isotropic'])

        for control, value in controlsToPopulate:
            control.set(value)


    def humanReadableInputValue(self, value):
        if value is None:
            return 'None'
        elif isinstance(value, (tuple, list)):
            """ Tracking with units (upm or percentage) """
            if value[1] in ['%', u'%']:
                v, u = value
                return '%s%s' % (v*100, u)
            else:return str(int(value[0]))
        elif isinstance(value, bool):
            return value
        elif isinstance(value, float):
            """ Scale to percentage """
            return '%s%s' % (value*100, u'%')
        else:
            return str(value)


    def _killObservers(self, notification=None):
        """ Kill all observers. """
        for method, event in self.observers:
            removeObserver(self, event)



ScaleFastController()