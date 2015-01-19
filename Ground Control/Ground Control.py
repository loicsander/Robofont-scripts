# -*- coding: utf8 -*-
GCVersion = "1.01"

# Script written by Loïc Sander — may 2014
# update 10 july 2014

# Based on mojo.UI’s MultiLineView

# Opens a window displaying all open fonts up to 6
# Fonts are displayed in line, displaying the same glyphs or text, defined in the input
# Can be used to simply compare letterforms on different masters/instances
# Also features modification of tracking on each font separately and on all of them at once
# The global tracking and local tracking on each line are additive
# for example:
# If you define a +10 units tracking on a global scale
# and add a -6 units tracking on the third fond displayed
# if you hit the [Apply All] button, all fonts will be applied a +10 units tracking except the third, which will be applied a +10-6 = 4 tracking
# More simply put: you get what you see.
# Alternatively, you can apply tracking on a single line/font, but bear in mind that tracking on this font will also be an addition of global and local tracking

from mojo.UI import *
from mojo.events import addObserver, removeObserver
from vanilla import *
from defconAppKit.tools.textSplitter import splitText
from AppKit import NSColor, NSEvent

class BenchToolBox:

    def __init__(self):
        self.lastModifiedFont = None

    def getFontName(self, font):
        if font is not None:
            if (font.info.familyName != None) and (font.info.styleName != None):
                return font.info.familyName + " " + font.info.styleName
            else:
                return "* Unamed Font"
        else:
            return ""
            print "toolBox.getFontName: No Font provided"

    def getFontByName(self, setOfFonts, fontName):

        for font in setOfFonts:
            if self.getFontName(font) == fontName:
                return font

    def modifyTracking(self, font, trackingValue, glyphSet=None):

        if (myTypeBench.lastModifiedFont is None) or (self.getFontName(font) != self.getFontName(myTypeBench.lastModifiedFont)):

            font.prepareUndo("modifyTracking")

            if glyphSet == None:
                for glyph in font:
                    glyph.leftMargin += trackingValue / 2
                    glyph.rightMargin += trackingValue / 2

                    if len(glyph.components) > 0:
                        for component in glyph.components:
                            component.move(((-trackingValue / 2), 0))

            font.performUndo()

            myTypeBench.lastModifiedFont = font


class BenchLine:

    def __init__(self, index):
        self.index = index
        self.font = None
        self.selected = False
        self.showControls = False
#        self.selectedGlyph = None
        self.localTrackingValue = 0
        self.line = Group((0, 0, 0, 0))
        self.line.view = MultiLineView(
                (0, 0, 0, 0),
                pointSize = 128,
                lineHeight = 100,
                doubleClickCallback = None,
                applyKerning = True,
                bordered = False,
                hasHorizontalScroller = False,
                hasVerticalScroller = False,
                displayOptions = {'Waterfall':False},
                selectionCallback = self.selectionCallback,
                menuForEventCallback = None
                )
        self.line.view.setCanSelect(True)

        self.line.controlsToggle = Button((-45, 5, 35, 14), "+", callback=self.toggleControlsCallback, sizeStyle="mini")
        self.line.controls = Group((-310, 41, 300, 50))
        self.line.controls.fontChoice = PopUpButton((5, 0, 0, 22), [], callback=self.switchFontCallback)
        self.line.controls.localTracking = PopUpButton((5, 28, 60, 22), [], callback=self.localTrackingCallback)
        self.line.controls.applyTrackingButton = Button((70, 28, 60, 22), "Apply", callback=self.applyTrackingCallback)
        self.line.controls.toSpaceCenterButton = Button((-80, -18, 80, 18), "Space Center", sizeStyle="mini", callback=self.toSpacecenter)

        self.toggleControls(False)

    # Send back line to be displayed

    def display(self):
        return self.line

    # Set/Update ComboBoxes (font list & tracking values)

    def setFontCombo(self, allFontsList):
        self.line.controls.fontChoice.setItems(allFontsList)
        if self.font is not None:
            self.line.controls.fontChoice.setTitle(toolBox.toolBox.getFontName(self.font))
            self.line.glyphView._glyphLineView._font = self.font.naked()
            self.line.glyphView._glyphLineView.setItalicAngle()

    def setTrackingCombo(self, trackingValuesList):
        self.line.controls.localTracking.setItems(trackingValuesList)
        self.line.controls.localTracking.setTitle("+0")

    # Local Font settings

    def setFont(self, font):
        if font is not None:
            self.font = font
            self.line.controls.fontChoice.setTitle(benchToolBox.getFontName(font))
            self.line.view._glyphLineView._font = self.font.naked()
            self.line.view._glyphLineView.setItalicAngle()

    def switchFontCallback(self, sender):
        fontName = sender.getTitle()
        self.setFont(benchToolBox.getFontByName(AllFonts(), fontName))
        self.setGlyphs(myTypeBench.glyphSet)
        myTypeBench.fontsOnBench[self.index] = benchToolBox.getFontByName(AllFonts(), fontName)
        myTypeBench.checkSimilarity()

    # about Glyphs

    def setGlyphs(self, glyphSet):
        if glyphSet != []:
            if isinstance(glyphSet[0], str) or isinstance(glyphSet[0], unicode):
                self.getGlyphsByName(glyphSet)
            else:
                self.glyphSet = glyphSet
            self.line.view.set(self.glyphSet)
        else:
            self.line.view.set([])

    def getGlyphsByName(self, glyphSet):
        # check if name is a valid glyphName
        # converts a set of glyph names to a set of glyphs of the local font
        self.glyphSet = []
        glyph = None
        for glyphName in glyphSet:
            if (glyphName == u'?') and (CurrentGlyph() is not None):
                glyphName = CurrentGlyph().name
            if glyphName in self.font.keys():
                glyph = self.font[glyphName].naked()
            if glyph is not None:
                self.glyphSet.append(glyph)

    # Local Tracking

    def localTrackingCallback(self, sender):
        self.localTrackingValue = int(sender.getTitle())
        myTypeBench.displayTracking()

    def applyTrackingCallback(self, sender):
        self.applyTracking()

    def applyTracking(self):
        trackingValue = myTypeBench.globalTrackingValue + self.localTrackingValue

        benchToolBox.modifyTracking(self.font, trackingValue)

        self.resetLocalTracking()
        myTypeBench.resetGlobalTracking()

    def resetLocalTracking(self):
        self.localTrackingValue = 0
        self.line.controls.localTracking.setTitle("+0")
        self.setGlyphs(myTypeBench.glyphSet)

    # Selection callback

    def selectionCallback(self, multiLineView):

        if (multiLineView._glyphLineView.getSelected() is None):
            self.selected = not self.selected

        if (self.selected == True) or (multiLineView._glyphLineView.getSelected() is not None):
            myTypeBench.selectedLine = self.index
            myTypeBench.onSelectionUpdate()
        elif self.selected == False:
            myTypeBench.selectedLine = None
            myTypeBench.onSelectionUpdate()

        if (multiLineView._glyphLineView.getSelected() is not None) and (NSEvent.modifierFlags() & NSAlternateKeyMask):
            OpenGlyphWindow(self.font[multiLineView._glyphLineView.getSelected().name], False)

    def setColor(self, color):
        self.line.view._glyphLineView._glyphColor = color

    def toSpacecenter(self, info):
        OpenSpaceCenter(self.font, False)
        CurrentSpaceCenter().set(myTypeBench.glyphSet)

    def toggleControlsCallback(self, sender):
        self.showControls = not self.showControls
        self.toggleControls(self.showControls)

    def toggleControls(self, boolean):
        if boolean == False:
            self.line.controlsToggle.setTitle("+")
        elif boolean == True:
            self.line.controlsToggle.setTitle("-")
        self.line.controls.show(boolean)


class GroundControl:

    def __init__(self):

        if len(AllFonts()) == 0:
            print "Please open at least one font before using Ground Control"
            return

        # [windowWidth, maxWindowWidth, minWindowWidth]
        self.xDimensions = [1200, 2880, 400]
        # [windowHeight, maxWindowHeight, minWindowHeight headerHeight, footerHeight]
        self.yDimensions = [600, 1800, 400, 50, 28]
        self.allLinesHeight = self.yDimensions[0] - (self.yDimensions[3] + self.yDimensions[4])
        self.lineNames = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]
        self.pointSizeList = ["36", "48", "56", "64", "72", "96", "128", "160", "192", "256", "364", "512"]
        self.trackingValuesList = ["%+d" % i for i in range(-100, -60, 20)] + ["%+d" % i for i in range(-60, -30, 10)] + ["%+d" % i for i in range(-30, -10, 6)] + ["%+d" % i for i in range(-10, 10, 2)] + ["%+d" % i for i in range(10, 30, 6)] + ["%+d" % i for i in range(30, 60, 10)] + ["%+d" % i for i in range(60, 120, 20)]
        self.fontsOnBench = []
        self.charMap = CurrentFont().getCharacterMapping()
        self.glyphSet = ["A", "B", "C"]
        self.lastModifiedFont = None
        self.globalTrackingValue = 0
        self.minNumberOfLines = 2
        self.maxNumberOfLines = 9
        self.selectedLine = None
        self.showAllControls = False
        self.displaySettings = {"Show Metrics": [[False, False] for i in range(self.maxNumberOfLines)], "Inverse": [[False, False] for i in range(self.maxNumberOfLines)], "Upside Down": [[False, False] for i in range(self.maxNumberOfLines)]}
        self.baseColor = NSColor.blackColor()
        self.selectionColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(.3, .1, .1, 0.8)

        self.w = Window((self.xDimensions[0], self.yDimensions[0]), "Ground Control " + GCVersion, maxSize=(self.xDimensions[1], self.yDimensions[1]), minSize=(self.xDimensions[2], self.yDimensions[2]))
        self.w.header = Group((0, 0, -0, self.yDimensions[3]))
        self.w.allLines = Group((0, self.w.header.getPosSize()[3], -0, self.allLinesHeight))
        self.w.footer = Group((0, -self.yDimensions[4], -0, self.yDimensions[4]))

        import os
        if os.path.isfile("GroundControlPrefList.txt"):
            with open("GroundControlPrefList.txt") as myfile:
                prefList = myfile.read().split("\n")
        else:
            prefList = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "HHH0HHH00HHH000HHH", "nnnonnnoonnnooonnn"]

        self.w.header.inputText = ComboBox((10, 10, -320, 22),
            prefList,
            continuous = True,
            completes = True,
            callback = self.inputCallback)
        self.w.header.pointSizePopUp = PopUpButton((-305, 10, 60, 22), self.pointSizeList, callback=self.pointSizePopUpCallback)
        self.w.header.pointSizePopUp.setTitle("128")
        self.w.header.globalTrackingPopUp = PopUpButton((-175, 10, 60, 22), self.trackingValuesList, callback=self.trackingPopUpCallback)
        self.w.header.globalTrackingPopUp.setTitle("+0")
        self.w.header.applyAllTrackingButton = Button((-110, 10, 100, 22), "Apply All", callback=self.ApplyAllTracking)

        self.w.footer.toggleAllControlsButton = Button((-260, 7, 100, 14), "All Controls", sizeStyle="mini", callback=self.toggleAllLineControlsCallback)
        self.w.footer.addLineButton = Button((-135, 7, 60, 14), "Add", sizeStyle="mini", callback=self.addBenchLine)
        self.w.footer.removeLineButton = Button((-70, 7, 60, 14), "Remove", sizeStyle="mini", callback=self.removeLastBenchLine)
        self.w.footer.options = Group((10, 5, -260, 18))
        self.w.footer.options.fontName = TextBox((0, 2, 50, 18), "All", sizeStyle="small")
        self.w.footer.options.showMetrics = CheckBox((50, 0, 90, 18), "Show Metrics", sizeStyle="small", callback=self.showMetricsCallback)
        self.w.footer.options.inverse = CheckBox((150, 0, 60, 18), "Inverse", sizeStyle="small", callback=self.inverseCallback)
        self.w.footer.options.upsideDown = CheckBox((220, 0, 90, 18), "Flip", sizeStyle="small", callback=self.flipCallback)

        index = 0

        for lineName in self.lineNames:

            # One part of the object is Methods & Attributes
            setattr(self.w.allLines, lineName + "MethAttr", BenchLine(index))
            thisLineMethAttr = getattr(self.w.allLines, lineName + "MethAttr")

            # The second part of the object corresponds to the Vanilla objects, MultiLineView, buttons and such
            setattr(self.w.allLines, lineName + "Vanillas", thisLineMethAttr.display())
            thisLineVanillas = getattr(self.w.allLines, lineName + "Vanillas")

            thisLineVanillas.show(False)
            thisLineMethAttr.setFontCombo(self.allFontsList())
            thisLineMethAttr.setTrackingCombo(self.trackingValuesList)
            index += 1

        self.getFontsOnBench()
        self.setBench()

        addObserver(self, "_currentGlyphChanged", "currentGlyphChanged")
        addObserver(self, "updateCurrentGlyphInView", "keyDown")
        addObserver(self, "updateCurrentGlyphInView", "mouseDown")
        addObserver(self, "updateCurrentGlyphInView", "mouseDragged")
        addObserver(self, "updateFontsCallback", "fontDidOpen")
        addObserver(self, "updateFontsCallback", "fontDidClose")
        self.w.bind("resize", self.resizeWindowCallback)
        self.w.open()

    # Main function, setting lines, glyphset and fonts

    def setBench(self):

        self.w.allLines.resize(-0, self.allLinesHeight)

        displayedFonts = len(self.fontsOnBench)
        if displayedFonts == 0:
            displayedFonts = self.minNumberOfLines
        benchLineHeight = self.allLinesHeight / displayedFonts

        for i in range(self.maxNumberOfLines):

            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            thisLineVanillas = getattr(self.w.allLines, self.lineNames[i] + "Vanillas")

            if i < displayedFonts:
                thisLineVanillas.setPosSize((0, (benchLineHeight * i), -0, benchLineHeight))
                thisLineVanillas.show(True)

                if len(self.fontsOnBench) != 0:
                    thisLineMethAttr.setFont(self.fontsOnBench[i])
                    thisLineMethAttr.setGlyphs(self.glyphSet)
                    thisLineVanillas.controls.fontChoice.setItems(self.allFontsList())
                    thisLineVanillas.controls.fontChoice.setTitle(benchToolBox.getFontName(self.fontsOnBench[i]))
                    thisLineMethAttr.toggleControls(self.showAllControls)

            elif i >= displayedFonts:
                thisLineVanillas.setPosSize((0, 0, 0, 0))
                thisLineVanillas.show(False)

        for modes in self.displaySettings.keys():
            self.updateDisplaySetting(modes)

        if len(self.fontsOnBench) == self.maxNumberOfLines:
            self.w.footer.addLineButton.enable(False)
        elif len(self.fontsOnBench) < self.maxNumberOfLines:
            self.w.footer.addLineButton.enable(True)

        if len(self.fontsOnBench) == self.minNumberOfLines:
            self.w.footer.removeLineButton.enable(False)
        elif len(self.fontsOnBench) > self.minNumberOfLines:
            self.w.footer.removeLineButton.enable(True)

        self.checkSimilarity()

    # If all fonts on bench are the same, deactivate the [Apply all] (tracking) button

    def checkSimilarity(self):

        previousFont = None
        sameFonts = False

        for i in range(len(self.fontsOnBench)):

            if self.fontsOnBench[i] == previousFont:
                sameFonts = True
            else:
                sameFonts = False

            previousFont = self.fontsOnBench[i]

        if sameFonts == True:
            self.w.header.applyAllTrackingButton.enable(False)
        else:
            self.w.header.applyAllTrackingButton.enable(True)


    # Add/Remove lines

    def addBenchLine(self, sender):
        if len(self.fontsOnBench) < self.maxNumberOfLines:
            self.fontsOnBench.append(self.fontsOnBench[-1:][0])
            self.setBench()

    def removeLastBenchLine(self, sender):
        if len(self.fontsOnBench) > self.minNumberOfLines:
            self.fontsOnBench = self.fontsOnBench[:-1]
            self.setBench()

    def removeBenchLine(self, index):
        if len(self.fontsOnBench) > self.minNumberOfLines:
            del self.fontsOnBench[index]
            self.setBench()
        elif len (self.fontsOnBench) == self.minNumberOfLines:
            del self.fontsOnBench[index]
            self.fontsOnBench.append(self.fontsOnBench[-1:][0])
            self.setBench()

    # Controls

    def toggleAllLineControlsCallback(self, sender):
        self.showAllControls = not self.showAllControls
        for i in range(len(self.fontsOnBench)):
            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            thisLineMethAttr.toggleControls(self.showAllControls)

    # Get names of all available fonts

    def allFontsList(self):
        allAvailableFonts = []
        for font in AllFonts():
            allAvailableFonts.append(benchToolBox.getFontName(font))
        return allAvailableFonts

    # Define fonts to be displayed by default: first definition of self.fontsOnBench
    # Afterwards, self.fontsOnBench is modified by the user interacting through the fontChoice comboBoxes

    def getFontsOnBench(self):
        allFonts = AllFonts()

        if len(allFonts) == 1:
            self.fontsOnBench = [allFonts[0], allFonts[0]]
        elif len(allFonts) > 1:
            self.fontsOnBench = [allFonts[i] for i in range(len(allFonts)) if i < self.maxNumberOfLines]

    # Point size

    def pointSizePopUpCallback(self, sender):
        pointSize = int(sender.getTitle())

        for i in range(len(self.fontsOnBench)):
            thisLineVanillas = getattr(self.w.allLines, self.lineNames[i] + "Vanillas")
            thisLineVanillas.view.setPointSize(pointSize)

    # Tracking…

    def trackingPopUpCallback(self, sender):
        self.globalTrackingValue = int(sender.getTitle())
        self.displayTracking()

    def displayTracking(self):
        localTrackingValues = self.getlocalTracking()
        globalTrackingValue = self.globalTrackingValue

        for i in range(len(self.fontsOnBench)):
            thisLineVanillas = getattr(self.w.allLines, self.lineNames[i] + "Vanillas")
            thisLineVanillas.view.setTracking(self.globalTrackingValue + localTrackingValues[i])

    def getlocalTracking(self):
        return [getattr(getattr(self.w.allLines, self.lineNames[i] + "MethAttr"), "localTrackingValue") for i in range(len(self.fontsOnBench))]

    def resetGlobalTracking(self):
        self.globalTrackingValue = 0
        self.displayTracking()
        self.w.header.globalTrackingPopUp.setTitle("+0")
        self.lastModifiedFont = None

    def ApplyAllTracking(self, sender):

        for i in range(len(self.fontsOnBench)):

            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            trackingValue = self.globalTrackingValue + thisLineMethAttr.localTrackingValue

            print self.globalTrackingValue

            benchToolBox.modifyTracking(thisLineMethAttr.font, trackingValue)

            thisLineMethAttr.resetLocalTracking()

        self.resetGlobalTracking()

    # BenchLine Selection

    def onSelectionUpdate(self):
        for i in range(len(self.fontsOnBench)):
            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            if i != self.selectedLine:
                thisLineMethAttr.selected = False
                thisLineMethAttr.setColor(self.baseColor)
                thisLineMethAttr.setGlyphs(self.glyphSet)
            elif (i == self.selectedLine) and (thisLineMethAttr.line.view._glyphLineView._glyphColor != self.selectionColor):
                thisLineMethAttr.setColor(self.selectionColor)
                thisLineMethAttr.setGlyphs(self.glyphSet)

        self.footerOptions()

    # Responsive stuff

    def resizeWindowCallback(self, sender):

        if self.w.getPosSize()[2] < 600:
            self.footerOptions()
            self.w.footer.toggleAllControlsButton.show(False)
            self.w.footer.addLineButton.setTitle("+")
            self.w.footer.addLineButton.setPosSize((-75, 7, 30, 14))
            self.w.footer.removeLineButton.setTitle("-")
            self.w.footer.removeLineButton.setPosSize((-40, 7, 30, 14))

            for i in range(len(self.fontsOnBench)):
                thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
                thisLineMethAttr.toggleControls(False)

        elif self.w.getPosSize()[2] >= 600:
            self.footerOptions()
            self.w.footer.toggleAllControlsButton.show(True)
            self.w.footer.addLineButton.setTitle("Add")
            self.w.footer.addLineButton.setPosSize((-135, 7, 60, 14))
            self.w.footer.removeLineButton.setTitle("Remove")
            self.w.footer.removeLineButton.setPosSize((-70, 7, 60, 14))

        self.allLinesHeight = self.w.getPosSize()[3] - (self.yDimensions[3] + self.yDimensions[4])
        self.setBench()

    def footerOptions(self):

        if self.w.getPosSize()[2] < 600:

            self.w.footer.options.resize(-75, 18)
            self.w.footer.options.fontName.show(False)
            self.w.footer.options.showMetrics.setPosSize((0, 0, 90, 18))
            self.w.footer.options.inverse.setPosSize((100, 0, 60, 18))
            self.w.footer.options.upsideDown.setPosSize((170, 0, 90, 18))

        elif self.w.getPosSize()[2] >= 600:

            self.w.footer.options.fontName.show(True)

            if self.selectedLine is not None:
                self.w.footer.options.showMetrics.set(self.displaySettings["Show Metrics"][self.selectedLine][0])
                self.w.footer.options.inverse.set(self.displaySettings["Inverse"][self.selectedLine][0])
                self.w.footer.options.upsideDown.set(self.displaySettings["Upside Down"][self.selectedLine][0])

                fontName = benchToolBox.getFontName(self.fontsOnBench[self.selectedLine])
                fontNameWidth = len(fontName) * 8

                self.w.footer.options.fontName.resize(fontNameWidth, 18)
                self.w.footer.options.showMetrics.setPosSize((fontNameWidth + 10, 0, 90, 18))
                self.w.footer.options.inverse.setPosSize((fontNameWidth + 110, 0, 60, 18))
                self.w.footer.options.upsideDown.setPosSize((fontNameWidth + 180, 0, 90, 18))

                self.w.footer.options.fontName.set(str(self.selectedLine + 1) + ": " + fontName)
                str(self.selectedLine + 1)

            else:
                self.w.footer.options.fontName.set("All")
                self.w.footer.options.showMetrics.setPosSize((50, 0, 90, 18))
                self.w.footer.options.inverse.setPosSize((150, 0, 60, 18))
                self.w.footer.options.upsideDown.setPosSize((220, 0, 90, 18))

    # Display Settings, Show Metrics, Inverse (white on black), Flip (upside down)

    def updateDisplaySetting(self, mode):

        for i in range(len(self.fontsOnBench)):

            if self.displaySettings[mode][i][0] != self.displaySettings[mode][i][1]:

                if (self.selectedLine is not None) and (i != self.selectedLine):
                    continue

                thisLineVanillas = getattr(self.w.allLines, self.lineNames[i] + "Vanillas")
                thisLineVanillas.view.setDisplayMode(mode)
                self.displaySettings[mode][i][1] = self.displaySettings[mode][i][0]

    def updateDisplaySettingCallback(self, mode, boolValue):

        boolean = bool(boolValue)
        self.onSelectionUpdate()

        for i in range(self.maxNumberOfLines):
            if (self.selectedLine is not None) and (i != self.selectedLine):
                continue
            self.displaySettings[mode][i][0] = boolean
        self.onSelectionUpdate()
        self.updateDisplaySetting(mode)

    def showMetricsCallback(self, sender):
        self.updateDisplaySettingCallback("Show Metrics", sender.get())

    def inverseCallback(self, sender):
        self.updateDisplaySettingCallback("Inverse", sender.get())

    def flipCallback(self, sender):
        self.updateDisplaySettingCallback("Upside Down", sender.get())

    # Text input & parsing

    def inputCallback(self, sender):

        typedString = sender.get()

        self.glyphSet = splitText(typedString, self.charMap)

        for i in range(len(self.fontsOnBench)):
            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            thisLineMethAttr.setGlyphs(self.glyphSet)

    # Observer callbacks

    def windowClose(self, sender):
        removeObserver(self, "fontDidOpen")
        removeObserver(self, "fontDidClose")
        removeObserver(self, "currentGlyphChanged")
        removeObserver(self, "mouseDown")
        removeObserver(self, "keyDown")
        removeObserver(self, "mouseDragged")

    def _currentGlyphChanged(self, notification):
        if ((notification['notificationName'] == 'currentGlyphChanged') and (CurrentGlyph() is not None) and (u"?" in self.glyphSet)) or\
           (notification['notificationName'] in ['mouseDragged', 'keyDown', 'mouseDown']):
            for i in range(len(self.fontsOnBench)):
                thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
                thisLineMethAttr.setGlyphs(self.glyphSet)

    def updateCurrentGlyphInView(self, notification):
        glyph = notification['glyph']
        if (notification['notificationName'] == 'mouseDragged') and (len(glyph.selection) == 0):
            return
        self._currentGlyphChanged(notification)

    def updateFontsCallback(self, info):

        for i in range(len(self.fontsOnBench)):
            thisLineMethAttr = getattr(self.w.allLines, self.lineNames[i] + "MethAttr")
            thisLineVanillas = getattr(self.w.allLines, self.lineNames[i] + "Vanillas")

            if (info["notificationName"] == "fontDidClose") and (benchToolBox.getFontByName(AllFonts(), benchToolBox.getFontName(thisLineMethAttr.font)) == None):
                self.removeBenchLine(i)
                continue

            thisLineVanillas.controls.fontChoice.setItems(self.allFontsList())
            thisLineVanillas.controls.fontChoice.setTitle(benchToolBox.getFontName(thisLineMethAttr.font))

benchToolBox = BenchToolBox()
myTypeBench = GroundControl()