#coding=utf-8

# script for Robofont
# written by Loïc Sander
# february 2015

DGBVersion = '0.5.1'

from math import tan, radians
from mojo.events import addObserver, removeObserver
from mojo.UI import MultiLineView
from defconAppKit.tools.textSplitter import splitText
from vanilla import *
from copy import deepcopy

def listFontNames(fontList):
    fontNames = []
    unnamedCounter = 0
    for font in fontList:
        familyName, styleName = fontName(font)
        if familyName == 'Unnamed Font':
            familyName += ' %s' % unnamedCounter
            unnamedCounter += 1
        name = ' > '.join((familyName, styleName))
        fontNames.append(name)
    return fontNames

def fontName(font):
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None: font.info.familyName = familyName = 'Unnamed Font'
    if styleName is None: font.info.styleName = styleName = 'Unnamed style'
    return familyName, styleName

class GlyphDefinition:

    alterations = {
        'asComponent': True,
        'rotationPoint': ('center', 'center'),
        'flip': (1, 1),
        'offset': (0, 0),
        'xAlign': False,
        'yAlign': False,
        'width': True
    }

    def __init__(self, glyphName, baseGlyphRecords={}):
        self.name = glyphName
        self.baseGlyphs = []
        self.baseGlyphRecords = {}
        for baseGlyphName, alterations in baseGlyphRecords.items():
            baseAlterations = deepcopy(self.alterations)
            for key in alterations:
                baseAlterations[key] = alterations[key]
            self.addBaseGlyphRecord(baseGlyphName, baseAlterations)

    def __repr__(self):
        return '<GlyphDefinition: %s [%s]' % (self.name, ', '.join(self.baseGlyphs))

    def __getitem__(self, key):
        if isinstance(key, int):
            if key == 0:
                return self.name
            elif key == 1:
                return self.baseGlyphs
            elif key == 2:
                return self.baseGlyphRecords
            else: raise IndexError
        elif isinstance(key, str):
            if key == 'glyphName':
                return self.name
            elif key in ['alterations','baseGlyphRecords']:
                return self.baseGlyphRecords
            elif key in ['name','baseGlyphs']:
                return getattr(self, key)
            else: raise KeyError

    def setGlyphName(self, glyphName):
        if isinstance(glyphName, (str, unicode)):
            self.name = glyphName
        else: raise TypeError

    def addBaseGlyphRecord(self, baseGlyphName, alterations=None):
        if alterations is None: alterations = deepcopy(self.alterations)

        if not len(self.baseGlyphs):
            alterations['leftMargin'] = True
        alterations['rightMargin'] = True

        if baseGlyphName not in self.baseGlyphs:
            self.baseGlyphs.append(baseGlyphName)
            self.baseGlyphRecords[baseGlyphName] = alterations

    def updateBaseGlyphsList(self, baseGlyphsList):
        currentBaseGlyphList = self.baseGlyphs

        baseGlyphsToRemove = list(set(currentBaseGlyphList) - set(baseGlyphsList))
        baseGlyphsToAdd = list(set(baseGlyphsList) - set(currentBaseGlyphList))

        baseGlyphsToRemove.reverse()

        for baseGlyphName in baseGlyphsToRemove:
            self.removeBaseGlyphRecord(baseGlyphName)

        for baseGlyphName in baseGlyphsToAdd:
            self.addBaseGlyphRecord(baseGlyphName)

        self.baseGlyphs = baseGlyphsList

    def setBaseGlyphRecord(self, baseGlyphName, alterations=None):
        if baseGlyphName in self.baseGlyphs:
            for key, value in alterations.items():
                self.baseGlyphRecords[baseGlyphName][key] = value
        else: raise KeyError(baseGlyphName)

    def removeBaseGlyphRecord(self, baseGlyphName):
        if baseGlyphName in self.baseGlyphs:
            self.baseGlyphs.remove(baseGlyphName)
            self.baseGlyphRecords.pop(baseGlyphName, 0)
        else: raise KeyError(baseGlyphName)

    def getBaseGlyphRecord(self, baseGlyphName):
        if baseGlyphName in self.baseGlyphs:
            return self.baseGlyphRecords[baseGlyphName]
        else: raise KeyError(baseGlyphName)

class DerivativeGlyphsBuilder:

    def __init__(self, ):
        self.obfuscated = False
        self.events = [
            ('updateFontList','fontDidOpen'),
            ('updateFontList','fontDidClose')
        ]
        self.builtGlyphs = {}
        self.copiedDefinitions = None
        self.fonts = fonts = AllFonts()
        self.controlGlyph = 'H'

        if not len(fonts):
            print '## Derivative Glyph Builder ##\nNo open fonts.'
            return

        f = fonts[0]
        self.collectFontData(f)

        m = 20
        self.w = FloatingWindow((700, 700), 'Derivative Glyphs Builder %s' % (DGBVersion), minSize=(600, 700))
        self.w.inner = Group((m, m, -m, -15))
#        self.w.inner.fontName = TextBox((0, 0, -0, 20), '%s %s' % (f.info.familyName.upper(), f.info.styleName.upper()))
        self.w.inner.fonts = PopUpButton((0, 0, -250, 20), listFontNames(fonts), callback=self.changeCurrentFont)
        self.w.inner.derivatives = List((0, 35, -360, 330),
            self.buildDerivativesUIList(self.derivatives),
            selectionCallback=self.selectDerivativeGlyph,
            editCallback=self.editDerivativeGlyphNames,
            columnDescriptions=[{'title':'Derivative Glyph', 'width':130}, {'title':'Base Glyphs'}])

        self.w.inner.addDefinition = SquareButton((0, 365, -500, 20), 'Add', callback=self.addDefinition, sizeStyle='small')
        self.w.inner.removeDefinition = SquareButton((-500, 365, 140, 20), 'Remove', callback=self.removeDefinition, sizeStyle='small')
        self.w.inner.definition = Box((-340, 35, -0, 350))
        m = 15
        self.w.inner.definition.inner = Group((m, m, -m, 0))

        self.w.inner.previewTop = HorizontalLine((0, 399, -0, 1))
        self.w.inner.preview = MultiLineView((0, 400, -0, -40), hasHorizontalScroller=True, hasVerticalScroller=False)
        self.w.inner.previewBottom = HorizontalLine((0, -40, -0, 1))
        self.w.inner.preview.setDisplayMode('Single Line')
        displayStates = self.w.inner.preview.getDisplayStates()
        displayStates['Show Metrics'] = True
        self.w.inner.preview.setDisplayStates(displayStates)
        self.w.inner.preview.setCanSelect(True)

        self.w.inner.preview._glyphLineView._italicAngle = self.tempFont.info.italicAngle
        self.w.inner.preview._glyphLineView._italicSlantOffset = self.tempFont.lib['com.typemytype.robofont.italicSlantOffset']

        self.w.inner.controlGlyphTitle = TextBox((0, -18, 80, 14), 'Control glyph', sizeStyle='small')
        self.w.inner.controlGlyph = EditText((80, -22, 90, 22), text='H', callback=self.changeControlGlyph, continuous=False)

        self.w.inner.buildSelectedGlyphs = Button((-200, -22, 200, 20), 'Build selected glyphs', callback=self.buildSelectedGlyphs)

        self.w.inner.copySelectedDefinitions = Button((-230, 0, 120, 20), 'Copy', callback=self.copySelectedDefinitions)
        self.w.inner.pasteDefinitions = Button((-100, 0, 100, 20), 'Paste', callback=self.pasteDefinitions)
        self.w.inner.pasteDefinitions.enable(False)

        self.buildDefinitionSheet()

        for callback, event in self.events:
            addObserver(self, callback, event)

        self.w.bind('close', self.endOperations)
        self.w.open()

    def updateFontList(self, notification):
        fonts = AllFonts()
        fontNamesList = listFontNames(fonts)
        self.w.inner.fonts.setItems(fontNamesList)
        if len(fonts):
            self.collectFontData(fonts[0])
            self.updateDefinitionsList()

    def collectFontData(self, font):

        italicAngle = font.info.italicAngle
        italicSlantOffset = font.lib['com.typemytype.robofont.italicSlantOffset']

        if italicAngle is None: italicAngle = 0
        if italicSlantOffset is None: italicSlantOffset = 0

        self.tempFont = RFont(showUI=False)

        self.tempFont.info.italicAngle = italicAngle
        self.tempFont.lib['com.typemytype.robofont.italicSlantOffset'] = italicSlantOffset

        self.glyphOrder = font.lib['public.glyphOrder']
        self.availableGlyphs = font.keys()
        self.cmap = font.getCharacterMapping()
        self.currentFont = font
        self.heights = self.collectFontHeights()
        self.derivatives = self.getGlyphDefinitions()

        for height in self.heights:
            setattr(self.tempFont.info, height, self.heights[height])

        self.baseGlyphsList = [derivative['baseGlyphs'] for derivative in self.derivatives]
        self.derivedGlyphs = [derivative['glyphName'] for derivative in self.derivatives]

        if hasattr(self, 'w'):
            self.w.inner.preview._glyphLineView._italicAngle = self.tempFont.info.italicAngle
            self.w.inner.preview._glyphLineView._italicSlantOffset = self.tempFont.lib['com.typemytype.robofont.italicSlantOffset']

        self.updateTempFont()

    def collectFontHeights(self):
        font = self.currentFont
        heights = {heightName: getattr(font.info, heightName) for heightName in ['ascender','capHeight','xHeight','descender']}
        heights['baseline'] = 0
        for h in ['capHeight','xHeight','ascender','descender']:
            heights['mid%s'%(h.capitalize())] = heights[h] / 2
        if font.lib.has_key('com.loicsander.additionalVerticalMetrics'):
            additionalFontHeights = font.lib['com.loicsander.additionalVerticalMetrics']
            if hasattr(additionalFontHeights, 'heights'):
                additionalHeights = additionalFontHeights.heights
                for key in additionalHeights:
                    heights[key] = additionalHeights[key]
        return heights

    def changeCurrentFont(self, sender):
        fontList = sender.getItems()
        index = sender.get()
        selectedFontName = fontList[index]
        selectedFont = AllFonts().getFontsByFamilyNameStyleName(*selectedFontName.split(' > '))
        if selectedFont is None:
            print '## Derivative Glyph Builder ##\nNo open fonts.'
            return
        self.collectFontData(selectedFont)
        self.updateDefinitionsList()

    def changeControlGlyph(self, sender):
        textInput = sender.get()
        glyphNames = splitText(textInput, self.cmap)
        if len(glyphNames):
            self.controlGlyph = glyphNames[0]
        elif not len(glyphNames):
            self.controlGlyph = 'H'
        self.updatePreview()

    def addDefinition(self, sender):
        key = self.updateDefinitionSheet()
        self.derivatives.append(GlyphDefinition(key))
        self.baseGlyphsList.append([])
        self.derivedGlyphs.append(key)
        self.updateDefinitionsList()

    def removeDefinition(self, sender):
        selection = self.w.inner.derivatives.getSelection()
        if len(selection):
            for index in reversed(selection):
                for glyphList in [self.derivatives, self.baseGlyphsList, self.derivedGlyphs]:
                    glyphList.pop(index)
        self.updateDefinitionsList()

    def updateDefinition(self, sender):
        index, definition = self.getCurrentDefinition()

        if definition is not None:

            baseGlyphsList = self.w.inner.definition.inner.baseGlyph.getItems()
            selectedBaseGlyph = self.w.inner.definition.inner.baseGlyph.get()
            baseGlyphName = baseGlyphsList[selectedBaseGlyph]

            alterations = {
                'asComponent':True,
                'flip': (1, 1),
                'offset': (0, 0),
                'xAlign': False,
                'yAlign': False,
                'width': True
            }
            for item in ['asComponent', 'flip', 'offset', 'xAlign','yAlign','width']:
                alterations[item] = self.definitionInputFields[item]()

            definition.setBaseGlyphRecord(baseGlyphName, alterations)

            self.derivatives[index] = definition
            self.storeGlyphDefinitions(self.derivatives)

            self.updateTempFont()
            self.updatePreview()

    def getCurrentDefinition(self):
        selection = self.w.inner.derivatives.getSelection()
        if len(selection) == 1:
            index = selection[0]
            definition = self.derivatives[index]
            return index, definition
        return 0, None

    def editDerivativeGlyphNames(self, sender):
        glyphNamesList = sender.get()
        selection = sender.getSelection()
        derivativesList = self.derivatives
        for i, line in enumerate(glyphNamesList):
            glyphDefinition = derivativesList[i]
            glyphName = line['Derivative Glyph']
            baseGlyphsList = [name.replace(' ','') for name in line['Base Glyphs'].split(',')]
            if glyphName in baseGlyphsList:
                return
            glyphDefinition.setGlyphName(glyphName)
            glyphDefinition.updateBaseGlyphsList(baseGlyphsList)
            self.derivedGlyphs[i] = glyphName
            self.baseGlyphsList[i] = baseGlyphsList
            if (len(selection) == 1 and i in selection) or (len(selection) == 0 and i == 0):
                self.updateDefinitionSheet(glyphName=glyphName, definition=glyphDefinition)
        self.derivatives = derivativesList
        self.storeGlyphDefinitions(self.derivatives)
        self.updatePreview()

    def selectDerivativeGlyph(self, sender):
        selection = sender.getSelection()
        self.updateTempFont(selection)
        if len(selection) == 1:
            index = selection[0]
            glyphDefinition = self.derivatives[index]
            self.updateDefinitionSheet(glyphName=glyphDefinition['glyphName'], definition=glyphDefinition)
        elif len(selection) > 1:
            self.obfuscated = True
            self.obfuscateDefinitionSheet()
        self.updatePreview()

    def updateTempFont(self, indices=None):
        derivatives = self.derivatives
        for i, definition in enumerate(derivatives):
            if (indices is None) or (indices is not None and i in indices):
                self.makeGlyph(definition, self.tempFont)

    def updateDefinitionsList(self):
        derivativesList = self.buildDerivativesUIList(self.derivatives)
        self.w.inner.derivatives.set(derivativesList)

    def obfuscateDefinitionSheet(self):
        self.w.inner.definition.inner.show(False)
        self.w.inner.definition.warning.show(True)

    def updateDefinitionSheet(self, glyphName=None, definition=None, selectedBaseGlyph=0):

        validationStatus = u'✖'
        baseGlyphs = []

        if glyphName is None:
            derivativeGlyphNames = [_definition_['glyphName'] for _definition_ in self.derivatives]
            n = len([name for name in derivativeGlyphNames if 'Undefined glyph' in name])
            glyphName = '%s %s' % ('Undefined glyph', n)

        definitionDict = {
            'asComponent': True,
            'flip': (1, 1),
            'offset': (0, 0),
            'xAlign': False,
            'yAlign': False,
            'width': True
        }

        if definition is not None and len(definition['baseGlyphs']):
            baseGlyphs = definition['baseGlyphs']
            baseGlyphName = baseGlyphs[selectedBaseGlyph]
            definitionDict['baseGlyphName'] = baseGlyphName
            baseGlyphRecord = definition.getBaseGlyphRecord(baseGlyphName)
            for key in baseGlyphRecord:
                definitionDict[key] = baseGlyphRecord[key]

            isValid = self.validateGlyphDefinition(definition)
            if isValid: validationStatus = u'✔'

        if self.obfuscated:
           self.w.inner.definition.inner.show(True)
           self.w.inner.definition.warning.show(False)

        self.w.inner.definition.inner.title.set(u'%s %s' % (validationStatus, glyphName))
        self.w.inner.definition.inner.baseGlyph.setItems(baseGlyphs)
        if len(baseGlyphs):
            self.w.inner.definition.inner.baseGlyph.set(selectedBaseGlyph)
        self.w.inner.definition.inner.asComponent.set(int(definitionDict['asComponent']))

        hFlip, vFlip = definitionDict['flip']
        self.w.inner.definition.inner.flipHorizontal.set(int(((hFlip*-1)+1)/2))
        self.w.inner.definition.inner.flipVertical.set(int(((vFlip*-1)+1)/2))

        self.w.inner.definition.inner.flipHorizontal.enable(not definitionDict['asComponent'])
        self.w.inner.definition.inner.flipVertical.enable(not definitionDict['asComponent'])

        for axis in ['x','y']:
            positionAlign = getattr(self.w.inner.definition.inner, 'positionAlign%s' % (axis.upper()))
            key = '%sAlign' % (axis)
            if definitionDict[key] == False:
                positionAlign.alignTo.set(0)
                positionAlign.reference.set('')
                positionAlign.title.set(False)
                self.activateAlignment(False, axis.upper())
            else:
                positionAlign.title.set(True)
                index = positionAlign.alignTo.getItems().index(definitionDict[key][0])
                positionAlign.alignTo.set(index)
                positionAlign.reference.set(definitionDict[key][1])
                self.activateAlignment(True, axis.upper())

        self.w.inner.definition.inner.contributeWidth.set(definitionDict['width'])

        self.w.inner.definition.inner.positionOffset.x.set(str(definitionDict['offset'][0]))
        self.w.inner.definition.inner.positionOffset.y.set(str(definitionDict['offset'][1]))

        return glyphName

    def buildDefinitionSheet(self):

        definitionInputFields = {}

        self.w.inner.definition.inner.title = TextBox((0, 2, 150, 17), u'○ Undefined')
        self.w.inner.definition.inner.baseGlyph = PopUpButton((160, 0, -0, 20), [], callback=self.switchBaseGlyph, sizeStyle='small')
        self.w.inner.definition.warning = TextBox((15, 15, -15, -15), 'Cannot edit multiple definitions at once.')
        self.w.inner.definition.warning.show(False)

        ypos = 35
        self.w.inner.definition.inner.h1 = HorizontalLine((0, ypos, -0, 1))

        ypos += 11
        self.w.inner.definition.inner.asComponent = RadioGroup((0, ypos, -0, 17), ['Contour','Component'], isVertical=False, callback=self.updateDefinition)
        ypos += 28
        self.w.inner.definition.inner.h2 = HorizontalLine((0, ypos, -0, 1))

        definitionInputFields['asComponent'] = self.getCopyMode

        ypos += 11

        # Flipping
        self.w.inner.definition.inner.flipIcon = TextBox((0, ypos, 10, 17), u'◧')
        self.w.inner.definition.inner.flipTitle = TextBox((15, ypos, 70, 17), u'Flip')

        ypos += 27

        self.w.inner.definition.inner.flipHorizontal = CheckBox((0, ypos, 150, 17), 'Horizontally', callback=self.updateDefinition)
        self.w.inner.definition.inner.flipVertical = CheckBox((150, ypos, 150, 17), 'Vertically', callback=self.updateDefinition)

        self.w.inner.definition.inner.flipHorizontal.enable(False)
        self.w.inner.definition.inner.flipVertical.enable(False)

        definitionInputFields['flip'] = self.getFlipping

        ypos += 30
        self.w.inner.definition.inner.h4 = HorizontalLine((0, ypos, -0, 1))

        # Positioning
        ypos += 11
        self.w.inner.definition.inner.positionIcon = TextBox((0, ypos, 10, 17), u'↥')
        self.w.inner.definition.inner.positionTitle = TextBox((15, ypos, 70, 17), u'Align')

        ypos += 25
        self.w.inner.definition.inner.positionAlignY = Group((0, ypos, -0, 22))
        self.w.inner.definition.inner.positionAlignY.title = CheckBox((0, 2, 65, 17), u'Vert.', value=False, callback=self.updateDefinition)
        self.w.inner.definition.inner.positionAlignY.alignTo = PopUpButton((65, 2, 70, 17), ['top','center','bottom'], sizeStyle='small', callback=self.updateDefinition)
        self.w.inner.definition.inner.positionAlignY.of = TextBox((135, 2, 30, 17), u'to', alignment='center')
        availableReferences = self.heights.keys() + [''] + self.availableGlyphs
        self.w.inner.definition.inner.positionAlignY.reference = ComboBox((165, 2, -0, 17), availableReferences, sizeStyle='small', callback=self.updateDefinition)

        self.w.inner.definition.inner.positionAlignY.alignTo.enable(False)
        self.w.inner.definition.inner.positionAlignY.reference.enable(False)

        ypos += 25
        self.w.inner.definition.inner.positionAlignX = Group((0, ypos, -0, 22))
        self.w.inner.definition.inner.positionAlignX.title = CheckBox((0, 2, 65, 17), u'Hor.', value=False, callback=self.updateDefinition)
        self.w.inner.definition.inner.positionAlignX.alignTo = PopUpButton((65, 2, 70, 17), ['left','center','right'], sizeStyle='small', callback=self.updateDefinition)
        self.w.inner.definition.inner.positionAlignX.of = TextBox((135, 2, 30, 17), u'to', alignment='center')
        availableReferences = self.availableGlyphs
        self.w.inner.definition.inner.positionAlignX.reference = ComboBox((165, 2, -0, 17), availableReferences, sizeStyle='small', callback=self.updateDefinition)

        self.w.inner.definition.inner.positionAlignX.alignTo.enable(False)
        self.w.inner.definition.inner.positionAlignX.reference.enable(False)

        ypos += 37
        self.w.inner.definition.inner.positionOffset = Group((0, ypos, -0, 22))
        self.w.inner.definition.inner.positionOffset.title = TextBox((0, 2, 60, 17), u'offset')
        self.w.inner.definition.inner.positionOffset.xTitle = TextBox((60, 2, 15, 17), u'X')
        self.w.inner.definition.inner.positionOffset.x = EditText((75, 0, 50, 22), text='0', callback=self.updateDefinition, continuous=False)
        self.w.inner.definition.inner.positionOffset.yTitle = TextBox((150, 2, 15, 17), u'Y')
        self.w.inner.definition.inner.positionOffset.y = EditText((165, 0, 50, 22), text='0', callback=self.updateDefinition, continuous=False)

        definitionInputFields['yAlign'] = self.getYPositioning
        definitionInputFields['xAlign'] = self.getXPositioning
        definitionInputFields['offset'] = self.getOffset

        ypos += 37
        self.w.inner.definition.inner.contributeWidth = CheckBox((0, ypos, -0, 22), 'Add width', value=True, callback=self.updateDefinition)

        definitionInputFields['width'] = self.getWidthContribution

        for radiogroupName in ['asComponent']:
            radiogroup = getattr(self.w.inner.definition.inner, radiogroupName)
            radiogroup.set(0)

        self.definitionInputFields = definitionInputFields

        if len(self.derivatives):
            self.updateDefinitionSheet(self.derivatives[0]['glyphName'], self.derivatives[0])
            self.w.inner.derivatives.setSelection([0])
            self.updatePreview()

    def switchBaseGlyph(self, sender):
        baseGlyphIndex = sender.get()
        index, definition = self.getCurrentDefinition()
        glyphName = definition['glyphName']
        self.updateDefinitionSheet(glyphName, definition, baseGlyphIndex)

    def activateAlignment(self, activate, axis):
        alignment = getattr(self.w.inner.definition.inner, 'positionAlign%s'%(axis))
        alignTo = alignment.alignTo
        reference = alignment.reference
        if activate:
            alignTo.enable(True)
            reference.enable(True)
        elif not activate:
            alignTo.enable(False)
            reference.enable(False)

    def getWidthContribution(self):
        value = self.w.inner.definition.inner.contributeWidth.get()
        return value

    def getFlipping(self):
        hValue = self.booleanToScale(self.w.inner.definition.inner.flipHorizontal.get())
        vValue = self.booleanToScale(self.w.inner.definition.inner.flipVertical.get())
        return hValue, vValue

    def booleanToScale(self, value):
        if value == 0: return 1
        elif value == 1: return -1
        else: return 1

    def getCopyMode(self):
        b = bool(self.w.inner.definition.inner.asComponent.get())
        self.w.inner.definition.inner.flipHorizontal.enable(not b)
        self.w.inner.definition.inner.flipVertical.enable(not b)
        return b

    def getYPositioning(self):
        yAlign = self.w.inner.definition.inner.positionAlignY.title.get()
        if bool(yAlign) == True:
            alignementItems = self.w.inner.definition.inner.positionAlignY.alignTo.getItems()
            alignementIndex = self.w.inner.definition.inner.positionAlignY.alignTo.get()
            alignment = alignementItems[alignementIndex]
            reference = self.w.inner.definition.inner.positionAlignY.reference.get()
            self.activateAlignment(True, 'Y')
            if self.validateReference(reference, 'Y'):
                return alignment, reference
        elif bool(yAlign) == False:
            self.activateAlignment(False, 'Y')
        return False

    def getXPositioning(self):
        xAlign = self.w.inner.definition.inner.positionAlignX.title.get()
        if bool(xAlign) == True:
            alignementItems = self.w.inner.definition.inner.positionAlignX.alignTo.getItems()
            alignementIndex = self.w.inner.definition.inner.positionAlignX.alignTo.get()
            alignment = alignementItems[alignementIndex]
            reference = self.w.inner.definition.inner.positionAlignX.reference.get()
            self.activateAlignment(True, 'X')
            if self.validateReference(reference, 'X'):
                return alignment, reference
        elif bool(xAlign) == False:
            self.activateAlignment(False, 'X')
        return False

    def getOffset(self):
        try: x = int(self.w.inner.definition.inner.positionOffset.x.get())
        except: x = 0

        try: y = int(self.w.inner.definition.inner.positionOffset.y.get())
        except: y = 0

        return x, y

    def getRotationAngle(self):
        strValue = self.w.inner.definition.inner.rotation.get()
        try: value = float(strValue)
        except: value = 0
        return value

    def getRotationCenter(self):
        hReferencePoint = self.w.inner.definition.inner.hCenter.getItems()
        vReferencePoint = self.w.inner.definition.inner.vCenter.getItems()
        hIndex = self.w.inner.definition.inner.hCenter.get()
        vIndex = self.w.inner.definition.inner.vCenter.get()
        return hReferencePoint[hIndex], vReferencePoint[vIndex]

    def validateReference(self, reference, axis):
        if axis == 'Y':
            return reference in self.heights or reference in self.availableGlyphs
        elif axis == 'X':
            return reference in self.availableGlyphs

    def validateGlyphDefinition(self, definition):
        currentFont, tempFont = self.currentFont, self.tempFont
        baseGlyphNames = [baseGlyphName.split(':')[0] for baseGlyphName in definition['baseGlyphs']]
        validBaseGlyphsList = list(set(baseGlyphNames) & set(currentFont.keys() + tempFont.keys()))
        baseGlyphs = {}
        for baseGlyphName in baseGlyphNames:
            if baseGlyphName in tempFont:
                baseGlyphs[baseGlyphName] = tempFont[baseGlyphName]
            elif baseGlyphName in currentFont:
                baseGlyphs[baseGlyphName] = currentFont[baseGlyphName]
        baseGlyphRecords = definition['baseGlyphRecords']
        compositeBaseGlyphs = [baseGlyphName for baseGlyphName in definition['baseGlyphs'] if (baseGlyphName.split(':')[0] in validBaseGlyphsList) and (len(baseGlyphs[baseGlyphName.split(':')[0]].components))]
        return not bool(len(compositeBaseGlyphs)) and bool(len(validBaseGlyphsList))

    def buildDerivativesUIList(self, derivativesList):
        return [{'Derivative Glyph':definition['glyphName'], 'Base Glyphs':', '.join(definition['baseGlyphs'])} for definition in derivativesList]

    def selectBaseGlyph(self, sender):
        selection = sender.get()
        derivativeGlyphNames = [self.baseGlyphNames[index] for index in selection]
        self.w.inner.derivatives.set(derivativeGlyphNames)

    def updatePreview(self):
        font = self.currentFont
        tempFont = self.tempFont
        selection = self.w.inner.derivatives.getSelection()
        controlGlyphName = self.controlGlyph
        controlGlyph = font[controlGlyphName]
        glyphs = [controlGlyph]

        for index in selection:
            if index < len(self.derivatives):
                definition = self.derivatives[index]
                glyphName = definition['glyphName']
                if glyphName in tempFont:
                    g = tempFont[glyphName]
                else:
                    g = self.makeGlyph(definition, tempFont)
                if g is not None:
                    glyphs.append(g)
                    glyphs.append(controlGlyph)

        self.w.inner.preview.setFont(tempFont)
        self.w.inner.preview.set(glyphs)
        self.tempFont = tempFont

    def makeGlyph(self, definition, font):
        currentFont = self.currentFont
        italicAngle = font.info.italicAngle
        glyphName = definition['glyphName']
        baseGlyphs = definition['baseGlyphs']
        baseGlyphRecords = definition['baseGlyphRecords']

        if glyphName in font:
            glyph = font[glyphName]
            glyph.clear()
        else:
            font.newGlyph(glyphName, True)
            glyph = font[glyphName]

        glyph.prepareUndo('deriveFromBase')
        glyphWidth = 0
        xAdvance = 0
        margins = {'left':[], 'right':[]}

        for b, baseGlyphName in enumerate(baseGlyphs):

            baseGlyphRecord = baseGlyphRecords[baseGlyphName]
            baseGlyphName = baseGlyphName.split(':')[0]
            baseGlyph = None

            if baseGlyphName in self.derivedGlyphs:

                index = self.derivedGlyphs.index(baseGlyphName)
                subDefinition = self.derivatives[index]

                if baseGlyphName not in font:
                    font.newGlyph(baseGlyphName, True)
                    baseGlyph = self.makeGlyph(subDefinition, font)

                elif baseGlyphName in font:
                    baseGlyph = font[baseGlyphName]
            else:
                if baseGlyphName in self.availableGlyphs:
                   font[baseGlyphName] = currentFont[baseGlyphName].copy()
                   baseGlyph = font[baseGlyphName]
#                    baseGlyph = currentFont[baseGlyphName]

            if baseGlyph is None:
                return

            baseWidth = baseGlyph.width
            straightLeftMargin = baseGlyph.leftMargin
            leftMargin = baseGlyph.angledLeftMargin
            rightMargin = baseGlyph.angledRightMargin
            baseDimensions = self.getGlyphDimensions(baseGlyph)

            contributeWidth = baseGlyphRecord['width']

            xCenter, yCenter = baseDimensions['center']
            xShift, yShift = 0, 0
            h1, h2 = 0, 0

            xShift += xAdvance

            xOffset, yOffset = baseGlyphRecord['offset']
            xShift += xOffset
            yShift += yOffset

            if baseGlyphRecord['yAlign']:
                line, reference = baseGlyphRecord['yAlign']
                if reference in self.heights.keys():
                    h1 = self.heights[reference]
                elif reference in self.availableGlyphs:
                    referenceGlyph = currentFont[reference]
                    if referenceGlyph.box is not None:
                        if line == 'top':
                            h1 = referenceGlyph.box[3]
                        elif line == 'bottom':
                            h1 = referenceGlyph.box[1]
                        elif line == 'center':
                            h1 = ((referenceGlyph.box[3] - referenceGlyph.box[1]) / 2) + referenceGlyph.box[1]
                if line == 'top':
                    h2 = baseDimensions['yTop']
                elif line == 'bottom':
                    h2 = baseDimensions['yBottom']
                elif line == 'center':
                    h2 = yCenter
                yShift += (h1 - h2)

            if baseGlyphRecord['xAlign']:
                line, reference = baseGlyphRecord['xAlign']
                referenceGlyph = currentFont[reference]
                if referenceGlyph.box is not None:
                    if line == 'left':
                        w1 = glyph.angledLeftMargin
                    elif line == 'right':
                        w1 = glyph.width - glyph.angledRightMargin
                    elif line == 'center':
                        w1 = glyph.angledLeftMargin + (self.getOutlineWidth(referenceGlyph) / 2)
                if line == 'left':
                    w2 = baseDimensions['xLeft']
                elif line == 'right':
                    w2 = baseDimensions['xRight']
                elif line == 'center':
                    w2 = xCenter
                xShift += (w1 - w2)

            slantOffset = yShift * tan(radians(italicAngle))
            xShift -= slantOffset

            if not contributeWidth:
                xShift -= xAdvance

            dimensions = self.getGlyphDimensions(baseGlyph)
            xCenter, yCenter = dimensions['center']

            tempGlyph = baseGlyph.copy()
            tempGlyph.scale(baseGlyphRecord['flip'], (xCenter, yCenter))

            if baseGlyphRecord['asComponent']:
                glyph.appendComponent(baseGlyphName, (xShift, yShift))

            elif not baseGlyphRecord['asComponent']:
                glyph.appendGlyph(tempGlyph, (xShift, yShift))

            if contributeWidth:
                baseWidth += (xShift - xAdvance)

            if baseGlyphRecord['flip'][0] == 1:
                if b == 0 or (b > 0 and contributeWidth):
                    margins['left'].append(leftMargin)
                    margins['right'].append(rightMargin)

            elif baseGlyphRecord['flip'][0] == -1:
                if b == 0 or (b > 0 and contributeWidth):
                    margins['left'].append(rightMargin)
                    margins['right'].append(leftMargin)

            if contributeWidth:
                xAdvance += baseWidth
                glyphWidth += baseWidth

        glyph.width = glyphWidth
        if len(margins['left']):
            glyph.angledLeftMargin = margins['left'][0]
        if len(margins['right']):
            glyph.angledRightMargin = margins['right'][-1]
        glyph.performUndo()

        return glyph


    def getOutlineWidth(self, glyph):
        return glyph.width - (glyph.angledLeftMargin + glyph.angledRightMargin)

    def getGlyphDimensions(self, glyph):
        dimensions = {}
        dimensions['width'] = self.getOutlineWidth(glyph)
        dimensions['yAlign'] = glyph.box[3] - glyph.box[1] if glyph.box is not None else 0
        dimensions['center'] = (
            # ((glyph.box[2] - glyph.box[0]) / 2) + glyph.box[0] if glyph.box is not None else 0,
            glyph.angledLeftMargin + (self.getOutlineWidth(glyph) / 2),
            ((glyph.box[3] - glyph.box[1]) / 2) + glyph.box[1] if glyph.box is not None else 0
            )
        dimensions['yTop'] = glyph.box[3] if glyph.box is not None else 0
        dimensions['yBottom'] = glyph.box[1] if glyph.box is not None else 0
        dimensions['xLeft'] = glyph.angledLeftMargin
        dimensions['xRight'] = glyph.width - glyph.angledRightMargin
        return dimensions

    def buildSelectedGlyphs(self, sender):
        font = self.currentFont
        selection = self.w.inner.derivatives.getSelection()
        derivatives = self.derivatives
        for index in selection:
            definition = derivatives[index]
            glyphName = definition['glyphName']
            self.makeGlyph(definition, font)

    def storeGlyphDefinitions(self, definitions):
        font = self.currentFont

        if not font.lib.has_key('com.loicsander.derivativeGlyphsBuilder'):
            font.lib['com.loicsander.derivativeGlyphsBuilder'] = {}
        derivativeGlyphsBuilderStorage = font.lib['com.loicsander.derivativeGlyphsBuilder']

        derivativeGlyphsBuilderStorage['derivedGlyphs'] = self.getDefinitionsDict(definitions)

    def getDefinitionsDict(self, definitions):
        return {glyphName:(baseGlyphsList, baseGlyphRecords) for glyphName, baseGlyphsList, baseGlyphRecords in definitions}

    def getGlyphDefinitions(self):
        font = self.currentFont
        fontKeys = font.keys()
        definitions = []
        if font.lib.has_key('com.loicsander.derivativeGlyphsBuilder'):
            derivativeGlyphsBuilderStorage = font.lib['com.loicsander.derivativeGlyphsBuilder']
            if derivativeGlyphsBuilderStorage.has_key('derivedGlyphs'):
                derivedGlyphNames = derivativeGlyphsBuilderStorage['derivedGlyphs']
                for glyphName, (baseGlyphList, baseGlyphRecords) in derivedGlyphNames.items():
                    glyphDefinition = GlyphDefinition(glyphName, baseGlyphRecords)
                    glyphDefinition.updateBaseGlyphsList(baseGlyphList)
                    definitions.append(glyphDefinition)
        return definitions

    def copySelectedDefinitions(self, sender):
        selection = self.w.inner.derivatives.getSelection()
        definitions = [definition for i, definition in enumerate(self.derivatives) if i in selection]
        if len(definitions):
            self.copiedDefinitions = definitions
            l = len(definitions)
            self.w.inner.pasteDefinitions.setTitle('Paste (%s)' % (l))
            self.w.inner.pasteDefinitions.enable(True)

    def pasteDefinitions(self, sender):
        if self.copiedDefinitions is not None:
            self.storeGlyphDefinitions(self.copiedDefinitions)

        self.derivatives = self.getGlyphDefinitions()
        self.baseGlyphsList = [derivative['baseGlyphs'] for derivative in self.derivatives]
        self.derivedGlyphs = [derivative['glyphName'] for derivative in self.derivatives]

        self.updateDefinitionsList()

    def clearTemporaryData(self):
        self.tempFont.close()

    def endOperations(self, notification):
        for callback, event in self.events:
            removeObserver(self, event)
        self.clearTemporaryData()

DerivativeGlyphsBuilder()