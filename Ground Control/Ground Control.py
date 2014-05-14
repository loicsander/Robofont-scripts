from mojo.UI import *
from vanilla import *
from mojo.events import addObserver, removeObserver

def modifyTracking(font, trackingValue):

	font.prepareUndo("modifyTracking")

	for glyph in font:
		glyph.leftMargin += trackingValue
		glyph.rightMargin += trackingValue

	font.performUndo()

class BenchLine:
	
	def __init__(self, posSize, pointSize, lineHeight, fontList, trackingList):
		self.benchLineHeight = posSize[3]
		self.pointSize = pointSize
		self.lineHeight = lineHeight
		self.localTrackingValue = 0
		self.trackingList = trackingList
		self.line = Group(posSize)
		self.line.glyphView = MultiLineView(
		    (0, 0, 0, 0), 
		    pointSize = self.pointSize, 
		    lineHeight = self.lineHeight, 
		    doubleClickCallbak=None, 
		    applyKerning=None, 
		    bordered=False, 
		    hasHorizontalScroller=False, 
		    hasVerticalScroller=False, 
		    displayOptions= {'Waterfall':False}, 
		    selectionCallback=None, 
		    menuForEventCallback=None)
		self.line.controls = Group((-310, self.lineHeight - 22, 300, 50))
		self.line.controls.fontChoice = PopUpButton((5, 0, 0, 22), fontList, callback=self.switchFontCallback)
		self.line.controls.localTracking = PopUpButton((5, 28, 145, 22), trackingList, callback=self.localTrackingCallback)
		self.line.controls.applyTrackingButton = Button((155, 28, 145, 22), "Apply", callback=self.applyTrackingCallback)

		self.resetLocalTracking()

	def identify(self, index):
		self.lineIndex = index
		self.line.controls.fontChoice.set(index)
		
	def clearLine(self):
		self.line.glyphView.set([])
		return self.line.glyphView

	def setGlyphs(self, glyphSet):
		self.getGlyphsByName(glyphSet)
		self.line.glyphView.set(self.glyphSet)

	def setFont(self, font):
		self.font = font
		return self.line.glyphView
		
	def display(self, font, glyphSet):
		self.line.glyphView.setFont(font)
		self.font = font
		self.setGlyphs(glyphSet)
		return self.line
		
	def getGlyphsByName(self, glyphSet):
		self.glyphSet = [self.font[glyphSet[i]] for i in range(len(glyphSet))]
		
	def switchFontCallback(self, sender):
		myTypeBench.changeFontOnLine(self.lineIndex, sender.get())
		
	def hideControls(self):
	    self.line.controls.show(False)
	
	def showControls(self):
	    self.line.controls.show(True)

	def localTrackingCallback(self, sender):
		self.localTrackingValue = int(sender.getTitle())
		myTypeBench.setTracking()

	def localTracking(self):
		return self.localTrackingValue

	def applyTrackingCallback(self, sender):
		self.applyTracking()

	def applyTracking(self):
		trackingValue = myTypeBench.globalTrackingValue + self.localTrackingValue

		modifyTracking(self.font, trackingValue)

		self.resetLocalTracking()

	def resetLocalTracking(self):
		self.localTrackingValue = 0
		self.line.controls.localTracking.set(int(len(self.trackingList)/2))

		
		
class TypeBench:
	
	def __init__(self, glyphSet=["G","R","O","U","N","D","space","C","O","N","T","R","O","L"]):
		self.headerHeight = 42
		self.fonts = AllFonts()
		self.glyphSet = glyphSet
		self.pointSize = 100
		self.pointSizeList = ["36", "48", "56", "64", "72", "96", "128", "160", "192", "256", "364", "512"]
		self.lineHeight = 50
		self.globalTrackingValue = 0
		self.localTracking = []
		self.trackingSteps = 10
		self.trackingSpan = 200 #in both positive and negative directions
		self.trackingList = ["%+d" % i for i in range(-100, -60, 20)] + ["%+d" % i for i in range(-60, -30, 10)] + ["%+d" % i for i in range(-30, -10, 5)] + ["%+d" % i for i in range(-10, 10)] + ["%+d" % i for i in range(10, 30, 5)] + ["%+d" % i for i in range(30, 60, 10)] + ["%+d" % i for i in range(60, 120, 20)]

		self.w = FloatingWindow((1440, 900), maxSize=(2880, 1800))
		self.buildBench()
		self.addControls()
		self.w.bind("resize", self.sizeUpdate)
		self.w.open()
	
		
	def buildBench(self):
		
		fontList = self.fontList()
		self.multiLines = [BenchLine((0, 0, 0, 0), self.pointSize, self.lineHeight, fontList, self.trackingList) for i in range(len(self.fonts)) if (len(self.fonts) < 6) and (len(self.fonts) < 6)]
		self.w.allLines = Group((1, self.headerHeight, -1, -1))
		
		if (len(self.fonts) > 0) and (len(self.fonts) < 6):
			self.w.allLines.firstLine = Group(self.linePosSize(0))
			self.w.allLines.firstLine.bench = self.multiLines[0].display(self.fonts[0], self.glyphSet)
			self.multiLines[0].identify(0)
		if (len(self.fonts) > 1) and (len(self.fonts) < 6):
			self.w.allLines.secondLine = Group(self.linePosSize(1))
			self.w.allLines.secondLine.bench = self.multiLines[1].display(self.fonts[1], self.glyphSet)
			self.multiLines[1].identify(1)
		if (len(self.fonts) > 2) and (len(self.fonts) < 6):
			self.w.allLines.thirdLine = Group(self.linePosSize(2))
			self.w.allLines.thirdLine.bench = self.multiLines[2].display(self.fonts[2], self.glyphSet)
			self.multiLines[2].identify(2)
		if (len(self.fonts) > 3) and (len(self.fonts) < 6):
			self.w.allLines.fourthLine = Group(self.linePosSize(3))
			self.w.allLines.fourthLine.bench = self.multiLines[3].display(self.fonts[3], self.glyphSet)
			self.multiLines[3].identify(3)
		if (len(self.fonts) > 4) and (len(self.fonts) < 6):
			self.w.allLines.fifthLine = Group(self.linePosSize(4))
			self.w.allLines.fifthLine.bench = self.multiLines[4].display(self.fonts[4], self.glyphSet)
			self.multiLines[4].identify(4)
		if (len(self.fonts) > 5) and (len(self.fonts) < 6):
			self.w.allLines.sixthLine = Group(self.linePosSize(5))
			self.w.allLines.sixthLine.bench = self.multiLines[5].display(self.fonts[5], self.glyphSet)
			self.multiLines[5].identify(5)
		

	def addControls(self):

		self.w.headerControls = Group((0, 0, -0, self.headerHeight))

		self.w.headerControls.inputText = EditText((10, 10, -320, 22), callback=self.inputCallback)

		self.w.headerControls.pointSizePopUp = PopUpButton((-305, 10, 60, 22), self.pointSizeList, callback=self.pointSizePopUpCallback)
		self.w.headerControls.pointSizePopUp.set(6)

		self.w.headerControls.globalTrackingPopUp = PopUpButton((-175, 10, 60, 22), self.trackingList, callback=self.trackingPopUpCallback)
		self.w.headerControls.globalTrackingPopUp.set(int(len(self.trackingList)/2))

		self.w.headerControls.applyAllTrackingButton = Button((-110, 10, 100, 22), "Apply All", callback=self.ApplyAllTracking)

		
	def sizeUpdate(self, sender):

		if (len(self.fonts) < 6):
			if (len(self.fonts) > 0):
				sender.allLines.firstLine.setPosSize(self.linePosSize(0))
			if (len(self.fonts) > 1):
				sender.allLines.secondLine.setPosSize(self.linePosSize(1))
			if (len(self.fonts) > 2):
				sender.allLines.thirdLine.setPosSize(self.linePosSize(2))
			if (len(self.fonts) > 3):
				sender.allLines.fourthLine.setPosSize(self.linePosSize(3))
			if (len(self.fonts) > 4):
				sender.allLines.fifthLine.setPosSize(self.linePosSize(4))
			if (len(self.fonts) > 5):
				sender.allLines.sixthLine.setPosSize(self.linePosSize(5))

			if len(self.fonts > 0):
				if (self.w.getPosSize()[2] < 1200) and (self.w.allLines.firstLine.bench.controls.isVisible() == True) or (self.w.getPosSize()[3] < 600) and (self.w.allLines.firstLine.bench.controls.isVisible() == True):
					for i in range(len(self.fonts)):
						self.multiLines[i].hideControls()
				elif (self.w.getPosSize()[2] > 1200) and (self.w.allLines.firstLine.bench.controls.isVisible() == False) or (self.w.getPosSize()[3] > 600) and (self.w.allLines.firstLine.bench.controls.isVisible() == False):
					for i in range(len(self.fonts)):
						self.multiLines[i].showControls()
		
	def linePosSize(self, index):
		self.benchLineHeight = ((self.w.getPosSize()[3]-self.headerHeight)/(len(self.fonts)))
		return (0, self.benchLineHeight * index, 0, self.benchLineHeight)
		
	def fontList(self):
		fontSetNames = []
		if len(AllFonts()) != len(self.fonts):
			self.fonts = AllFonts()
		for i in range(len(self.fonts)):
			fontName = self.fonts[i].info.familyName + " " + self.fonts[i].info.styleName
			fontSetNames.append(fontName)
		return fontSetNames

	def inputCallback(self, sender):

		inputString = sender.get()

		if inputString == "":
			self.glyphSet = []
		elif len(inputString) < len(self.glyphSet):
			self.glyphSet = []
			for char in inputString:
				charMap = CurrentFont().getCharacterMapping()
				uni = ord(char)
				glyphName = charMap.get(uni)
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

		for i in range(len(self.fonts)):
			self.multiLines[i].setGlyphs(self.glyphSet)

		
	def trackingPopUpCallback(self, sender):
		self.globalTrackingValue = int(sender.getTitle())
		self.setTracking()

	def getlocalTracking(self):
		return [self.multiLines[i].localTracking() for i in range(len(self.fonts))]

	def setTracking(self):
		self.localTracking = self.getlocalTracking()

		if (len(self.fonts) > 0) and (len(self.fonts) < 6):
			self.w.allLines.firstLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[0])
		if (len(self.fonts) > 1) and (len(self.fonts) < 6):
			self.w.allLines.secondLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[1])
		if (len(self.fonts) > 2) and (len(self.fonts) < 6):
			self.w.allLines.thirdLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[2])
		if (len(self.fonts) > 3) and (len(self.fonts) < 6):
			self.w.allLines.fourthLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[3])
		if (len(self.fonts) > 4) and (len(self.fonts) < 6):
			self.w.allLines.fifthLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[4])
		if (len(self.fonts) > 5) and (len(self.fonts) < 6):
			self.w.allLines.sixthLine.bench.glyphView.setTracking(self.globalTrackingValue + self.localTracking[5])
			
	def pointSizePopUpCallback(self, sender):
		pointSize = int(sender.getTitle())
		if (len(self.fonts) > 0) and (len(self.fonts) < 6):
			self.w.allLines.firstLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fonts) > 1) and (len(self.fonts) < 6):
			self.w.allLines.secondLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fonts) > 2) and (len(self.fonts) < 6):
			self.w.allLines.thirdLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fonts) > 3) and (len(self.fonts) < 6):
			self.w.allLines.fourthLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fonts) > 4) and (len(self.fonts) < 6):
			self.w.allLines.fifthLine.bench.glyphView.setPointSize(pointSize)
		if (len(self.fonts) > 5) and (len(self.fonts) < 6):
			self.w.allLines.sixthLine.bench.glyphView.setPointSize(pointSize)
			
	def changeFontOnLine(self, lineIndex, fontIndex):
		self.multiLines[lineIndex].setFont(self.fonts[fontIndex])
		self.multiLines[lineIndex].setGlyphs(self.glyphSet)

	def ApplyAllTracking(self, sender):

		for i in range(len(self.fonts)):
			self.multiLines[i].applyTracking()
			self.multiLines[i].resetLocalTracking()

		self.resetGlobalTracking()

	def resetGlobalTracking(self):
		self.globalTrackingValue = 0
		self.w.headerControls.globalTrackingPopUp.set(int(len(self.trackingList)/2))

	def resetWindow(self):
		self.multiLines = []

myTypeBench = TypeBench()
