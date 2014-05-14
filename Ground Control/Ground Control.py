
# Script written by Loic Sander — may 2014
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
from vanilla import *
from mojo.events import addObserver, removeObserver

# Global function that applies spacing modification on fonts
def modifyTracking(font, trackingValue):

	if font == myTypeBench.lastModifiedFont:
		return

	font.prepareUndo("modifyTracking")

	for glyph in font:
		glyph.leftMargin += trackingValue
		glyph.rightMargin += trackingValue

	font.performUndo()

	myTypeBench.lastModifiedFont = font	

def getFontName(font):
	return font.info.familyName + " " + font.info.styleName


def getFontByName(setOfFonts, fontName):

	for font in setOfFonts:
		if getFontName(font) == fontName:
			return font


# Class for each line/font in the window, hosting local parameters (which font is displayed, what tracking is applied on which line)
class BenchLine:
	
	def __init__(self, posSize, pointSize, lineHeight, trackingValuesList, allFontsList):
		self.benchLineHeight = posSize[3]
		self.pointSize = pointSize
		self.lineHeight = lineHeight
		self.localTrackingValue = 0
		self.trackingValuesList = trackingValuesList
		self.line = Group(posSize)
		self.lineIndex = 0
		self.displayModes = {'metrics': False, 'inverse': False, 'upsideDown': False}
		self.line.glyphView = MultiLineView(
		    (0, 0, 0, 0), 
		    pointSize = self.pointSize, 
		    lineHeight = self.lineHeight, 
		    doubleClickCallbak=None, 
		    applyKerning=True, 
		    bordered=False, 
		    hasHorizontalScroller=False, 
		    hasVerticalScroller=False, 
		    displayOptions= {'Waterfall':False}, 
		    selectionCallback=None,
		    menuForEventCallback=None)
		self.line.glyphView.setCanSelect(True)

		self.line.buttonToControls = Button((-45, 5, 35, 14), "+", callback=self.displayControls, sizeStyle="mini")
		self.line.buttonToSpaceCenter = Button((-85, 5, 35, 14), "SC", callback=self.toSpacecenter, sizeStyle="mini")

		self.line.controls = Group((-310, 41, 300, 50))
		self.line.controls.fontChoice = PopUpButton((5, 0, 0, 22), allFontsList, callback=self.switchFontCallback)
		self.line.controls.localTracking = PopUpButton((5, 28, 60, 22), trackingValuesList, callback=self.localTrackingCallback)
		self.line.controls.applyTrackingButton = Button((66, 28, 60, 22), "Apply", callback=self.applyTrackingCallback)
		self.line.controls.applyInvertButton = Button((-20, 28, 20, 22), "i", callback=self.displayNegative)
		self.line.controls.applyUpsideDownButton = Button((-65, 28, 40, 22), "u/n", callback=self.displayUpsideDown)
		self.line.controls.applyShowMetricsButton = Button((-100, 28, 30, 22), "m", callback=self.displayMetrics)

		self.line.controls.show(False)
		self.resetLocalTracking()

	def makeLine(self, font, glyphSet):
		self.setFont(font)
		self.line.glyphView._glyphLineView._font = self.font.naked()
		self.line.glyphView._glyphLineView.setItalicAngle()
		self.setGlyphs(glyphSet)
		return self.line

	def refreshLine(self, font, glyphSet):
		self.setFont(font)
		self.setGlyphs(glyphSet)
		self.resizeLine()

	def identify(self, index):
		self.lineIndex = index
		self.line.controls.fontChoice.set(index)
		
	def clearLine(self):
		self.line.glyphView.set([])
		return self.line.glyphView

	def setGlyphs(self, glyphSet):
		if isinstance(glyphSet[0], str) == True:
			self.getGlyphsByName(glyphSet)
		else:
			self.glyphSet = glyphSet
		self.line.glyphView.set(self.glyphSet)

	def setFont(self, font):
		self.font = font
		self.line.controls.fontChoice.setTitle(getFontName(font))
		# return self.line.glyphView
		
	def getGlyphsByName(self, glyphSet):
		self.glyphSet = [self.font[glyphSet[i]].naked() for i in range(len(glyphSet))]
		
	def switchFontCallback(self, sender):
		myTypeBench.changeFontOnLine(self.lineIndex, sender.getTitle())
		
	def hideControls(self):
	    self.line.controls.show(False)
	
	def showControls(self):
	    self.line.controls.show(True)

	def localTrackingCallback(self, sender):
		self.localTrackingValue = int(sender.getTitle())
		myTypeBench.displayTracking()

	def localTracking(self):
		return self.localTrackingValue

	def applyTrackingCallback(self, sender):
		self.applyTracking()

	def applyTracking(self):
		trackingValue = myTypeBench.globalTrackingValue + self.localTrackingValue

		modifyTracking(self.font, trackingValue)

		self.resetLocalTracking()
		myTypeBench.resetGlobalTracking()

	def resetLocalTracking(self):
		self.localTrackingValue = 0
		self.line.controls.localTracking.set(int(len(self.trackingValuesList)/2))

	def toSpacecenter(self, info):
		OpenSpaceCenter(self.font, False)
		CurrentSpaceCenter().set(myTypeBench.glyphSet)

	def displayControls(self, sender):
		if self.line.controls.isVisible():
			self.line.controls.show(False)
			self.line.buttonToControls.setTitle("+")
		else:
			self.line.controls.show(True)
			self.line.buttonToControls.setTitle("-")

	def displayNegative(self, sender):
		self.line.glyphView.setDisplayMode("Inverse")
		self.displayModes["inverse"] = not self.displayModes["inverse"]

	def displayUpsideDown(self, sender):
		self.line.glyphView.setDisplayMode("Upside Down")
		self.displayModes["upsideDown"] = not self.displayModes["upsideDown"]

	def displayMetrics(self, sender):
		self.line.glyphView.setDisplayMode("Show Metrics")	
		self.displayModes["metrics"] = not self.displayModes["metrics"]

	def updateFontList(self, fontList):
		self.line.controls.fontChoice.setItems(myTypeBench.allFontsList())

	def resizeLine(self):
		self.line.setPosSize(myTypeBench.linePosSize(self.lineIndex))


		
# Main class hosting the main window and global parameters	
class TypeBench:
	
	def __init__(self, glyphSet=["G","R","O","U","N","D","space","C","O","N","T","R","O","L"]):
		self.headerHeight = 42
		self.footerHeight = 28
		self.fonts = AllFonts()
		self.charMap = CurrentFont().getCharacterMapping()
		self.numberOfBenchLines = 9
		self.singleFontNumberOfBenchLines = 2
		self.fontsOnBench = []
		self.lastModifiedFont = None
		self.glyphSet = glyphSet
		self.pointSize = 100
		self.pointSizeList = ["36", "48", "56", "64", "72", "96", "128", "160", "192", "256", "364", "512"]
		self.line = ["firstLine", "secondLine", "thirdLine", "fourthLine", "fifthLine", "sixthLine", "seventhLine", "eighthLine", "ninthLine"]
		self.lineHeight = 150
		self.globalTrackingValue = 0
		self.localTrackingValues = []
		self.trackingValuesList = ["%+d" % i for i in range(-100, -60, 20)] + ["%+d" % i for i in range(-60, -30, 10)] + ["%+d" % i for i in range(-30, -10, 5)] + ["%+d" % i for i in range(-10, 10)] + ["%+d" % i for i in range(10, 30, 5)] + ["%+d" % i for i in range(30, 60, 10)] + ["%+d" % i for i in range(60, 120, 20)]

		self.w = Window((1440, 900), maxSize=(2880, 1800))
		self.buildBench()
		self.addControls()
		self.w.bind("resize", self.sizeUpdate)
		
	def buildBench(self):

		if (hasattr(self, 'multiLines') == False) or (len(self.multiLines) < 0):
			self.multiLines = [BenchLine((0, 0, 0, 0), self.pointSize, self.lineHeight, self.trackingValuesList, self.allFontsList()) for i in range(self.numberOfBenchLines)]

		if (len(self.fontsOnBench) == 0) and (len(AllFonts()) != 0):
			self.getAvailableFonts()

		if hasattr(self.w, "allLines") == False:
			self.w.allLines = Group((1, self.headerHeight, -1, -self.footerHeight))

		displayedFonts = len(self.fontsOnBench)

		if displayedFonts == 1:

			self.fontsOnBench = self.fontsOnBench * self.singleFontNumberOfBenchLines

			for i in range(self.singleFontNumberOfBenchLines):
				if hasattr(self.w.allLines, self.line[i]) == False:
					setattr(self.w.allLines, self.line[i], Group(self.linePosSize(i)))
					setattr(getattr(self.w.allLines, self.line[i]), "bench", self.multiLines[i].makeLine(self.fontsOnBench[i], self.glyphSet))
					self.multiLines[i].identify(i)
				else:
					self.multiLines[i].refreshLine(self.fontsOnBench[i], self.glyphSet)
		else:
			for i in range(displayedFonts):
				if displayedFonts > i:
					if hasattr(self.w.allLines, self.line[i]) == False:
						setattr(self.w.allLines, self.line[i], Group(self.linePosSize(i)))
						setattr(getattr(self.w.allLines, self.line[i]), "bench", self.multiLines[i].makeLine(self.fontsOnBench[i], self.glyphSet))
						self.multiLines[i].identify(i)
					else:
						self.multiLines[i].refreshLine(self.fontsOnBench[i], self.glyphSet)

		self.w.open()
		

	def addControls(self):

		self.w.headerControls = Group((0, 0, -0, self.headerHeight))
		self.w.footerControls = Group((0, -self.footerHeight, -0, self.footerHeight))

		self.w.headerControls.inputText = EditText((10, 10, -320, 22), callback=self.inputCallback)

		self.w.headerControls.pointSizePopUp = PopUpButton((-305, 10, 60, 22), self.pointSizeList, callback=self.pointSizePopUpCallback)
		self.w.headerControls.pointSizePopUp.set(6)

		self.w.headerControls.globalTrackingPopUp = PopUpButton((-175, 10, 60, 22), self.trackingValuesList, callback=self.trackingPopUpCallback)
		self.w.headerControls.globalTrackingPopUp.set(int(len(self.trackingValuesList)/2))

		self.w.headerControls.applyAllTrackingButton = Button((-110, 10, 100, 22), "Apply All", callback=self.ApplyAllTracking)

		self.w.footerControls.addLine = Button((-215, 7, 100, 14), "Add line", callback=self.addLineCallback, sizeStyle='mini')
		self.w.footerControls.removeLine = Button((-110, 7, 100, 14), "Remove line", callback=self.removeLineCallback, sizeStyle='mini')
		self.w.footerControls.addLine.enable(False)
		self.w.footerControls.removeLine.enable(False)

		
	def sizeUpdate(self, sender):

		for i in range(len(self.fontsOnBench)):
			line = getattr(sender.allLines, self.line[i])
			line.setPosSize(self.linePosSize(i))
		
	def linePosSize(self, index):
		self.benchLineHeight = ((self.w.getPosSize()[3] - (self.headerHeight + self.footerHeight)) / (len(self.fontsOnBench)))
		return (0, self.benchLineHeight * index, 0, self.benchLineHeight)
		
	def allFontsList(self):
		fontSetNames = []
		for font in AllFonts():
			fontSetNames.append(getFontName(font))
		return fontSetNames

	def addFontToBench(self, font):
		if font is None:
			font = self.fontsOnBench[-1]
		self.fontsOnBench.append(font)

	def getFontsOnBench(self):
		return self.fontsOnBench

	def inputCallback(self, sender):

		inputString = sender.get()

		if inputString == "":
			self.glyphSet = []
		elif len(inputString) < len(self.glyphSet):
			self.glyphSet = []
			for char in inputString:
				uni = ord(char)
				glyphName = self.charMap.get(uni)
				if glyphName:
					glyphName = glyphName[0]
				self.glyphSet.append(glyphName)
		else:
			char = inputString[-1]
			charMap = CurrentFont().getCharacterMapping()
			uni = ord(char)
			glyphName = charMap.get(uni)
			if glyphName:
				glyphName = glyphName[0]
			self.glyphSet.append(glyphName)

		for i in range(len(self.fontsOnBench)):
			self.multiLines[i].setGlyphs(self.glyphSet)

		
	def trackingPopUpCallback(self, sender):
		self.globalTrackingValue = int(sender.getTitle())
		self.displayTracking()

	def getlocalTracking(self):
		return [self.multiLines[i].localTrackingValue for i in range(len(self.fontsOnBench))]

	def displayTracking(self):
		localTrackingValues = self.getlocalTracking()
		globalTrackingValue = self.globalTrackingValue

		for i in range(len(self.fontsOnBench)):
			line = getattr(self.w.allLines, self.line[i])
			line.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[i])
			
	def pointSizePopUpCallback(self, sender):
		pointSize = int(sender.getTitle())

		for i in range(len(self.fontsOnBench)):
			line = getattr(self.w.allLines, self.line[i])
			line.bench.glyphView.setPointSize(pointSize)
			
	def changeFontOnLine(self, lineIndex, fontName):
		self.multiLines[lineIndex].setFont(getFontByName(AllFonts(), fontName))
		self.multiLines[lineIndex].setGlyphs(self.glyphSet)


	def ApplyAllTracking(self, sender):

		for i in range(len(self.fontsOnBench)):
			self.multiLines[i].applyTracking()
			self.multiLines[i].resetLocalTracking()

		self.resetGlobalTracking()

	def resetGlobalTracking(self):
		self.globalTrackingValue = 0
		self.displayTracking()
		self.w.headerControls.globalTrackingPopUp.set(int(len(self.trackingValuesList)/2))
		self.lastModifiedFont = None

	def resetWindow(self):
		self.multiLines = []

	def addLineCallback(self, sender):
		if (len(self.fontsOnBench) > 0) and (len(self.fontsOnBench) < self.numberOfBenchLines):
			self.addFontToBench(None)
			self.buildBench()
		else:
			return

	def removeLineCallback(self, sender):

		if len(self.fontsOnBench) > 0:
			self.fontsOnBench = self.fontsOnBench[:-1]

			self.buildBench()
		else:
			return

	def getAvailableFonts(self):
		allFonts = AllFonts()
		self.fontsOnBench = [allFonts[i] for i in range(len(allFonts)) if i < self.numberOfBenchLines]

myTypeBench = TypeBench()
