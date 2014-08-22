# Script using glyphPreview to build a 3x3 matrix allowing preview of interpolated and/or extrapolated glyphs

from vanilla import *
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver
from AppKit import NSColor
from math import cos, sin, pi

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

def rawGlyph(glyph):
    components = glyph.components
    font = glyph.getParent()
    decomposedGlyph = RGlyph()
    
    if font is not None:
        for component in components:
            decomponent = RGlyph()
            decomponent.appendGlyph(font[component.baseGlyph])
            decomponent.scale((component.scale[0], component.scale[1]))
            decomponent.move((component.offset[0], component.offset[1]))
            decomposedGlyph.appendGlyph(decomponent)
        for contour in glyph.contours:
            decomposedGlyph.appendContour(contour)
        decomposedGlyph.width = glyph.width
        
    return decomposedGlyph

# def rawGlyph(glyph):
#     decompGlyph = 
#     components = glyph.components
#     font = glyph.getParent()
    
#     if font is not None:
#         for component in reversed(components):
#             component.decompose()
#     return decompGlyph

class SingleFontList(List):
    
    def __init__(self, parent, fontList, posSize):
        fontNames = [' '.join([font.info.familyName, font.info.styleName]) for font in fontList]
        super(SingleFontList, self).__init__(posSize, fontNames, selectionCallback=self.selectedFont, allowsMultipleSelection=False)
        self.fonts = fontList
        self.selection = fontList[0]
        self.parent = parent
        
    def selectedFont(self, info):
        if len(info.getSelection()) > 0:
            index = info.getSelection()[0]
            self.selection = self.fonts[index]
            self.parent.updateFont(self.selection)
        else:
            self.selection = None
            self.parent.updateFont(None)
        
    def selected(self):
        return self.selection
        
    def select(self, thisFont):
        for i, font in enumerate(self.fonts):
            if thisFont == font:
                self.setSelection([i])

class interpolationMatrixController(object):
    
    def __init__(self):
        bgColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(255, 255, 255, 255)
        self.w = Window((1200, 900), minSize=(900, 600))
        self.w.getNSWindow().setBackgroundColor_(bgColor)
        self.w.fontList = SingleFontList(self, AllFonts(), (0, 0, 300, 250))
        self.w.matrixModel = Group((15, 265, 270, 270))
        self.w.matrixView = Group((300, 0, -0, -0))
        self.master_matrix = []
        self.instance_matrix = []
        self.ipf = .5
        self.xpf = 1
        for i, k in enumerate(['a','b','c']):
            self.master_matrix.append([])
            self.instance_matrix.append([])
            for j, l in enumerate(['a','b','c']):
                setattr(self.w.matrixView, 'back'+k+l, Box((300*i, 300*j, 300, 300)))
                setattr(self.w.matrixView, k+l, GlyphPreview((300*i, 300*j, 300, 300)))
                setattr(self.w.matrixModel, k+l, SquareButton((90*i, 90*j, 90, 90), '', callback=self.pickSpot, sizeStyle='mini'))
                spotButton = getattr(self.w.matrixModel, k+l)
                spotButton.key = (i,j,k,l)
                self.master_matrix[i].append([k+l, None])
                self.instance_matrix[i].append([k+l, None])
        self.w.interpolation = Group((10, 565, 280, 50))
        self.w.interpolation.start = TextBox((7, 2, 20, 12), '0', sizeStyle='mini')
        self.w.interpolation.end = TextBox((-20, 2, 20, 12), '1', sizeStyle='mini')
        self.w.interpolation.title = TextBox((20, 0, -20, 17), 'Interpolation factor', sizeStyle='small', alignment='center')
        self.w.interpolation.slider = Slider((5, 27, -5, 15), minValue=0, maxValue=1, value=self.ipf, callback=self.sliderInput, tickMarkCount=5)
        self.w.interpolation.slider.name = 'ipf'
        self.w.extrapolation = Group((10, 632, 280, 50))
        self.w.extrapolation.start = TextBox((7, 2, 20, 12), '1', sizeStyle='mini')
        self.w.extrapolation.end = TextBox((-20, 2, 20, 12), '3', sizeStyle='mini')
        self.w.extrapolation.title = TextBox((20, 0, -20, 17), 'Extrapolation factor', sizeStyle='small', alignment='center')
        self.w.extrapolation.slider = Slider((5, 27, -5, 15), minValue=0, maxValue=2, value=self.xpf, callback=self.sliderInput, tickMarkCount=5)
        self.w.extrapolation.slider.name = 'xpf'
        self.spotFocus = getattr(self.w.matrixModel, 'bb')
        self.w.updateMatrixButton = Button((10, 727, 280, 20), 'Update', callback=self.updateMasters)
        self.w.resetMatrixButton = Button((10, 755, 280, 20), 'Reset', callback=self.resetMatrix)
        self.newFont = []
        addObserver(self, 'updateMasters', 'currentGlyphChanged')
        addObserver(self, 'updateMasters', 'draw')
        self.w.bind('close', self.windowClose)
        self.w.bind('resize', self.windowResize)
        self.w.open()
        
    def updateInstances(self):
        for i, k in enumerate(['a','b','c']):
            for j, l in enumerate(['a','b','c']):
                if self.master_matrix[i][j][1] is None:
                    self.makeInstance(i,j,k,l)
                        
    def updateMasters(self, notification=None):
        for i, line in enumerate(self.master_matrix):
            for j, spot in enumerate(line):
                if spot[1] is not None:
                    stringKey = [char for char in spot[0]]
                    key = i, j, stringKey[0], stringKey[1]
                    self.setMaster(key)
        self.updateInstances()

    def updateFont(self, font):
        self.newFont = [font]
        spotFocus = self.spotFocus
        key = spotFocus.key
        self.setMaster(key)
        self.clearMatrix(True)
        self.updateMasters()

    def pickSpot(self, notifier):
        self.spotFocus = notifier
        key = notifier.key
        self.setMaster(key)
        self.clearMatrix(True)
        self.updateMasters()
                       
    def setMaster(self,key):
        i, j, k, l = key
        if CurrentGlyph() is None:
            return
        g = CurrentGlyph().name
        
        if self.master_matrix[i][j][1] is None:
            selectedFont = self.w.fontList.selected()
        elif self.master_matrix[i][j][1] is not None:
            if len(self.newFont) == 0:
                selectedFont = self.master_matrix[i][j][1].getParent()
            elif len(self.newFont) > 0:
                selectedFont = self.newFont[0]
                self.w.fontList.select(selectedFont)
        
        spotButton = getattr(self.w.matrixModel, k+l)
        matrixView = getattr(self.w.matrixView, k+l)
        
        if (selectedFont is not None) and (g in selectedFont.keys()):
            
            for spotKey, spotGlyph in [spot for line in self.master_matrix for spot in line]:
                if (spotGlyph == selectedFont[g]) and (spotKey != k+l):
                    spotGlyph = None
                    break
            
            glyph = rawGlyph(selectedFont[g])
            glyph.setParent(selectedFont)

            matrixView.show(True)
            matrixView.setGlyph(glyph)
            self.master_matrix[i][j][1] = glyph
            self.instance_matrix[i][j][1] = glyph
            familyName = selectedFont.info.familyName
            styleName = selectedFont.info.styleName
            spotButton.setTitle('\n'.join([familyName,styleName]))  
                        
        elif selectedFont is None:
            self.master_matrix[i][j][1] = None
            self.instance_matrix[i][j][1] = None
            spotButton.setTitle('')
            
        self.newFont = []
            
    def makeInstance(self, i, j, k, l, instancesAsMasters=False):
        instance = RGlyph()
        previousInstance = None
        matrixView = getattr(self.w.matrixView, k+l)
        matrix = self.master_matrix

        if instancesAsMasters:
            matrix = self.instance_matrix
        
        prevHspot = matrix[i][(j-1)%3][1]
        nextHspot = matrix[i][(j+1)%3][1]
        prevVspot = matrix[(i-1)%3][j][1]
        nextVspot = matrix[(i+1)%3][j][1]
        
        # look for masters in one direction
        if (prevHspot is not None) and (nextHspot is not None):
            
            master1 = prevHspot
            master2 = nextHspot
            
            instance = self.linearInterpolation(j, master1, master2)
          
        # look for masters in second direction      
        if (prevVspot is not None) and (nextVspot is not None):
            
            master1 = prevVspot
            master2 = nextVspot
            if instance.isEmpty() == False: previousInstance = instance
            
            instance = self.linearInterpolation(i, master1, master2, previousInstance)

        # if no masters in line found
        #if instance.isEmpty():

        corner_1 = matrix[(i-1)%3][(j-1)%3][1]
        corner_2 = matrix[(i-1)%3][(j+1)%3][1]
        corner_3 = matrix[(i+1)%3][(j+1)%3][1]
        corner_4 = matrix[(i+1)%3][(j-1)%3][1]

        if (prevHspot is not None) and (prevVspot is not None) and (corner_1 is not None):
            if instance.isEmpty() == False: previousInstance = instance
            instance = self.triangularInterpolation(prevHspot, prevVspot, corner_1, previousInstance)

        elif (nextHspot is not None) and (prevVspot is not None) and (corner_2 is not None):
            if instance.isEmpty() == False: previousInstance = instance
            instance = self.triangularInterpolation(nextHspot, prevVspot, corner_2, previousInstance)

        elif (nextHspot is not None) and (nextVspot is not None) and (corner_3 is not None):
            if instance.isEmpty() == False: previousInstance = instance
            instance = self.triangularInterpolation(nextHspot, nextVspot, corner_3, previousInstance)

        elif (nextHspot is not None) and (prevVspot is not None) and (corner_4 is not None):
            if instance.isEmpty() == False: previousInstance = instance
            instance = self.triangularInterpolation(nextHspot, prevVspot, corner_4, previousInstance)

        if instance.isEmpty() and not instancesAsMasters:
            self.makeInstance(i,j,k,l, True)
            return
        
        matrixView.show(True)
        matrixView.setGlyph(instance)
        self.instance_matrix[i][j][1] = instance

    def linearInterpolation(self, i, master1, master2, previousInstance=None):

        instance = RGlyph()
        ipf = self.ipf
        xpf = self.xpf

        if ((i-1)%3 < i) and ((i+1)%3 < i):
            instance.interpolate(-xpf, master1, master2)
        elif ((i-1)%3 > i) and ((i+1)%3 > i):
            instance.interpolate(1+xpf, master1, master2)
            
        elif ((((i-1)%3 < i) and ((i+1)%3 > i)) or (((i-1)%3 > i) and (i+1)%3 < i)):
            instance.interpolate(ipf, master1, master2)

        if previousInstance is not None:
            instance.interpolate(ipf, instance, previousInstance)

        # if instance.isEmpty():
        #     instance = errorGlyph()
        return instance

    def triangularInterpolation(self, master1, master2, master3, previousInstance=None):

        ipf = self.ipf
        xpf = self.xpf

        instance = RGlyph()
        midInstance = RGlyph()
        midInstance.interpolate(ipf, master1, master2)
        instance.interpolate(1+xpf, master3, midInstance)

        if previousInstance is not None:
            instance.interpolate(ipf, instance, previousInstance)
        
        # if instance.isEmpty():
        #     instance = errorGlyph()
        return instance

    def sliderInput(self, sender):
        mode = sender.name
        value = sender.get()
        setattr(self, mode, value)
        self.updateMasters()

    def resetMatrix(self, sender):
        self.clearMatrix()

    def clearMatrix(self, keepMasters=False):
        saveMasters = list(self.master_matrix)
        self.master_matrix = []
        self.instance_matrix = []
        for i, k in enumerate(['a','b','c']):
            self.master_matrix.append([])
            self.instance_matrix.append([])
            for j, l in enumerate(['a','b','c']):
                if keepMasters and (saveMasters[i][j][1] is not None):
                    master = saveMasters[i][j][1]
                    self.master_matrix[i].append([k+l, master])
                else:
                    self.master_matrix[i].append([k+l, None])
                self.instance_matrix[i].append([k+l, None])
                glyphCell = getattr(self.w.matrixView, k+l)
                glyphCell.setGlyph(None)
                spot = getattr(self.w.matrixModel, k+l)
                spot.setTitle('')

    def windowResize(self, info):
        x, y, w, h = info.getPosSize()
        w -= 300
        cW = w / 3
        cH = h / 3
        for i, k in enumerate(['a', 'b', 'c']):
            for j, l in enumerate(['a', 'b', 'c']):
                background = getattr(self.w.matrixView, 'back'+k+l)
                glyphView = getattr(self.w.matrixView, k+l)
                background.setPosSize((i*cW, j*cH, cW, cH))
                glyphView.setPosSize((i*cW, j*cH, cW, cH))

    def windowClose(self, notification):
        removeObserver(self, "currentGlyphChanged")
        removeObserver(self, "draw")

interpolationMatrixController()