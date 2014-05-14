
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
		    selectionCallback=self.lineSelectionCallback,
		    menuForEventCallback=None)
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
		self.setGlyphs(glyphSet)
		return self.line

	def update(self, font, glyphSet):
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
		return self.line.glyphView
		
	def getGlyphsByName(self, glyphSet):
		self.glyphSet = [self.font[glyphSet[i]].naked() for i in range(len(glyphSet))]
		
	def switchFontCallback(self, sender):
		myTypeBench.changeFontOnLine(self.lineIndex, sender.get())
		
	def hideControls(self):
	    self.line.controls.show(False)
	
	def showControls(self):
	    self.line.controls.show(True)

	def localTrackingCallback(self, sender):
		self.localTrackingValue = int(sender.getTitle())
		myTypeBench.displayTracking()
		#self.setGlyphs(self.glyphSet)

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

	def lineSelectionCallback(self, info):
		if self.line.controls.isVisible():
			self.line.controls.show(False)
		else:
			self.line.controls.show(True)

	def displayNegative(self, sender):
		self.line.glyphView.setDisplayMode("Inverse")

	def displayUpsideDown(self, sender):
		self.line.glyphView.setDisplayMode("Upside Down")

	def displayMetrics(self, sender):
		self.line.glyphView.setDisplayMode("Show Metrics")	

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
		self.numberOfBenchLines = 6
		self.fontsOnBench = []
		self.lastModifiedFont = None
		self.glyphSet = glyphSet
		self.pointSize = 100
		self.pointSizeList = ["36", "48", "56", "64", "72", "96", "128", "160", "192", "256", "364", "512"]
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
		
		if (len(self.fontsOnBench) > 0):
			if hasattr(self.w.allLines, "firstLine") == False:
				self.w.allLines.firstLine = Group(self.linePosSize(0))
				self.w.allLines.firstLine.bench = self.multiLines[0].makeLine(self.fontsOnBench[0], self.glyphSet)
				self.multiLines[0].identify(0)
			else:
				self.multiLines[0].update(self.fontsOnBench[0], self.glyphSet)
		if (len(self.fontsOnBench) > 1):
			if hasattr(self.w.allLines, "secondLine") == False:
				self.w.allLines.secondLine = Group(self.linePosSize(1))
				self.w.allLines.secondLine.bench = self.multiLines[1].makeLine(self.fontsOnBench[1], self.glyphSet)
				self.multiLines[1].identify(1)
			else:
				self.multiLines[1].update(self.fontsOnBench[1], self.glyphSet)
		if (len(self.fontsOnBench) > 2):
			if hasattr(self.w.allLines, "thirdLine") == False:
				self.w.allLines.thirdLine = Group(self.linePosSize(2))
				self.w.allLines.thirdLine.bench = self.multiLines[2].makeLine(self.fontsOnBench[2], self.glyphSet)
				self.multiLines[2].identify(2)
			else:
				self.multiLines[2].update(self.fontsOnBench[2], self.glyphSet)
		if (len(self.fontsOnBench) > 3):
			if hasattr(self.w.allLines, "fourthLine") == False:
				self.w.allLines.fourthLine = Group(self.linePosSize(3))
				self.w.allLines.fourthLine.bench = self.multiLines[3].makeLine(self.fontsOnBench[3], self.glyphSet)
				self.multiLines[3].identify(3)
			else:
				self.multiLines[3].update(self.fontsOnBench[3], self.glyphSet)
		if (len(self.fontsOnBench) > 4):
			if hasattr(self.w.allLines, "fifthLine") == False:
				self.w.allLines.fifthLine = Group(self.linePosSize(4))
				self.w.allLines.fifthLine.bench = self.multiLines[4].makeLine(self.fontsOnBench[4], self.glyphSet)
				self.multiLines[4].identify(4)
			else:
				self.multiLines[4].update(self.fontsOnBench[4], self.glyphSet)
		if (len(self.fontsOnBench) > 5):
			if hasattr(self.w.allLines, "sixthLine") == False:
				self.w.allLines.sixthLine = Group(self.linePosSize(5))
				self.w.allLines.sixthLine.bench = self.multiLines[5].makeLine(self.fontsOnBench[5], self.glyphSet)
				self.multiLines[5].identify(5)
			else:
				self.multiLines[5].update(self.fontsOnBench[5], self.glyphSet)

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

		if (len(self.fontsOnBench) > 0):
			sender.allLines.firstLine.setPosSize(self.linePosSize(0))
		if (len(self.fontsOnBench) > 1):
			sender.allLines.secondLine.setPosSize(self.linePosSize(1))
		if (len(self.fontsOnBench) > 2):
			sender.allLines.thirdLine.setPosSize(self.linePosSize(2))
		if (len(self.fontsOnBench) > 3):
			sender.allLines.fourthLine.setPosSize(self.linePosSize(3))
		if (len(self.fontsOnBench) > 4):
			sender.allLines.fifthLine.setPosSize(self.linePosSize(4))
		if (len(self.fontsOnBench) > 5):
			sender.allLines.sixthLine.setPosSize(self.linePosSize(5))
		
	def linePosSize(self, index):
		self.benchLineHeight = ((self.w.getPosSize()[3] - (self.headerHeight + self.footerHeight)) / (len(self.fontsOnBench)))
		return (0, self.benchLineHeight * index, 0, self.benchLineHeight)
		
	def allFontsList(self):
		fontSetNames = []
		for i in range(len(AllFonts())):
			fontName = self.fonts[i].info.familyName + " " + self.fonts[i].info.styleName
			fontSetNames.append(fontName)
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

		if (len(self.fontsOnBench) > 0):
			self.w.allLines.firstLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[0])
		if (len(self.fontsOnBench) > 1):
			self.w.allLines.secondLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[1])
		if (len(self.fontsOnBench) > 2):
			self.w.allLines.thirdLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[2])
		if (len(self.fontsOnBench) > 3):
			self.w.allLines.fourthLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[3])
		if (len(self.fontsOnBench) > 4):
			self.w.allLines.fifthLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[4])
		if (len(self.fontsOnBench) > 5):
			self.w.allLines.sixthLine.bench.glyphView.setTracking(self.globalTrackingValue + localTrackingValues[5])

		for i in range(len(self.fontsOnBench)):
			self.multiLines[i].setGlyphs(self.glyphSet)
			
	def pointSizePopUpCallback(self, sender):
		pointSize = int(sender.getTitle())
		if (len(self.fontsOnBench) > 0):
			self.w.allLines.firstLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fontsOnBench) > 1):
			self.w.allLines.secondLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fontsOnBench) > 2):
			self.w.allLines.thirdLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fontsOnBench) > 3):
			self.w.allLines.fourthLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fontsOnBench) > 4):
			self.w.allLines.fifthLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fontsOnBench) > 5):
			self.w.allLines.sixthLine.bench.glyphView.setPointSize(pointSize)
			
	def changeFontOnLine(self, lineIndex, fontIndex):
		self.multiLines[lineIndex].setFont(self.fonts[fontIndex])
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
			print self.fontsOnBench
		else:
			return

	def removeLineCallback(self, sender):

		if len(self.fontsOnBench) > 0:
			self.fontsOnBench = self.fontsOnBench[:-1]
			self.buildBench()
			print self.fontsOnBench
		else:
			return

	def getAvailableFonts(self):
		allFonts = AllFonts()
		self.fontsOnBench = [allFonts[i] for i in range(len(allFonts)) if i < self.numberOfBenchLines]

myTypeBench = TypeBench()
