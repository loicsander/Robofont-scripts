#coding=utf-8


'''
Interpolation Matrix
v0.6
Interpolation matrix implementing Erik van Blokland’s MutatorMath objects (https://github.com/LettError/MutatorMath)
in a grid/matrix, allowing for easy preview of inter/extrapolation behavior of letters while drawing in Robofont.
As the math is the same to Superpolator’s, the preview is as close as can be to Superpolator output,
although you don’t have as fine a coordinate system with this matrix (up to 15x15).

(The standalone script will work only on Robofont from versions 1.6 onward)
(For previous versions of Robofont (tested on 1.5 only) you can use the extension)

Loïc Sander
'''

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator
from fontMath.mathGlyph import MathGlyph
from fontMath.mathInfo import MathInfo
from fontMath.mathKerning import MathKerning

from vanilla import *
from vanilla.dialogs import putFile, getFile
from defconAppKit.controls.fontList import FontList
from defconAppKit.tools.textSplitter import splitText
from defconAppKit.windows.progressWindow import ProgressWindow
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver
from mojo.extensions import getExtensionDefaultColor, setExtensionDefaultColor
from AppKit import NSColor, NSThickSquareBezelStyle, NSFocusRingTypeNone, NSBoxCustom, NSBezelBorder, NSLineBorder
from math import cos, sin, pi
from time import time
import os
import re

MasterColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.4, 0.1, 0.2, 1)
BlackColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
GlyphBoxFillColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.4, 0.4, .1)
GlyphBoxTextColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0.4, 0.4, 1)
GlyphBoxBorderColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 1)
Transparent = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0)

def makePreviewGlyph(glyph, fixedWidth=True):
    if glyph is not None:
        components = glyph.components
        font = glyph.getParent()
        previewGlyph = RGlyph()

        if font is not None:
            for component in components:
                base = font[component.baseGlyph]
                if len(base.components) > 0:
                    base = makePreviewGlyph(base, False)
                decomponent = RGlyph()
                decomponent.appendGlyph(base)
                decomponent.scale((component.scale[0], component.scale[1]))
                decomponent.move((component.offset[0], component.offset[1]))
                previewGlyph.appendGlyph(decomponent)
            for contour in glyph.contours:
                previewGlyph.appendContour(contour)

            if fixedWidth:
                previewGlyph.width = 1000
                previewGlyph.leftMargin = previewGlyph.rightMargin = (previewGlyph.leftMargin + previewGlyph.rightMargin)/2
                previewGlyph.scale((.75, .75), (previewGlyph.width/2, 0))
                previewGlyph.move((0, -50))

            previewGlyph.name = glyph.name

        return previewGlyph
    return

def errorGlyph():
    glyph = RGlyph()
    glyph.width = 500
    pen = glyph.getPen()

    l = 50
    p = (220, 150)
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

def getValueForKey(ch):
    try:
        return 'abcdefghijklmnopqrstuvwxyz'.index(ch)
    except:
        return

def getKeyForValue(i):
    try:
        A = 'abcdefghijklmnopqrstuvwxyz'
        return A[i]
    except:
        return

def splitFlatSpot(flatSpot):
    try:
        ch = flatSpot[0]
        j = int(flatSpot[1:])
        return ch, j
    except:
        return None

def fontName(font):
    return ' '.join([font.info.familyName, font.info.styleName])

def colorToTuple(color): # convert NSColor to rgba tuple
    return color.redComponent(), color.greenComponent(), color.blueComponent(), color.alphaComponent(),

class MatrixMaster(object):

    def __init__(self, spot=None, font=None):
        self.font = font
        a, b = spot
        if isinstance(a, int):
            self.spot = (getKeyForValue(a), b)
            self.i = a
        else:
            self.spot = (a, b)
            self.i = getValueForKey(a)
        self.j = b

    def __getitem__(self, index):
        if index == 0:
            return self.spot
        elif index == 1:
            return self.font
        else:
            raise IndexError

    def shift(self, iAdd, jAdd):
        self.i += iAdd
        self.j += jAdd
        self.spot = (getKeyForValue(self.i), j)

    def setCoord(self, i, j):
        self.i, self.j = i, j
        self.spot = (getKeyForValue(i), j)

    def setFont(self, font):
        self.font = font

    def getLocation(self):
        return Location(horizontal=self.i, vertical=self.j)

    def getFont(self):
        return self.font

    def getSpot(self):
        return self.spot

    def getFlatSpot(self):
        return self.spot[0] + str(self.spot[1])

    def getCoord(self):
        return self.i, self.j

    def getPath(self):
        if hasattr(self.font, 'path'):
            return self.font.path

class InterpolationMatrixController:

    def __init__(self):
        bgColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(255, 255, 255, 255)
        buttonColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 255)
        self.w = Window((1000, 400), 'Interpolation Matrix', minSize=(470, 300))
        self.w.getNSWindow().setBackgroundColor_(bgColor)
        self.w.glyphTitle = Box((10, 10, 200, 30))
        self.w.glyphTitle.name = EditText((5, 0, -5, 20), 'No current glyph', self.changeGlyph, continuous=False)
        glyphEdit = self.w.glyphTitle.name.getNSTextField()
        glyphEdit.setBordered_(False)
        glyphEdit.setBackgroundColor_(Transparent)
        glyphEdit.setFocusRingType_(NSFocusRingTypeNone)
        self.axesGrid = {'horizontal': 3, 'vertical': 1}
        self.gridMax = 15
        self.masters = []
        self.instanceSpots = []
        self.mutatorMasters = None
        self.mutator = None
        self.currentGlyph = None
        self.errorGlyph = errorGlyph()
        self.buildMatrix((self.axesGrid['horizontal'], self.axesGrid['vertical']))
        self.w.addColumn = SquareButton((-80, 10, 30, 30), u'+', callback=self.addColumn)
        self.w.removeColumn = SquareButton((-115, 10, 30, 30), u'-', callback=self.removeColumn)
        self.w.addLine = SquareButton((-40, -40, 30, 30), u'+', callback=self.addLine)
        self.w.removeLine = SquareButton((-40, -72, 30, 30), u'-', callback=self.removeLine)
        for button in [self.w.addColumn, self.w.removeColumn, self.w.addLine, self.w.removeLine]:
            button.getNSButton().setBezelStyle_(10)
        self.w.generate = GradientButton((225, 10, 100, 30), title=u'Generate…', callback=self.generationSheet)
        self.w.loadMatrix = GradientButton((430, 10, 70, 30), title='Load', callback=self.loadMatrixFile)
        self.w.saveMatrix = GradientButton((505, 10, 70, 30), title='Save', callback=self.saveMatrix)
        self.w.clearMatrix = GradientButton((580, 10, 70, 30), title='Clear', callback=self.clearMatrix)
        addObserver(self, 'updateMatrix', 'currentGlyphChanged')
        addObserver(self, 'updateMatrix', 'fontDidClose')
        addObserver(self, 'updateMatrix', 'mouseUp')
        addObserver(self, 'updateMatrix', 'keyUp')
        self.w.bind('close', self.windowClose)
        self.w.bind('resize', self.windowResize)
        self.w.open()

    def buildMatrix(self, axesGrid):
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        if hasattr(self.w, 'matrix'):
            delattr(self.w, 'matrix')
        self.w.matrix = Group((0, 50, -50, -0))
        matrix = self.w.matrix
        windowPosSize = self.w.getPosSize()
        cellXSize, cellYSize = self.glyphPreviewCellSize(windowPosSize, axesGrid)

        for i in range(nCellsOnHorizontalAxis):
            ch = getKeyForValue(i)
            for j in range(nCellsOnVerticalAxis):
                setattr(matrix, '%s%s'%(ch,j), Group(((i*cellXSize)-i, (j*cellYSize), cellXSize, cellYSize)))
                xEnd = yEnd = -2
                if i == nCellsOnHorizontalAxis-1:
                    xEnd = -3
                if j == nCellsOnVerticalAxis-1:
                    yEnd = -3
                bSize = (2, 2, xEnd, yEnd)
                cell = getattr(matrix, '%s%s'%(ch,j))
                cell.background = Box(bSize)
                cell.selectionMask = Box(bSize)
                cell.selectionMask.show(False)
                cell.masterMask = Box(bSize)
                cell.masterMask.show(False)
                for box in [cell.background, cell.selectionMask, cell.masterMask]:
                    box = box.getNSBox()
                    box.setBoxType_(NSBoxCustom)
                    box.setFillColor_(GlyphBoxFillColor)
                    box.setBorderWidth_(2)
                    box.setBorderColor_(GlyphBoxBorderColor)
                cell.glyphView = GlyphPreview(bSize)
                cell.button = SquareButton((0, 0, -0, -0), None, callback=self.pickSpot)
                cell.button.spot = (ch, j)
                # cell.button.getNSButton().setBordered_(False)
                cell.button.getNSButton().setTransparent_(True)
                cell.coordinate = TextBox((5, -17, 30, 12), '%s%s'%(ch.capitalize(), j+1), sizeStyle='mini')
                cell.coordinate.getNSTextField().setTextColor_(GlyphBoxTextColor)
                cell.name = TextBox((7, 7, -5, 12), '', sizeStyle='mini', alignment='left')
                cell.name.getNSTextField().setTextColor_(MasterColor)

    def updateMatrix(self, notification=None):
        axesGrid = self.axesGrid['horizontal'], self.axesGrid['vertical']
        self.currentGlyph = currentGlyph = self.getCurrentGlyph(notification)
        if currentGlyph is not None:
            self.w.glyphTitle.name.set(currentGlyph)
        elif currentGlyph is None:
            self.w.glyphTitle.name.set('No current glyph')
        self.placeGlyphMasters(currentGlyph, axesGrid)
        self.makeGlyphInstances(axesGrid)

    def placeGlyphMasters(self, glyphName, axesGrid):
        availableFonts = AllFonts()
        masters = self.masters
        mutatorMasters = []
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        matrix = self.w.matrix
        masterGlyph = None

        for matrixMaster in masters:
            spot, masterFont = matrixMaster
            ch, j = spot
            i = getValueForKey(ch)

            if (masterFont in availableFonts) and (glyphName is not None) and (glyphName in masterFont):
                if i <= nCellsOnHorizontalAxis and j <= nCellsOnVerticalAxis:
                    l = Location(horizontal=i, vertical=j)
                    masterGlyph = makePreviewGlyph(masterFont[glyphName])
                    if masterGlyph is not None:
                        mutatorMasters.append((l, MathGlyph(masterGlyph)))
            elif (masterFont not in availableFonts):
                masters.remove(matrixMaster)

            if i < nCellsOnHorizontalAxis and j < nCellsOnVerticalAxis:
                cell = getattr(matrix, '%s%s'%(ch, j))
                cell.glyphView.setGlyph(masterGlyph)
                if masterGlyph is not None:
                    cell.glyphView.getNSView().setContourColor_(MasterColor)
                    cell.masterMask.show(True)
                    fontName = ' '.join([masterFont.info.familyName, masterFont.info.styleName])
                    cell.name.set(fontName)
                elif masterGlyph is None:
                    cell.glyphView.getNSView().setContourColor_(BlackColor)
                    cell.masterMask.show(False)
                    cell.name.set('')

        self.mutatorMasters = mutatorMasters

    def makeGlyphInstances(self, axesGrid):

        instanceTime = []

        mutatorMasters = self.mutatorMasters
        masterSpots = [spot for spot, masterFont in self.masters]
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        matrix = self.w.matrix
        instanceGlyphs = None

        # start = time()
        # count = 0

        if mutatorMasters:

            try:
                bias, mutator = buildMutator(mutatorMasters)
            except:
                mutator = None

            for i in range(nCellsOnHorizontalAxis):
                ch = getKeyForValue(i)

                for j in range(nCellsOnVerticalAxis):

                    if (ch, j) not in masterSpots:

                        if mutator is not None:
                            instanceLocation = Location(horizontal=i, vertical=j)
                            instanceStart = time()
                            instanceGlyph = RGlyph()
                            iGlyph = mutator.makeInstance(instanceLocation)
                            instanceGlyph = iGlyph.extractGlyph(RGlyph())
                            instanceStop = time()
                            instanceTime.append((instanceStop-instanceStart)*1000)
                        else:
                            instanceGlyph = self.errorGlyph

                        cell = getattr(matrix, '%s%s'%(ch, j))
                        cell.glyphView.setGlyph(instanceGlyph)
    #                     count += 1

        # stop = time()
        # if count:
        #     wholeTime = (stop-start)*1000
        #     print 'made %s instances in %0.3fms, average: %0.3fms' % (count, wholeTime, wholeTime/count)

    def generationSheet(self, sender):

        readableCoord = None
        incomingSpot = None

        if hasattr(sender, 'spot'):
            if hasattr(self.w, 'spotSheet'):
                self.w.spotSheet.close()
            incomingSpot = sender.spot
            ch, j = incomingSpot
            readableCoord = '%s%s'%(ch.upper(), j+1)

        hAxis, vAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        self.w.generateSheet = Sheet((500, 275), self.w)
        generateSheet = self.w.generateSheet
        if incomingSpot is None:
            generateSheet.tabs = Tabs((15, 12, -15, -15), ['Instance(s)','Report'])
            instance = generateSheet.tabs[0]
            report = generateSheet.tabs[1]
        elif incomingSpot is not None:
            generateSheet.instance = Group((20, 20, -20, -20))
            instance = generateSheet.instance

        instance.guide = TextBox((10, 7, -10, 22),
            u'A1, B2, C4 — A, C (whole columns) — 1, 5 (whole lines) — * (everything)',
            sizeStyle='small'
            )
        instance.headerBar = HorizontalLine((10, 25, -10, 1))
        instance.spotsListTitle = TextBox((10, 40, 70, 17), 'Locations')
        instance.spots = EditText((100, 40, -10, 22))
        if readableCoord is not None:
            instance.spots.set(readableCoord)

        instance.sourceFontTitle = TextBox((10, 90, -280, 17), 'Source font (naming & groups)', sizeStyle='small')
        instance.sourceFontBar = HorizontalLine((10, 110, -280, 1))
        instance.sourceFont = PopUpButton((10, 120, -280, 22), [fontName(masterFont) for spot, masterFont in self.masters], sizeStyle='small')

        instance.interpolationOptions = TextBox((-250, 90, -10, 17), 'Interpolate', sizeStyle='small')
        instance.optionsBar = HorizontalLine((-250, 110, -10, 1))
        instance.glyphs = CheckBox((-240, 120, -10, 22), 'Glyphs', value=True, sizeStyle='small')
        instance.fontInfos = CheckBox((-240, 140, -10, 22), 'Font info', value=True, sizeStyle='small')
        instance.kerning = CheckBox((-120, 120, -10, 22), 'Kerning', value=True, sizeStyle='small')
        instance.groups = CheckBox((-120, 140, -10, 22), 'Copy Groups', value=True, sizeStyle='small')

        instance.openUI = CheckBox((10, -48, -10, 22), 'Open generated fonts', value=True, sizeStyle='small')
        instance.report = CheckBox((10, -28, -10, 22), 'Generation report', value=False, sizeStyle='small')

        instance.yes = Button((-170, -30, 160, 20), 'Generate Instance(s)', self.getGenerationInfo)
        instance.yes.id = 'instance'
        instance.no = Button((-250, -30, 75, 20), 'Cancel', callback=self.cancelGeneration)

        if incomingSpot is None:
            report.options = RadioGroup((10, 5, -10, 40), ['Report only', 'Report and mark glyphs'], isVertical=False)
            report.options.set(0)
            report.markColors = Group((10, 60, -10, -40))
            report.markColors.title = TextBox((0, 5, -10, 20), 'Mark glyphs', sizeStyle='small')
            report.markColors.bar = HorizontalLine((0, 25, 0, 1))
            report.markColors.compatibleTitle = TextBox((0, 35, 150, 20), 'Compatible')
            report.markColors.compatibleColor = ColorWell(
                (170, 35, -0, 20),
                color=getExtensionDefaultColor('interpolationMatrix.compatibleColor', fallback=NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3,0.8,0,.9)))
            report.markColors.incompatibleTitle = TextBox((0, 60, 150, 20), 'Incompatible')
            report.markColors.incompatibleColor = ColorWell(
                (170, 60, -0, 20),
                color=getExtensionDefaultColor('interpolationMatrix.incompatibleColor', fallback=NSColor.colorWithCalibratedRed_green_blue_alpha_(0.9,0.1,0,1)))
            report.markColors.mixedTitle = TextBox((0, 85, 150, 20), 'Mixed compatibility')
            report.markColors.mixedColor = ColorWell(
                (170, 85, -0, 20),
                color=getExtensionDefaultColor('interpolationMatrix.mixedColor', fallback=NSColor.colorWithCalibratedRed_green_blue_alpha_(.6,.7,.3,.5)))
            report.yes = Button((-170, -30, 160, 20), 'Generate Report', self.getGenerationInfo)
            report.yes.id = 'report'
            report.no = Button((-250, -30, 75, 20), 'Cancel', callback=self.cancelGeneration)

        generateSheet.open()

    def getGenerationInfo(self, sender):

        _ID = sender.id
        generateSheet = self.w.generateSheet
        generateSheet.close()

        if _ID == 'instance':
            if hasattr(generateSheet, 'tabs'):
                instanceTab = generateSheet.tabs[0]
            elif hasattr(generateSheet, 'instance'):
                instanceTab = generateSheet.instance
            spotsList = []

            if self.masters:
                availableFonts = AllFonts()
                mastersList = instanceTab.sourceFont.getItems()
                sourceFontIndex = instanceTab.sourceFont.get()
                sourceFontName = mastersList[sourceFontIndex]
                sourceFont = [masterFont for spot, masterFont in self.masters if fontName(masterFont) == sourceFontName and masterFont in availableFonts]

                generationInfos = {
                    'sourceFont': sourceFont,
                    'interpolateGlyphs': instanceTab.glyphs.get(),
                    'interpolateKerning': instanceTab.kerning.get(),
                    'interpolateFontInfos': instanceTab.fontInfos.get(),
                    'addGroups': instanceTab.groups.get(),
                    'openFonts': instanceTab.openUI.get(),
                    'report': instanceTab.report.get()
                }

                spotsInput = instanceTab.spots.get()
                spotsList = self.parseSpotsList(spotsInput)

                if (spotsList is None):
                    print u'Interpolation matrix — at least one location is required.'
                    return

                # print ['%s%s'%(getKeyForValue(i).upper(), j+1) for i, j in spotsList]

            for spot in spotsList:
                i, j = spot
                ch = getKeyForValue(i)
                pickedCell = getattr(self.w.matrix, '%s%s'%(ch, j))
                pickedCell.selectionMask.show(False)
                self.generateInstanceFont(spot, generationInfos)

        elif _ID == 'report':
            reportTab = generateSheet.tabs[1]

            compatibleColor = reportTab.markColors.compatibleColor.get()
            incompatibleColor = reportTab.markColors.incompatibleColor.get()
            mixedColor = reportTab.markColors.mixedColor.get()

            setExtensionDefaultColor('interpolationMatrix.incompatibleColor', incompatibleColor)
            setExtensionDefaultColor('interpolationMatrix.compatibleColor', compatibleColor)
            setExtensionDefaultColor('interpolationMatrix.mixedColor', mixedColor)

            reportInfos = {
                'markGlyphs': bool(reportTab.options.get()),
                'compatibleColor': colorToTuple(compatibleColor),
                'incompatibleColor': colorToTuple(incompatibleColor),
                'mixedColor': colorToTuple(mixedColor)
            }

            self.generateCompatibilityReport(reportInfos)

        delattr(self.w, 'generateSheet')

    def parseSpotsList(self, inputSpots):

        axesGrid = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        inputSpots = inputSpots.split(',')
        masterSpots = [(getValueForKey(ch),j) for (ch, j), masterFont in self.masters]
        spotsToGenerate = []

        if inputSpots[0] == '':
            return
        elif inputSpots[0] == '*':
            return [(i, j) for i in range(nCellsOnHorizontalAxis) for j in range(nCellsOnVerticalAxis) if (i,j) not in masterSpots]
        else:
            for item in inputSpots:
                parsedSpot = self.parseSpot(item, axesGrid)
                if parsedSpot is not None:
                    parsedSpot = list(set(parsedSpot) - set(masterSpots))
                    spotsToGenerate += parsedSpot
            return spotsToGenerate

    def parseSpot(self, spotName, axesGrid):
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        s = re.search('([a-zA-Z](?![0-9]))|([a-zA-Z][0-9][0-9]?)|([0-9][0-9]?)', spotName)
        if s:
            letterOnly = s.group(1)
            letterNumber = s.group(2)
            numberOnly = s.group(3)

            if numberOnly is not None:
                lineNumber = int(numberOnly) - 1
                if lineNumber < nCellsOnVerticalAxis:
                    return [(i, lineNumber) for i in range(nCellsOnHorizontalAxis)]

            elif letterOnly is not None:
                columnNumber = getValueForKey(letterOnly.lower())
                if columnNumber is not None and columnNumber < nCellsOnHorizontalAxis:
                    return [(columnNumber, j) for j in range(nCellsOnVerticalAxis)]

            elif letterNumber is not None:
                letter = letterNumber[:1]
                number = letterNumber[1:]
                columnNumber = getValueForKey(letter.lower())
                try:
                    lineNumber = int(number) - 1
                except:
                    return
                if columnNumber is not None and columnNumber < nCellsOnHorizontalAxis and lineNumber < nCellsOnVerticalAxis:
                    return [(columnNumber, lineNumber)]
        return

    def cancelGeneration(self, sender):
        self.w.generateSheet.close()
        delattr(self.w, 'generateSheet')

    def generateInstanceFont(self, spot, generationInfos):

        if generationInfos['sourceFont']:

            start = time()
            report = []

            doGlyphs = bool(generationInfos['interpolateGlyphs'])
            doKerning = bool(generationInfos['interpolateKerning'])
            doFontInfos = bool(generationInfos['interpolateFontInfos'])
            addGroups = bool(generationInfos['addGroups'])
            doReport = bool(generationInfos['report'])
            UI = bool(generationInfos['openFonts'])

            try:
                masters = self.masters
                baseFont = generationInfos['sourceFont'][0]
                newFont = None
                folderPath = None
                s = re.search('(.*)/(.*)(.ufo)', baseFont.path)
                if s is not None:
                    folderPath = s.group(1)

                masterFonts = [font for _, font in masters]

                i, j = spot
                ch = getKeyForValue(i)
                instanceLocation = Location(horizontal=i, vertical=j)
                instanceName = '%s%s'%(ch.upper(), j+1)
                masterLocations = [(matrixMaster.getLocation(), matrixMaster.getFont()) for matrixMaster in masters]

                progress = ProgressWindow('Generating instance %s%s'%(ch.upper(), j+1), parentWindow=self.w)
                report.append(u'\n*** Generating instance %s ***\n'%(instanceName))

                # Build fontx
                if (doGlyphs == True) or (doKerning == True) or (doFontInfos == True) or (addGroups == True):

                    if hasattr(RFont, 'showUI') or (not hasattr(RFont, 'showUI') and (folderPath is not None)):
                        newFont = RFont(showUI=False)
                    elif not hasattr(RFont, 'showUI') and (folderPath is None):
                        newFont = RFont()
                    newFont.info.familyName = baseFont.info.familyName
                    newFont.info.styleName = '%s%s'%(ch.upper(), j+1)
                    try:
                        newFont.glyphOrder = baseFont.glyphOrder
                    except:
                        try:
                            newFont.glyphOrder = baseFont.lib['public.glyphOrder']
                        except:
                            try:
                                newFont.lib['public.glyphOrder'] = baseFont.lib['public.glyphOrder']
                            except:
                                try:
                                    newFont.lib['public.glyphOrder'] = baseFont.glyphOrder
                                except:
                                    pass
                    if folderPath is not None:
                        instancesFolder = u'%s%s'%(folderPath, '/matrix-instances')
                        if not os.path.isdir(instancesFolder):
                            os.makedirs(instancesFolder)
                        folderPath = instancesFolder
                        path = '%s/%s-%s%s'%(folderPath, newFont.info.familyName, newFont.info.styleName, '.ufo')
                    interpolatedGlyphs = []
                    interpolatedInfo = None
                    interpolatedKerning = None
                    interpolationReports = []

                    report.append(u'+ Created new font')

                # interpolate font infos

                if doFontInfos == True:
                    infoMasters = [(infoLocation, MathInfo(masterFont.info)) for infoLocation, masterFont in masterLocations]
                    try:
                        bias, iM = buildMutator(infoMasters)
                        instanceInfo = iM.makeInstance(instanceLocation)
                        instanceInfo.extractInfo(newFont.info)
                        report.append(u'+ Successfully interpolated font info')
                    except:
                        report.append(u'+ Couldn’t interpolate font info')

                # interpolate kerning

                if doKerning == True:
                    kerningMasters = [(kerningLocation, MathKerning(masterFont.kerning)) for kerningLocation, masterFont in masterLocations]
                    try:
                        bias, kM = buildMutator(kerningMasters)
                        instanceKerning = kM.makeInstance(instanceLocation)
                        instanceKerning.extractKerning(newFont)
                        report.append(u'+ Successfully interpolated kerning')
                        if addGroups == True:
                            for key, value in baseFont.groups.items():
                                newFont.groups[key] = value
                            report.append(u'+ Successfully transferred groups')
                    except:
                        report.append(u'+ Couldn’t interpolate kerning')

                # filter compatible glyphs

                glyphList, strayGlyphs = self.compareGlyphSets(masterFonts)
                incompatibleGlyphs = []

                if doGlyphs == True:

                    for glyphName in glyphList:
                        masterGlyphs = [(masterLocation, MathGlyph(masterFont[glyphName])) for masterLocation, masterFont in masterLocations]
                        try:
                            bias, gM = buildMutator(masterGlyphs)
                            newGlyph = RGlyph()
                            instanceGlyph = gM.makeInstance(instanceLocation)
                            newFont.insertGlyph(instanceGlyph.extractGlyph(newGlyph), glyphName)
                        except:
                            incompatibleGlyphs.append(glyphName)
                            continue

                    report.append(u'+ Successfully interpolated %s glyphs'%(len(newFont)))
                    report.append(u'+ Couldn’t interpolate %s glyphs'%(len(incompatibleGlyphs)))

                if (newFont is not None) and hasattr(RFont, 'showUI') and (folderPath is None) and UI:
                    newFont.autoUnicodes()
                    newFont.round()
                    newFont.showUI()
                elif (newFont is not None) and (folderPath is not None):
                    newFont.autoUnicodes()
                    newFont.round()
                    newFont.save(path)
                    report.append(u'\n—> Saved font to UFO at %s\n'%(path))
                    if UI:
                        f = RFont(path)
                elif (newFont is not None):
                    print u'Couldn’t save font to UFO.'
            except:
                print u'Couldn’t finish generating, something happened…'
                return
            finally:
                progress.close()

                if doReport:
                    print '\n'.join(report)

            # stop = time()
            # print 'generated in %0.3f' % ((stop-start)*1000)

    def compareGlyphSets(self, fonts):

        fontKeys = [set(font.keys()) for font in fonts]
        commonGlyphsList = set()
        strayGlyphs = set()
        for i, keys in enumerate(fontKeys):
            if i == 0:
                commonGlyphsList = keys
                strayGlyphs = keys
            elif i > 0:
                commonGlyphsList = commonGlyphsList & keys
                strayGlyphs = strayGlyphs - keys
        return list(commonGlyphsList), list(strayGlyphs)

    def generateCompatibilityReport(self, reportInfo):

        markGlyphs = reportInfo['markGlyphs']
        compatibleColor = reportInfo['compatibleColor']
        incompatibleColor = reportInfo['incompatibleColor']
        mixedCompatibilityColor = reportInfo['mixedColor']

        title = 'Generating report'
        if markGlyphs:
            title += ' & marking glyphs'
        progress = ProgressWindow(title, parentWindow=self.w)

        masterFonts = [font for _, font in self.masters]
        glyphList, strayGlyphs = self.compareGlyphSets(masterFonts)
        digest = []
        interpolationReports = []
        incompatibleGlyphs = 0

        for glyphName in glyphList:

            refMasterFont = masterFonts[0]
            refMasterGlyph = refMasterFont[glyphName]

            for masterFont in masterFonts[1:]:

                firstGlyph = refMasterFont[glyphName]
                secondGlyph = masterFont[glyphName]
                try:
                    compatible, report = firstGlyph.isCompatible(secondGlyph)
                except:
                    report = u'Compatibility check error'
                    compatible == False

                if compatible == False:
                    names = '%s <X> %s'%(fontName(refMasterFont), fontName(masterFont))
                    reportID = (names, report)
                    if reportID not in interpolationReports:
                        digest.append(names)
                        digest += [u'– %s'%(reportLine) for reportLine in report]
                        digest.append('\n')
                        interpolationReports.append(reportID)
                        incompatibleGlyphs += 1

                    if markGlyphs:
                        if refMasterFont[glyphName].mark == compatibleColor:
                           refMasterFont[glyphName].mark = mixedCompatibilityColor
                        elif refMasterFont[glyphName].mark != compatibleColor and refMasterFont[glyphName].mark != mixedCompatibilityColor:
                            refMasterFont[glyphName].mark = incompatibleColor
                        masterFont[glyphName].mark = incompatibleColor

                elif compatible == True:

                    if markGlyphs:
                        if refMasterFont[glyphName].mark == incompatibleColor or refMasterFont[glyphName].mark == mixedCompatibilityColor:
                           refMasterFont[glyphName].mark = mixedCompatibilityColor
                           masterFont[glyphName].mark = mixedCompatibilityColor
                        else:
                            refMasterFont[glyphName].mark = compatibleColor
                            masterFont[glyphName].mark = compatibleColor

        progress.close()

        print u'\n*   Compatible glyphs: %s'%(len(glyphList) - incompatibleGlyphs)
        print u'**  Incompatible glyphs: %s'%(incompatibleGlyphs)
        print u'*** Stray glyphs: %s\n– %s\n'%(len(strayGlyphs),u'\n– '.join(list(strayGlyphs)))
        print '\n'.join(digest)

    def glyphPreviewCellSize(self, posSize, axesGrid):
        x, y, w, h = posSize
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        w -= 50-nCellsOnHorizontalAxis
        h -= 50
        cellWidth = w / nCellsOnHorizontalAxis
        cellHeight = h / nCellsOnVerticalAxis
        return cellWidth, cellHeight

    def pickSpot(self, sender):
        spot = sender.spot
        masters = self.masters
        masterSpots = [_spot for _spot, masterFont in masters]
        matrix = self.w.matrix
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        font = None

        for i in range(nCellsOnHorizontalAxis):
            ch = getKeyForValue(i)
            for j in range(nCellsOnVerticalAxis):
                cell = getattr(matrix, '%s%s'%(ch, j))
                if (ch,j) == spot:
                    cell.selectionMask.show(True)
                else:
                    cell.selectionMask.show(False)

        self.w.spotSheet = Sheet((500, 250), self.w)
        spotSheet = self.w.spotSheet
        spotSheet.fontList = FontList((20, 20, -20, 150), AllFonts(), allowsMultipleSelection=False)
        if spot not in masterSpots:
            spotSheet.yes = Button((-140, -40, 120, 20), 'Place Master', callback=self.changeSpot)
            spotSheet.generate = Button((20, -40, 150, 20), 'Generate Instance', callback=self.generationSheet)
            spotSheet.generate.spot = spot
            if len(masters) <= 1:
                spotSheet.generate.enable(False)
            elif len(masters) > 1:
                spotSheet.generate.enable(True)
        elif spot in masterSpots:
            spotSheet.clear = Button((20, -40, 130, 20), 'Remove Master', callback=self.clearSpot)
            spotSheet.yes = Button((-140, -40, 120, 20), 'Change Master', callback=self.changeSpot)
        spotSheet.no = Button((-230, -40, 80, 20), 'Cancel', callback=self.keepSpot)
        for buttonName in ['clear', 'yes', 'no', 'generate']:
            if hasattr(spotSheet, buttonName):
                button = getattr(spotSheet, buttonName)
                button.spot = spot
        spotSheet.open()

    def changeSpot(self, sender):
        spot = sender.spot
        ch, j = sender.spot
        fontsList = self.w.spotSheet.fontList.get()
        selectedFontIndex = self.w.spotSheet.fontList.getSelection()[0]
        font = fontsList[selectedFontIndex]
        self.w.spotSheet.close()
        delattr(self.w, 'spotSheet')
        pickedCell = getattr(self.w.matrix, '%s%s'%(ch, j))
        pickedCell.selectionMask.show(False)
        i = getValueForKey(ch)
        l = MatrixMaster(spot, font)
        self.masters.append(l)
        self.updateMatrix()

    def clearSpot(self, sender):
        spot = (ch, j) = sender.spot
        self.w.spotSheet.close()
        delattr(self.w, 'spotSheet')
        pickedCell = getattr(self.w.matrix, '%s%s'%(ch, j))
        pickedCell.selectionMask.show(False)
        pickedCell.masterMask.show(False)
        pickedCell.glyphView.getNSView().setContourColor_(BlackColor)
        pickedCell.name.set('')
        for matrixMaster in self.masters:
            masterSpot, masterFont = matrixMaster
            if spot == masterSpot:
                self.masters.remove(matrixMaster)
                break
        self.mutator = None
        self.updateMatrix()

    def keepSpot(self, sender):
        ch, j = sender.spot
        self.w.spotSheet.close()
        delattr(self.w, 'spotSheet')
        pickedCell = getattr(self.w.matrix, '%s%s'%(ch, j))
        pickedCell.selectionMask.show(False)

    def addColumn(self, sender):
        gridMax = self.gridMax
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnHorizontalAxis += 1
        if nCellsOnHorizontalAxis > gridMax:
            nCellsOnHorizontalAxis = gridMax
        self.buildMatrix((nCellsOnHorizontalAxis, nCellsOnVerticalAxis))
        self.axesGrid['horizontal'] = nCellsOnHorizontalAxis
        self.updateMatrix()

    def removeColumn(self, sender):
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        mastersToRemove = []

        if (nCellsOnHorizontalAxis > 3) or \
           ((nCellsOnHorizontalAxis <= 3) and (nCellsOnHorizontalAxis > 1) and (nCellsOnVerticalAxis >= 3)):
            nCellsOnHorizontalAxis -= 1

        self.buildMatrix((nCellsOnHorizontalAxis, nCellsOnVerticalAxis))
        self.axesGrid['horizontal'] = nCellsOnHorizontalAxis
        for matrixMaster in self.masters:
            masterSpot, masterFont = matrixMaster
            ch, j = masterSpot
            i = getValueForKey(ch)
            if i >= nCellsOnHorizontalAxis:
                mastersToRemove.append(matrixMaster)
        for matrixMaster in mastersToRemove:
            self.masters.remove(matrixMaster)
        self.mutator = None
        self.updateMatrix()

    def addLine(self, sender):
        gridMax = self.gridMax
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnVerticalAxis += 1
        if nCellsOnVerticalAxis > gridMax:
            nCellsOnVerticalAxis = gridMax
        self.buildMatrix((nCellsOnHorizontalAxis, nCellsOnVerticalAxis))
        self.axesGrid['vertical'] = nCellsOnVerticalAxis
        self.updateMatrix()

    def removeLine(self, sender):
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        mastersToRemove = []

        if (nCellsOnVerticalAxis > 3) or \
           ((nCellsOnVerticalAxis <= 3) and (nCellsOnVerticalAxis > 1) and (nCellsOnHorizontalAxis >= 3)):
            nCellsOnVerticalAxis -= 1

        self.buildMatrix((nCellsOnHorizontalAxis, nCellsOnVerticalAxis))
        self.axesGrid['vertical'] = nCellsOnVerticalAxis
        for matrixMaster in self.masters:
            masterSpot, masterFont = matrixMaster
            ch, j = masterSpot
            if j >= nCellsOnVerticalAxis:
                mastersToRemove.append(matrixMaster)
        for matrixMaster in mastersToRemove:
            self.masters.remove(matrixMaster)
        self.mutator = None
        self.updateMatrix()

    def clearMatrix(self, sender):
        self.masters = []
        self.mutator = None
        matrix = self.w.matrix
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']

        for i in range(nCellsOnHorizontalAxis):
            ch = getKeyForValue(i)
            for j in range(nCellsOnVerticalAxis):
                cell = getattr(matrix, '%s%s'%(ch, j))
                cell.glyphView.setGlyph(None)
                cell.glyphView.getNSView().setContourColor_(BlackColor)
                cell.selectionMask.show(False)
                cell.masterMask.show(False)
                cell.name.set('')

    def saveMatrix(self, sender):
        pathToSave = putFile(title='Save interpolation matrix', fileName='matrix.txt', fileTypes=['txt'])
        if pathToSave is not None:
            masters = self.masters
            axesGrid = self.axesGrid
            matrixTextValues = []
            for master in masters:
                matrixTextValues.append(':'.join([master.getFlatSpot(), master.getPath()]))
            posSize = self.w.getPosSize()
            matrixTextValues = ['Matrix Interpolation File\n','%s,%s\n'%(axesGrid['horizontal'], axesGrid['vertical']), ','.join([str(value) for value in posSize]),'\n', str(self.currentGlyph),'\n',','.join(matrixTextValues)]
            matrixTextForm = ''.join(matrixTextValues)
            f = open(pathToSave, 'w')
            f.write(matrixTextForm)

    def loadMatrixFile(self, sender):
        pathToLoad = getFile(fileTypes=['txt'], allowsMultipleSelection=False, resultCallback=self.loadMatrix, parentWindow=self.w)

    def loadMatrix(self, pathToLoad):
        if pathToLoad is not None:
            f = open(pathToLoad[0], 'r')
            matrixTextForm = f.read()
            matrixValues = matrixTextForm.split('\n')
            if matrixValues and matrixValues[0] == 'Matrix Interpolation File':
                limits = tuple(matrixValues[1].split(','))
                axesGrid = int(limits[0]), int(limits[1])
                posSize = tuple([float(value) for value in matrixValues[2].split(',')])
                self.w.resize(posSize[2], posSize[3])
                self.axesGrid['horizontal'], self.axesGrid['vertical'] = axesGrid
                self.buildMatrix(axesGrid)
                self.currentGlyph = matrixValues[3]
                masterSpots = [value.split(':') for value in matrixValues[4].split(',')]
                if len(masterSpots):
                    masters = []
                    fontsToOpen = []
                    for masterSpot in masterSpots:
                        if len(masterSpot) == 2:
                            flatSpot, fontPath = masterSpot
                            spot = splitFlatSpot(flatSpot)
                            if (spot is not None) and (fontPath is not None):
                                f = [font for font in AllFonts() if font.path == fontPath]
                                if not len(f):
                                    f = RFont(fontPath)
                                elif len(f):
                                    f = f[0]
                                masters.append(MatrixMaster(spot, f))
                    self.masters = masters
                self.updateMatrix()
            else:
                print 'not a valid matrix file'


    def changeGlyph(self, sender):
        inputText = sender.get()
        try:
            charMap = CurrentFont().getCharacterMapping()
            glyphs = splitText(inputText, charMap)
            if len(glyphs):
                self.currentGlyph = glyphs[0]
                self.updateMatrix()
        except:
            return

    def getCurrentGlyph(self, notification=None):
        # if (info is not None) and (info.has_key('glyph')):
        #     currentGlyph = info['glyph']
        # elif (info is None) or (info is not None and not info.has_key('glyph')):
        if notification is not None:
            currentGlyph = CurrentGlyph()

            if currentGlyph is None:
                currentGlyphName = self.currentGlyph
            elif currentGlyph is not None:
                currentGlyphName = currentGlyph.name
            return currentGlyphName
        return self.currentGlyph

    def windowResize(self, info):
        axesGrid = (nCellsOnHorizontalAxis, nCellsOnVerticalAxis) = (self.axesGrid['horizontal'], self.axesGrid['vertical'])
        posSize = info.getPosSize()
        cW, cH = self.glyphPreviewCellSize(posSize, axesGrid)
        matrix = self.w.matrix

        for i in range(nCellsOnHorizontalAxis):
            ch = getKeyForValue(i)
            for j in range(nCellsOnVerticalAxis):
                cell = getattr(matrix, '%s%s'%(ch,j))
                cell.setPosSize((i*cW, j*cH, cW, cH))

    def windowClose(self, notification):
        self.w.unbind('close', self.windowClose)
        self.w.unbind('resize', self.windowResize)
        removeObserver(self, "currentGlyphChanged")
        removeObserver(self, "mouseUp")
        removeObserver(self, "keyUp")
        removeObserver(self, "fontDidClose")

InterpolationMatrixController()