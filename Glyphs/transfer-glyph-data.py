# script for Robofont
# written by Loïc Sander
# august 2014

from vanilla import *
from mojo.events import addObserver, removeObserver
from defconAppKit.windows.baseWindow import BaseWindowController
from math import floor

def listFontNames(fontList):
    return [fontName(font) for font in fontList]

def fontName(font):
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None: font.info.familyName = familyName = 'Unnamed Font'
    if styleName is None: font.info.styleName = styleName = 'Unnamed style'
    return ' > '.join([familyName, styleName])

class FontList(List):
    
    def __init__(self, posSize, fontList):
        fontNames = listFontNames(fontList)
        super(FontList, self).__init__(posSize, fontNames, selectionCallback=self.updateSelectedFonts)
        self.fonts = fontList
        self.selection = None

    def update(self, fontList=None):
        if fontList is None: self.fonts = AllFonts()
        elif fontList is not None: self.fonts = fontList
        self.set(listFontNames(self.fonts))
        
    def updateSelectedFonts(self, info):
        indices = info.getSelection()
        self.selection = [self.fonts[i] for i in indices]

    def selectedFonts(self):
        return self.selection
        
    def select(self, thisFont):
        for i, font in enumerate(self.fonts):
            if thisFont == font:
                self.setSelection([i])

class GlyphMigrationController(BaseWindowController):
    
    def __init__(self):
        self.glyphAttributes = {
            'contours': True,
            'components': True,
            'anchors': True,
            'width': True,
            'leftMargin': False,
            'rightMargin': False,
            'angledLeftMargin': False,
            'angledRightMargin': False }
        attributeList = ['contours','components','anchors','width','leftMargin','rightMargin','angledLeftMargin','angledRightMargin']
        m = 20
        self.w = FloatingWindow((300, 630), 'Glyph data migration')
        self.w.source = Group((m, m, -m, 47))
        self.w.source.title = TextBox((0, 0, 0, 14), 'Source font',
        sizeStyle="small")
        self.w.source.font = PopUpButton((1, 22, 0, 20), listFontNames(AllFonts()), callback=self.updateTargetFontsList)
        self.w.target = Group((m, 75, -m, 135))
        self.w.target.title = TextBox((0, 0, 0, 14), 'Target font(s)', sizeStyle="small")
        self.w.target.fonts = FontList((0, 20, 0, 115), [])
        self.w.glyph = Group((m, 225, -m, -m-50))
        self.w.glyph.attributesTitle = TextBox((0, 0, 0, 14), 'Glyph attributes', sizeStyle='small')
        self.w.glyph.attributes = Box((0, 22, 0, 110))
        for i, attribute in enumerate(attributeList):
            j = floor(i/4)
            i = i%4
            setattr(self.w.glyph.attributes, attribute, CheckBox((8+(j*115), 5+(i*23), 0, 23), attribute, value=self.glyphAttributes[attribute], callback=self.selectedAttributes, sizeStyle='small'))
        self.w.glyph.repositionAnchors = CheckBox((0, 140, -0, 23), 'Reposition anchors proportionally', sizeStyle="small")
        self.w.glyph.layersTitle = TextBox((0, -150, 0, 14), 'Glyph layers', sizeStyle='small')
        columnDescriptions = [
            {'title': '=', 'cell': CheckBoxListCell(), 'width': 25},
            {'title': 'layer', 'cell': None} ]
        self.w.glyph.layers = List((0, -130, 0, 115), [{'=':True, 'layer':'foreground'}, {'=':False, 'layer':'background'}], selectionCallback=None, columnDescriptions=columnDescriptions)
        self.w.transfer = Button((m, -m-20, -m, 20), 'Transfer selected glyph data', callback=self.transferGlyphData)
        self.w.replace = CheckBox((m, -m-60, -m, 18), 'Replace layer data', value=False, sizeStyle='small')
        self.updateTargetFontsList()
        self.buildLayersList()
        addObserver(self, 'updateFontsLists', 'fontDidOpen')
        addObserver(self, 'updateFontsLists', 'newFontDidOpen')
        addObserver(self, 'updateFontsLists', 'fontDidClose')
        self.w.bind("close", self.windowClose)
        self.w.open()

    def updateFontsLists(self, notification):
        if len(AllFonts()) == 0:
            self.w.close()
            return
        self.w.source.font.setItems(listFontNames(AllFonts()))
        self.updateTargetFontsList()

    def updateTargetFontsList(self, sender=None):
        sourceFont = self.getSourceFont()
        targetFontsList = AllFonts()
        if sourceFont in targetFontsList:
            targetFontsList.remove(sourceFont)
        self.w.target.fonts.update(targetFontsList)
        self.buildLayersList()

    def buildLayersList(self):
        sourceFont = self.getSourceFont()
        layerList = sourceFont.layerOrder
        layerTable = [{'=':False, 'layer': layer} for layer in layerList]
        layerTable.insert(0, {'=':True, 'layer': 'foreground'})
        self.w.glyph.layers.set(layerTable)

    def getSourceFont(self):
        i = self.w.source.font.get()
        fontListNames = self.w.source.font.getItems()
        fontName = fontListNames[i].split(' > ')
        return AllFonts().getFontsByFamilyNameStyleName(fontName[0], fontName[1])

    def getSelectedLayers(self):
        layerTable = self.w.glyph.layers.get()
        return [layerLine['layer'] for layerLine in layerTable if layerLine['=']]

    def selectedAttributes(self, sender):
        name = sender.getTitle()
        value = sender.get()
        self.glyphAttributes[name] = value

        if name == 'leftMargin':
            self.setAttribute('angledLeftMargin', False)
        elif name == 'angledLeftMargin':
            self.setAttribute('leftMargin', False)
        if name == 'rightMargin':
            self.setAttribute('angledRightMargin', False)
        elif name == 'angledRightMargin':
            self.setAttribute('rightMargin', False)

        if (name in ['leftMargin', 'angledLeftMargin'] and (self.glyphAttributes['rightMargin'] or self.glyphAttributes['angledRightMargin'])) or \
           (name in ['rightMargin', 'angledRightMargin'] and (self.glyphAttributes['leftMargin'] or self.glyphAttributes['angledLeftMargin'])):
            self.setAttribute('width', False)
        if name == 'width' and ((self.glyphAttributes['rightMargin'] or self.glyphAttributes['angledRightMargin']) and (self.glyphAttributes['leftMargin'] or self.glyphAttributes['angledLeftMargin'])):
            for attribute in ['leftMargin', 'angledLeftMargin', 'rightMargin', 'angledRightMargin']:
                self.setAttribute(attribute, False)

    def setAttribute(self, attribute, value):
            self.glyphAttributes[attribute] = value
            width = getattr(self.w.glyph.attributes, attribute)
            width.set(value)

    def transferGlyphData(self, sender):
        sourceFont = self.getSourceFont()
        targetFonts = self.w.target.fonts.selectedFonts()
        glyphSelection = CurrentFont().selection
        glyphAttributes = self.glyphAttributes
        layers = self.getSelectedLayers()
        replaceLayerData = self.w.replace.get()
        repositionAnchors = self.w.glyph.repositionAnchors.get()
        digest = [
            '\n\n////////////////////\nCopy Agent\n////////////////////\n\n\n',
            '** TARGET FONTS **\n\n',
            ', '.join(listFontNames(targetFonts)),
            '\n\n\n** SELECTED GLYPHS **\n\n', 
            ', '.join(glyphSelection), 
            '\n\n\n** TRANSFERED **\n\n- ',
            '\n- '.join([attribute for attribute, value in glyphAttributes.items() if value])
            ]

        for glyph in glyphSelection:

            sourceGlyph = sourceFont[glyph]

            for font in targetFonts:

                if glyph not in font.keys():
                    font.newGlyph(glyph)

                targetGlyph = font[glyph]

                targetGlyph.prepareUndo('attr-transfer')

                for layer in layers:

                    sourceLayerGlyph = sourceGlyph.getLayer(layer)
                    targetLayerGlyph = targetGlyph.getLayer(layer)
                    sourceBox = sourceLayerGlyph.box
                    targetBox = targetLayerGlyph.box

                    for attribute, value in glyphAttributes.items():

                            if attribute in ['width', 'leftMargin', 'rightMargin', 'angledLeftMargin','angledRightMargin'] and value:
                                sourceValue = getattr(sourceGlyph, attribute)
                                setattr(targetGlyph, attribute, sourceValue)

                            elif (attribute in ['contours', 'components', 'anchors']) and value:

                                if attribute == 'anchors':
                                    if replaceLayerData:
                                        for anchor in targetLayerGlyph.anchors:
                                            targetLayerGlyph.removeAnchor(anchor)
                                    for anchor in sourceLayerGlyph.anchors:
                                        anchor_x = anchor.x
                                        anchor_y = anchor.y
                                        if repositionAnchors and (sourceBox is not None) and (targetBox is not None):
                                            if (anchor_x > sourceBox[0]) and (anchor_x < sourceBox[2]):
                                                sourceWidth = sourceBox[2] - sourceBox[0]
                                                targetWidth = targetBox[2] - targetBox[0]
                                                anchor_x = targetBox[0] + ((anchor_x-sourceBox[0])/sourceWidth)*targetWidth
                                            if (anchor_y > sourceBox[1]) and (anchor_y < sourceBox[3]):
                                                sourceHeight = sourceBox[3] - sourceBox[1]
                                                targetHeight = targetBox[3] - targetBox[1]
                                                anchor_y = targetBox[1] + ((anchor_y-sourceBox[1])/sourceHeight)*targetHeight
                                        targetLayerGlyph.appendAnchor(anchor.name, (anchor_x, anchor_y))

                                if attribute == 'components':
                                    if replaceLayerData:
                                        for component in targetLayerGlyph.components:
                                            targetLayerGlyph.removeComponent(component)
                                    for component in sourceLayerGlyph.components:
                                        targetLayerGlyph.appendComponent(component.baseGlyph, component.offset, component.scale)

                                if attribute == 'contours':
                                    if replaceLayerData:
                                        for contour in targetLayerGlyph.contours:
                                            targetLayerGlyph.removeContour(contour)
                                    for contour in sourceLayerGlyph.contours:
                                        targetLayerGlyph.appendContour(contour)

                    targetGlyph.performUndo()

        digest += ['\n\n\n** ON LAYERS **\n\n', ', '.join(layers)]

        print ''.join(digest)

    def windowClose(self, notification):
        removeObserver(self, 'fontDidOpen')
        removeObserver(self, 'newFontDidOpen')
        removeObserver(self, 'fontDidClose')

GlyphMigrationController()