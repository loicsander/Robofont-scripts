#coding=utf-8


'''
Interpolation Matrix
v0.5.1
Interpolation matrix implementing Erik van Blokland’s MutatorMath objects (https://github.com/LettError/MutatorMath)
in a grid/matrix, allowing for easy preview of inter/extrapolation behavior of letters while drawing in Robofont.
As the math are the same to Superpolator’s, the preview is as close as can be to Superpolator output,
although you don’t have as fine a coordinate system with this matrix (up to 20x20).

(The standalone script will work only on Robofont from versions 1.6 onward)
(For previous versions of Robofont (1.4+) you can use the extension)

Loïc Sander
'''

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator
from fontMath.mathGlyph import MathGlyph
from fontMath.mathInfo import MathInfo
from fontMath.mathKerning import MathKerning

from vanilla import *
from robofab.interface.all.dialogs import PutFile, GetFile, GetFolder
from defconAppKit.controls.fontList import FontList
from defconAppKit.tools.textSplitter import splitText
from defconAppKit.windows.progressWindow import ProgressWindow
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver
from AppKit import NSColor, NSThickSquareBezelStyle, NSFocusRingTypeNone
from math import cos, sin, pi
import re

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
    p = (220, 200)
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

def fontName(font):
    return ' '.join([font.info.familyName, font.info.styleName])

MasterColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.4, 0.1, 0.2, 1)
BlackColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
Transparent = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0)

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
        self.masters = []
        self.instanceSpots = []
        self.mutator = None
        self.currentGlyph = None
        self.errorGlyph = errorGlyph()
        self.buildMatrix((self.axesGrid['horizontal'], self.axesGrid['vertical']))
        self.w.addColumn = SquareButton((-80, 10, 30, 30), u'+', callback=self.addColumn)
        self.w.removeColumn = SquareButton((-115, 10, 30, 30), u'-', callback=self.removeColumn)
        self.w.addLine = SquareButton((-40, -40, 30, 30), u'+', callback=self.addLine)
        self.w.removeLine = SquareButton((-40, -70, 30, 30), u'-', callback=self.removeLine)
        for button in [self.w.addColumn, self.w.removeColumn, self.w.addLine, self.w.removeLine]:
            button.getNSButton().setBezelStyle_(10)
        self.w.clearMatrix = Button((220, 15, 70, 20), 'Clear', callback=self.clearMatrix)
        self.w.generate = Button((300, 15, 100, 20), 'Generate', callback=self.instanceGeneration)
        # self.w.saveMatrix = Button((300, 15, 70, 20), 'Save', callback=self.saveMatrix)
        # self.w.loadMatrix = Button((380, 15, 70, 20), 'Load', callback=self.loadMatrix)
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
                setattr(matrix, '%s%s'%(ch,j), Group(((i*cellXSize), (j*cellYSize), cellXSize, cellYSize)))
                cell = getattr(matrix, '%s%s'%(ch,j))
                cell.background = Box((0, 0, -0, -0))
                cell.selectionMask = Box((0, 0, -0, -0))
                cell.selectionMask.show(False)
                cell.masterMask = Box((0, 0, -0, -0))
                cell.masterMask.show(False)
                cell.glyphView = GlyphPreview((0, 0, -0, -0))
                cell.button = SquareButton((0, 0, -0, -0), None, callback=self.pickSpot)
                cell.button.spot = (ch, j)
                # cell.button.getNSButton().setBordered_(False)
                cell.button.getNSButton().setTransparent_(True)
                cell.coordinate = TextBox((5, -17, 30, 12), '%s%s'%(ch.capitalize(), j+1), sizeStyle='mini')
                cell.name = TextBox((40, -17, -10, 12), '', sizeStyle='mini', alignment='right')

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
        masters = []
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        matrix = self.w.matrix
        masterGlyph = None

        for matrixLocation in self.masters:
            spot, masterFont = matrixLocation
            ch, j = spot
            i = getValueForKey(ch)

            if (masterFont in availableFonts) and (glyphName is not None) and (glyphName in masterFont):
                if i <= nCellsOnHorizontalAxis and j <= nCellsOnVerticalAxis:
                    l = Location(horizontal=i, vertical=j)
                    masterGlyph = makePreviewGlyph(masterFont[glyphName])
                    if masterGlyph is not None:
                        masters.append((l, MathGlyph(masterGlyph)))
            elif (masterFont not in availableFonts):
                self.masters.remove(matrixLocation)

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

        if len(masters) > 1:
            try:
                bias, mutator = buildMutator(masters)
                self.mutator = mutator
            except:
                self.mutator = None

    def makeGlyphInstances(self, axesGrid):
        mutator = self.mutator
        masterSpots = [spot for spot, masterFont in self.masters]
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        matrix = self.w.matrix
        instanceGlyph = None

        for i in range(nCellsOnHorizontalAxis):
            ch = getKeyForValue(i)
            for j in range(nCellsOnVerticalAxis):
                if (ch, j) not in masterSpots:
                    instanceLocation = Location(horizontal=i, vertical=j)
                    if mutator is not None:
                        try:
                            instanceGlyph = RGlyph()
                            iGlyph = mutator.makeInstance(instanceLocation)
                            instanceGlyph = iGlyph.extractGlyph(instanceGlyph)
                        except:
                            instanceGlyph = self.errorGlyph
                    cell = getattr(matrix, '%s%s'%(ch, j))
                    cell.glyphView.setGlyph(instanceGlyph)

    def instanceGeneration(self, sender):

        if len(self.masters) > 1:

            readableCoord = None

            if hasattr(sender, 'spot'):
                if hasattr(self.w, 'spotSheet'):
                    self.w.spotSheet.close()
                spot = sender.spot
                ch, j = spot
                readableCoord = '%s%s'%(ch.upper(), j+1)

            hAxis, vAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
            self.w.generateSheet = Sheet((500, 250), self.w)
            generateSheet = self.w.generateSheet
            generateSheet.guide = TextBox((20, 20, -20, 22),
                u'A1, B2, C4 — A, C (whole columns) — 1, 5 (whole lines) — * (everything)',
                sizeStyle='small'
                )
            generateSheet.headerBar = HorizontalLine((20, 40, -20, 1))
            generateSheet.spotsListTitle = TextBox((20, 57, 70, 17), 'Locations')
            generateSheet.spots = EditText((100, 55, -20, 22))
            if readableCoord is not None:
                generateSheet.spots.set(readableCoord)

            generateSheet.sourceFontTitle = TextBox((20, 110, -290, 17), 'Source font (for naming & groups)', sizeStyle='small')
            generateSheet.sourceFontBar = HorizontalLine((20, 130, -290, 1))
            generateSheet.sourceFont = PopUpButton((20, 140, -290, 22), [fontName(masterFont) for spot, masterFont in self.masters], sizeStyle='small')

            generateSheet.options = TextBox((-270, 110, -20, 17), 'Interpolate', sizeStyle='small')
            generateSheet.optionsBar = HorizontalLine((-270, 130, -20, 1))
            generateSheet.kerning = CheckBox((-270, 140, -20, 22), 'Kerning', value=True, sizeStyle='small')
            generateSheet.fontInfos = CheckBox((-270, 160, -20, 22), 'Font infos', value=True, sizeStyle='small')

            generateSheet.report = CheckBox((20, -38, -20, 22), 'Add compatibility report', value=False, sizeStyle='small')

            generateSheet.yes = Button((-180, -40, 160, 20), 'Generate Instance(s)', self.getGenerationInfo)
            generateSheet.no = Button((-270, -40, 80, 20), 'Cancel', callback=self.cancelGeneration)
            generateSheet.open()

    def getGenerationInfo(self, sender):

        generateSheet = self.w.generateSheet

        if self.masters:
            availableFonts = AllFonts()
            mastersList = generateSheet.sourceFont.getItems()
            sourceFontIndex = generateSheet.sourceFont.get()
            sourceFontName = mastersList[sourceFontIndex]
            sourceFont = [masterFont for spot, masterFont in self.masters if fontName(masterFont) == sourceFontName and masterFont in availableFonts]

            spotsInput = generateSheet.spots.get()
            spotsList = self.parseSpotsList(spotsInput)

            generationInfos = {
                'sourceFont': sourceFont,
                'interpolateKerning': generateSheet.kerning.get(),
                'interpolateFontInfos': generateSheet.fontInfos.get(),
                'printReport': generateSheet.report.get()
            }

            # print ['%s%s'%(getKeyForValue(i).upper(), j+1) for i, j in spotsList]

        generateSheet.close()
        delattr(self.w, 'generateSheet')

        for spot in spotsList:
            self.generateInstanceFont(spot, generationInfos)

    def parseSpotsList(self, inputSpots):

        axesGrid = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        inputSpots = inputSpots.split(',')
        masterSpots = [(getValueForKey(ch),j) for (ch, j), masterFont in self.masters]
        spotsToGenerate = []

        if inputSpots[0] == '*':
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

        # self.w.spotSheet.close()
        # delattr(self.w, 'spotSheet')

        if generationInfos['sourceFont']:

            try:
                masters = self.masters
                baseFont = generationInfos['sourceFont'][0]
                folderPath = None
                s = re.search('(.*)/(.*)(.ufo)', baseFont.path)
                if s is not None:
                    folderPath = s.group(1)
                doKerning = generationInfos['interpolateKerning']
                doFontInfos = generationInfos['interpolateFontInfos']
                doReport = generationInfos['printReport']
                noUI = True

                progress = ProgressWindow('Generating instance', parentWindow=self.w)

                masterFonts = [font for _, font in masters]

                i, j = spot
                ch = getKeyForValue(i)
                instanceLocation = Location(horizontal=i, vertical=j)
                masterLocations = [(Location(horizontal=getValueForKey(_ch), vertical=_j), masterFont) for (_ch, _j), masterFont in masters]

                # Build font
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
                    path = '%s/%s-%s%s'%(folderPath, newFont.info.familyName, newFont.info.styleName, '.ufo')
                interpolatedGlyphs = []
                interpolatedInfo = None
                interpolatedKerning = None
                interpolationReports = []

                # interpolate font infos

                if doFontInfos:
                    infoMasters = [(infoLocation, MathInfo(masterFont.info)) for infoLocation, masterFont in masterLocations]
                    try:
                        bias, iM = buildMutator(infoMasters)
                        instanceInfo = iM.makeInstance(instanceLocation)
                        instanceInfo.extractInfo(newFont.info)
                    except:
                        pass

                # interpolate kerning

                if doKerning:
                    kerningMasters = [(kerningLocation, MathKerning(masterFont.kerning)) for kerningLocation, masterFont in masterLocations]
                    try:
                        bias, kM = buildMutator(kerningMasters)
                        instanceKerning = kM.makeInstance(instanceLocation)
                        instanceKerning.extractKerning(newFont)
                        for key, value in baseFont.groups.items():
                            newFont.groups[key] = value
                    except:
                        pass

                # filter compatible glyphs

                fontKeys = [set(masterFont.keys()) for masterFont in masterFonts]
                glyphList = set()
                for i, item in enumerate(fontKeys):
                    if i == 0:
                        glyphList = item
                    elif i > 0:
                        glyphList = glyphList & item

                incompatibleGlyphs = []

                for glyphName in glyphList:
                    glyphs = [(MathGlyph(masterFont[glyphName]), masterFont, masterLocation) for masterLocation, masterFont in masterLocations]
                    allCompatible = True
                    refMasterGlyph = glyphs[0][0]
                    refMasterFont = glyphs[0][1]
                    refMasterLocation = glyphs[0][2]
                    masterGlyphs = [(refMasterLocation, refMasterGlyph)]
                    for masterGlyph, _masterFont, _masterLocation in glyphs[1:]:
                        compatible = refMasterGlyph.isCompatible(masterGlyph)
                        if compatible == False:
                            incompatibleGlyphs.append((glyphName, refMasterFont, _masterFont))
                            allCompatible = False
                        elif compatible == True:
                            masterGlyphs.append((_masterLocation, masterGlyph))

                    if allCompatible:
                        try:
                            bias, gM = buildMutator(masterGlyphs)
                            newGlyph = RGlyph()
                            instanceGlyph = gM.makeInstance(instanceLocation)
                            interpolatedGlyphs.append((glyphName, instanceGlyph.extractGlyph(newGlyph)))
                        except:
                            continue

                for name, interpolatedGlyph in interpolatedGlyphs:
                    newFont.insertGlyph(interpolatedGlyph, name)

                progress.close()
                interpolationReports = []
                digest = []

                if doReport:
                    for glyphName, firstFont, secondFont in incompatibleGlyphs:
                        firstGlyph = firstFont[glyphName]
                        secondGlyph = secondFont[glyphName]
                        comp, report = firstGlyph.isCompatible(secondGlyph)
                        names = '%s <X> %s'%(fontName(firstFont), fontName(secondFont))
                        reportID = (name, report)
                        if reportID not in interpolationReports:
                            digest.append(names)
                            digest += [u'– %s'%(reportLine) for reportLine in report]
                            digest.append('\n')
                            interpolationReports.append(reportID)
                    print '\n'.join(digest)


                if hasattr(RFont, 'showUI') and (folderPath is None):
                    newFont.showUI()
                elif (folderPath is not None):
                    newFont.save(path)
                    f = RFont(path)
            except:
                try:
                    progress.close()
                except:
                    print u'Couldn’t finish generating, something happened…'
                    return

    def glyphPreviewCellSize(self, posSize, axesGrid):
        x, y, w, h = posSize
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = axesGrid
        w -= 50
        h -= 50
        cellWidth = w / nCellsOnHorizontalAxis
        cellHeight = h / nCellsOnVerticalAxis
        return cellWidth, cellHeight

    def pickSpot(self, sender):
        spot = sender.spot
        masterSpots = [_spot for _spot, masterFont in self.masters]
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
            spotSheet.generate = Button((20, -40, 150, 20), 'Generate Instance', callback=self.instanceGeneration)
            spotSheet.generate.spot = spot
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
        l = (spot, font)
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
        for matrixLocation in self.masters:
            masterSpot, masterFont = matrixLocation
            if spot == masterSpot:
                self.masters.remove(matrixLocation)
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
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnHorizontalAxis += 1
        if nCellsOnHorizontalAxis > 20:
            nCellsOnHorizontalAxis = 20
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
        for matrixLocation in self.masters:
            masterSpot, masterFont = matrixLocation
            ch, j = masterSpot
            i = getValueForKey(ch)
            if i >= nCellsOnHorizontalAxis:
                mastersToRemove.append(matrixLocation)
        for matrixLocation in mastersToRemove:
            self.masters.remove(matrixLocation)
        self.mutator = None
        self.updateMatrix()

    def addLine(self, sender):
        nCellsOnHorizontalAxis, nCellsOnVerticalAxis = self.axesGrid['horizontal'], self.axesGrid['vertical']
        nCellsOnVerticalAxis += 1
        if nCellsOnVerticalAxis > 20:
            nCellsOnVerticalAxis = 20
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
        for matrixLocation in self.masters:
            masterSpot, masterFont = matrixLocation
            ch, j = masterSpot
            if j >= nCellsOnVerticalAxis:
                mastersToRemove.append(matrixLocation)
        for matrixLocation in mastersToRemove:
            self.masters.remove(matrixLocation)
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
        pathToSave = PutFile()

    def loadMatrix(self, sender):
        pathToLoad = GetFile()

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
                currentGlyphName = None
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