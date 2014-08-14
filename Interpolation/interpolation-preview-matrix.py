# Script using glyphPreview to build a 3x3 matrix allowing preview of interpolated and/or extrapolated glyphs

from vanilla import *
from mojo.glyphPreview import GlyphPreview
from mojo.events import addObserver, removeObserver

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
        self.w = Window((1100, 900))
        self.w.fontList = SingleFontList(self, AllFonts(), (0, 0, 200, 250))
        self.w.matrixModel = Group((10, 270, 180, 180))
        self.w.matrixView = Group((200, 0, -0, -0))
        self.master_matrix = []
        self.instance_matrix = []
        for i, k in enumerate(['a','b','c']):
            self.master_matrix.append([])
            self.instance_matrix.append([])
            for j, l in enumerate(['a','b','c']):
                setattr(self.w.matrixView, 'back'+k+l, Box((300*i, 300*j, 300, 300)))
                setattr(self.w.matrixView, k+l, GlyphPreview((300*i, 300*j, 300, 300)))
                setattr(self.w.matrixModel, k+l, SquareButton((60*i, 60*j, 60, 60), '', callback=self.pickSpot, sizeStyle='mini'))
                spotButton = getattr(self.w.matrixModel, k+l)
                spotButton.key = (i,j,k,l)
                self.master_matrix[i].append([k+l, None])
                self.instance_matrix[i].append([k+l, None])
        self.spotFocus = getattr(self.w.matrixModel, 'bb')
        self.newFont = []
        addObserver(self, 'updateMasters', 'currentGlyphChanged')
        addObserver(self, 'updateMasters', 'draw')
        addObserver(self, 'windowClose', 'glyphWindowWillClose')
        self.w.bind('close', self.windowClose)
        self.w.open()
        
    def updateInstances(self):
        for i, k in enumerate(['a','b','c']):
            for j, l in enumerate(['a','b','c']):
                if self.master_matrix[i][j][1] is None:
                    self.makeInstance(i,j,k,l)
                        
    def updateMasters(self, notification):
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
        self.updateInstances()
        
    def pickSpot(self, notifier):
        self.spotFocus = notifier
        key = notifier.key
        self.setMaster(key)
        self.updateInstances()
                       
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
        
        if selectedFont is not None:
            
            for spotKey, spotGlyph in [spot for line in self.master_matrix for spot in line]:
                if (spotGlyph == selectedFont[g]) and (spotKey != k+l):
                    spotGlyph = None
                    break
            
            glyph = selectedFont[g]
            matrixView.show(True)
            matrixView.setGlyph(glyph)
            self.master_matrix[i][j][1] = glyph
            self.instance_matrix[i][j][1] = glyph
            styleName = glyph.getParent().info.styleName
            spotButton.setTitle(styleName)        
                        
        elif selectedFont is None:
            self.master_matrix[i][j][1] = None
            self.instance_matrix[i][j][1] = None
            spotButton.setTitle('x')
            
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

        if ((i-1)%3 < i) and ((i+1)%3 < i):
            instance.interpolate(-1, master1, master2)
        elif ((i-1)%3 > i) and ((i+1)%3 > i):
            instance.interpolate(2, master1, master2)
            
        elif ((((i-1)%3 < i) and ((i+1)%3 > i)) or (((i-1)%3 > i) and (i+1)%3 < i)):
            instance.interpolate(.5, master1, master2)

        if previousInstance is not None:
            instance.interpolate(.5, instance, previousInstance)

        return instance

    def triangularInterpolation(self, master1, master2, master3, previousInstance=None):

        instance = RGlyph()
        midInstance = RGlyph()
        midInstance.interpolate(.5, master1, master2)
        instance.interpolate(2, master3, midInstance)

        if previousInstance is not None:
            instance.interpolate(.5, instance, previousInstance)

        return instance

    def windowClose(self, notification):
        removeObserver(self, "currentGlyphChanged")
        removeObserver(self, "draw")
        removeObserver(self, "glyphWindowWillClose")

interpolationMatrixController()