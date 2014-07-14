# 2014 — Loïc Sander
# Group spacing in Robofont

from vanilla import FloatingWindow, CheckBox
from mojo.events import addObserver, removeObserver
from mojo.UI import CurrentSpaceCenter

metricsPrefix = '.mtrx'
leftIndicator = '_L_'
rightIndicator = '_R_'

class spacingObserver(object):
    
    def __init__(self):
        self.enableGroupSpacing = False
        self.popupOpen = False
        addObserver(self, 'glyphEditCallback', 'spaceCenterKeyDown')
        addObserver(self, 'glyphEditedCallback', 'spaceCenterKeyUp')
        addObserver(self, 'spaceCenterOpenCallback', 'spaceCenterDidOpen')
        addObserver(self, 'fontOpenCallback', 'fontDidOpen')
        self.previousMargins = {'left': 0, 'right': 0}

    def processMetricsGroups(self, baseGlyph=None):
            
        for groupName in self.metricsGroups:
            
            if (baseGlyph is None) and len(self.font.groups[groupName]) > 0:
                baseGlyph = self.font.groups[groupName][0]
                self.previousMargins['left'] = self.font[baseGlyph].angledLeftMargin
                self.previousMargins['right'] = self.font[baseGlyph].angledRightMargin
            
            if (metricsPrefix in groupName) and (baseGlyph in self.font.groups[groupName]):
                if (leftIndicator in groupName) and (self.previousMargins['left'] != self.font[baseGlyph].angledLeftMargin):
                    self.setGroupSpacing(baseGlyph, self.font.groups[groupName], 'Left')                    
                elif (rightIndicator in groupName) and (self.previousMargins['right'] != self.font[baseGlyph].angledRightMargin):    
                    self.setGroupSpacing(baseGlyph, self.font.groups[groupName], 'Right') 
    

    def setGroupSpacing(self, baseGlyphName, group, side):
        
        for glyphName in group:
            
            baseGlyph = self.font[baseGlyphName]
            targetGlyph = self.font[glyphName]

            if glyphName is not baseGlyphName:
        
                if (len(targetGlyph.components) > 0) and (side == 'Left'):
                    for component in targetGlyph.components:
                        if component.baseGlyph in group:
                            component.move((self.previousMargins['left']-baseGlyph.angledLeftMargin, 0))

                self.setSidebearing(baseGlyph, targetGlyph, side)

            elif glyphName is baseGlyphName:

                if (len(baseGlyph.components) > 0) and (side == 'Left'):
                    for component in baseGlyph.components:
                        if component.baseGlyph in group:
                            component.move((self.previousMargins['left']-baseGlyph.angledLeftMargin, 0))

            targetGlyph.update()
                    
    def setSidebearing(self, baseGlyph, targetGlyph, side):
        baseMargin = getattr(baseGlyph, 'angled' + side + 'Margin')
        targetMargin = getattr(targetGlyph, 'angled' + side + 'Margin')
        
        if targetMargin != baseMargin:
            setattr(targetGlyph, 'angled' + side + 'Margin', baseMargin)

                    
    def getMetricsGroups(self, notification=None):
        self.font = CurrentFont()            
        if self.font is not None:
            self.metricsGroups = [group for group in self.font.groups.keys() if metricsPrefix in group]         
            if (notification is not None) and (self.enableGroupSpacing == True):
                self.processMetricsGroups()
         

    def enableGroupSpacingCallback(self, sender):
        self.enableGroupSpacing = sender.get()
 
    def glyphEditCallback(self, notification):

        edGlyph = notification['glyph']
        self.previousMargins = {'width': edGlyph.width, 'left': edGlyph.angledLeftMargin, 'right': edGlyph.angledRightMargin}

    def glyphEditedCallback(self, notification):
        
        if self.enableGroupSpacing == True:
        
            edGlyph = notification['glyph']
            
            if self.font != CurrentFont():
                self.getMetricsGroups()
            
            self.processMetricsGroups(edGlyph.name)   
        

    def spaceCenterOpenCallback(self, notification):
        if not self.popupOpen:
            self.w = FloatingWindow((160, 36), 'Group Spacing')
            self.w.activateGroups = CheckBox((9, -27, 151, 18), "Activate Group spacing", value=self.enableGroupSpacing, callback=self.enableGroupSpacingCallback, sizeStyle="small")
            self.w.bind('close', self.windowCloseCallback)
            self.w.open()
            self.popupOpen = True

    def windowCloseCallback(self, notification):
        self.popupOpen = False

    def fontOpenCallback(self, notification):
        font = notification['font']
        font.groups.addObserver(self, 'getMetricsGroups', 'Groups.Changed')
        self.getMetricsGroups(notification)

        
spacingObserver()