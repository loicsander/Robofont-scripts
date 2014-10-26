#coding=utf-8

'''
Interpolation matrix implementing Erik van Blokland’s MutatorMath objects (https://github.com/LettError/MutatorMath)
in a grid/matrix, allowing for easy preview of inter/extrapolation behavior of letters while drawing in Robofont.
As the math are the same to Superpolator’s, the preview is as close as can be to Superpolator output,
although you don’t have as fine a coordinate system with this matrix (that can go up to 20x20).

(Will work only on Robofont from versions 1.6 onward)
'''

from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator
from fontMath.mathGlyph import MathGlyph
from fontMath.mathInfo import MathInfo
from fontMath.mathKerning import MathKerning

from vanilla import *
from robofab.interface.all.dialogs import PutFile, GetFile, GetFolder
from defconAppKit.controls.fontList import FontList
from defconAppKit.windows.progressWindow import ProgressWindow
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver
from AppKit import NSColor, NSThickSquareBezelStyle
from math import cos, sin, pi

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

        return previewGlyph
    return

def getValueForKey(ch):
    return 'abcdefghijklmnopqrstuvwxyz'.index(ch)

def getKeyForValue(i):
    A = 'abcdefghijklmnopqrstuvwxyz'
    return A[i]

def fontName(font):
    return ' '.join([font.info.familyName, font.info.styleName])

MasterColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.4, 0.1, 0.2, 1)
BlackColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 1)
Transparent = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0)

class InterpolationMatrixController:

    def __init__(self):
        bgColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(255, 255, 255, 255)
        buttonColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 255)
        self.w = Window((1000, 400), 'Interpolation Preview Matrix', minSize=(470, 300))
        self.w.getNSWindow().setBackgroundColor_(bgColor)
        self.w.glyphTitle = Box((10, 10, 200, 30))
        self.w.glyphName = TextBox((20, 15, 190, 20), 'No current glyph')
        # self.w.fontList = PopUpButton()
        self.axesGrid = {'horizontal': 3, 'vertical': 1}
        self.masters = []
        self.instanceSpots = []
        self.mutator = None
        self.currentGlyph = None
        self.buildMatrix((self.axesGrid['horizontal'], self.axesGrid['vertical']))
        self.w.addColumn = SquareButton((-80, 10, 30, 30), u'+', callback=self.addColumn)
        self.w.removeColumn = SquareButton((-115, 10, 30, 30), u'-', callback=self.removeColumn)
        self.w.addLine = SquareButton((-40, -40, 30, 30), u'+', callback=self.addLine)
        self.w.removeLine = SquareButton((-40, -70, 30, 30), u'-', callback=self.removeLine)
        for button in [self.w.addColumn, self.w.removeColumn, self.w.addLine, self.w.removeLine]:
            button.getNSButton().setBezelStyle_(10)
        self.w.clearMatrix = Button((220, 15, 70, 20), 'Clear', callback=self.clearMatrix)
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
        currentGlyph = self.getCurrentGlyph(notification)
        if currentGlyph is not None:
            self.w.glyphName.set(currentGlyph)
        elif currentGlyph is None:
            self.w.glyphName.set('No current glyph')
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
                        masters.append((l, masterGlyph))
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
                            instanceGlyph = mutator.makeInstance(instanceLocation)
                        except:
                            instanceGlyph = None
                    cell = getattr(matrix, '%s%s'%(ch, j))
                    cell.glyphView.setGlyph(instanceGlyph)

    def generateInstanceFont(self, sender):

        self.w.spotSheet.close()
        delattr(self.w, 'spotSheet')

        # progress = ProgressWindow('Generating instance', parentWindow=self.w)

        fonts = [font for spot, font in self.masters]

        ch, j = sender.spot
        i = getValueForKey(ch)
        instanceLocation = Location(horizontal=i, vertical=j)
        masterLocations = [(Location(horizontal=getValueForKey(ch), vertical=j), masterFont) for (ch, j), masterFont in self.masters]

        # Build font
        newFont = RFont(showUI=False)
        interpolatedGlyphs = []
        interpolatedInfo = None
        interpolatedKerning = None
        interpolationReports = []

        # interpolate font infos

        infoMasters = [(location, MathInfo(font.info)) for location, font in masterLocations]
        try:
            bias, iM = buildMutator(infoMasters)
            instanceInfo = iM.makeInstance(instanceLocation)
            instanceInfo.extractInfo(newFont.info)
        except:
            pass

        # interpolate kerning

        kerningMasters = [(location, MathKerning(font.kerning)) for location, font in masterLocations]
        try:
            bias, kM = buildMutator(kerningMasters)
            instanceKerning = kM.makeInstance(instanceLocation)
            instanceKerning.extractKerning(newFont)
            for key, value in fonts[0].groups.items():
                newFont.groups[key] = value
        except:
            pass

        # filter compatible glyphs

        fontKeys = [set(font.keys()) for font in fonts]
        glyphList = set()
        for i, item in enumerate(fontKeys):
            if i == 0:
                glyphList = item
            elif i > 0:
                glyphList = glyphList & item

        compatibleBaseGlyphList = []
        compatibleCompositeGlyphList = []

        for glyphName in glyphList:
            glyphs = [font[glyphName] for font in fonts]
            compatible = True
            for glyph in glyphs[1:]:
                comp, report = glyphs[0].isCompatible(glyph)
                if comp == False:
                    name = '%s <X> %s'%(fontName(glyphs[0].getParent()), fontName(glyph.getParent()))
                    reportLine = (name, report)
                    if reportLine not in interpolationReports:
                        interpolationReports.append(reportLine)
                    compatible = False
            if compatible:
                compatibleBaseGlyphList.append(glyphName)

        # initiate glyph interpolation

        for glyphName in compatibleBaseGlyphList:
            glyphMasters = [(location, MathGlyph(font[glyphName])) for location, font in masterLocations]
            try:
                bias, gM = buildMutator(glyphMasters)
                newGlyph = RGlyph()
                instanceGlyph = gM.makeInstance(instanceLocation)
                interpolatedGlyphs.append((glyphName, instanceGlyph.extractGlyph(newGlyph)))
            except:
                continue

        for name, iGlyph in interpolatedGlyphs:
            newFont.insertGlyph(iGlyph, name)

        # progress.close()
        digest = []

        for fontNames, report in interpolationReports:
            digest.append(fontNames)
            digest += [u'– %s'%(reportLine) for reportLine in report]
            digest.append('\n')
        print '\n'.join(digest)

        newFont.showUI()

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
        if spot in masterSpots:
            spotSheet.clear = Button((20, -40, 130, 20), 'Remove Master', callback=self.clearSpot)
        elif spot not in masterSpots:
            spotSheet.generate = Button((20, -40, 150, 20), 'Generate Instance', callback=self.generateInstanceFont)
        spotSheet.yes = Button((-120, -40, 100, 20), 'Add Master', callback=self.changeSpot)
        spotSheet.no = Button((-230, -40, 100, 20), 'Cancel', callback=self.keepSpot)
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

    def getCurrentGlyph(self, info=None):
        # if (info is not None) and (info.has_key('glyph')):
        #     currentGlyph = info['glyph']
        # elif (info is None) or (info is not None and not info.has_key('glyph')):
        currentGlyph = CurrentGlyph()

        if currentGlyph is None:
            currentGlyphName = None
        elif currentGlyph is not None:
            currentGlyphName = currentGlyph.name
        return currentGlyphName

    def windowResize(self, info):
        axesGrid = (nCellsOnHorizontalAxis, nCellsOnVerticalAxis) = (self.axesGrid['horizontal'], self.axesGrid['vertical'])
        posSize = info.getPosSize()
        cW, cH = self.glyphPreviewCellSize(posSize, axesGrid)
        matrix = self.w.matrix
        AB = 'abcdefghijklmnopqrstuvwxyz'

        for i in range(nCellsOnHorizontalAxis):
            ch = AB[i]
            for j in range(nCellsOnVerticalAxis):
                cell = getattr(matrix, '%s%s'%(ch,j))
                cell.setPosSize((i*cW, j*cH, cW, cH))

    def windowClose(self, notification):
        removeObserver(self, "currentGlyphChanged")
        removeObserver(self, "mouseUp")
        removeObserver(self, "keyUp")
        removeObserver(self, "fontDidClose")

InterpolationMatrixController()