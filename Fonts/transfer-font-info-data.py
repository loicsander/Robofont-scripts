
# script for Robofont
# written by Loïc Sander
# september 2014

from vanilla import *
from mojo.events import addObserver, removeObserver
from defconAppKit.windows.baseWindow import BaseWindowController
from math import floor

def breakCamelCase(string, strip=None):
    ws = []
    w = ''
    prevChar = None
    if strip is not None:
        for s in strip:
            if s in string:
                string = string.lstrip(s)
    for i, char in enumerate(string):
        if char.isupper() and i > 0 and not prevChar.isupper():
            ws.append(w)
            w = ''
        w += char
        prevChar = char
    ws.append(w)
    ws[0] = ws[0].capitalize()
    if ws[0] in ['Os2', 'Head', 'Vhea', 'Hhea', 'Name']:
        ws[0] = '(' + ws[0] + ')'
    return ' '.join(ws)

def splitFontInfo(fontInfo, selected=False):
    return {key: {u'\u2192':selected, 'attribute':breakCamelCase(key, ['postscript', 'openType']), 'value':unicode(value)}  for key, value in fontInfo.items()}

def listFontNames(fontList):
    fontNames = []
    unnamedCounter = 0
    for font in fontList:
        familyName, styleName = fontName(font)
        if familyName == 'Unnamed Font':
            familyName += ' %s' % unnamedCounter
            unnamedCounter += 1
        name = ' > '.join([familyName, styleName])
        fontNames.append(name)
    return fontNames

def fontName(font):
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None: font.info.familyName = familyName = 'Unnamed Font'
    if styleName is None: font.info.styleName = styleName = 'Unnamed style'
    return familyName, styleName

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

class FontInfoTransferController(BaseWindowController):

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
        ww = 600
        self.w = FloatingWindow((ww+(3*m), 600+(2*m)), 'Font Info Data Migration')
        self.w.source = Group((m, m, ww/2, 47))
        self.w.source.title = TextBox((0, 0, 0, 14), 'Source font',
        sizeStyle="small")
        self.w.source.font = PopUpButton((1, 22, 0, 20), listFontNames(AllFonts()), callback=self.switchSourceFont)
        self.w.target = Group(((ww/2)+(2*m), m, -m, 135))
        self.w.target.title = TextBox((0, 0, 0, 14), 'Target font(s)', sizeStyle="small")
        self.w.target.fonts = FontList((0, 20, 0, 115), [])
        self.w.sep1 = HorizontalLine((m, 170, -m, 1))
        self.w.fontInfo = Group((m, 180, -m, -m-50))
        # self.tables = ['general', 'postscript', 'opentype']

        self.tables = [
            {'width':100, 'title':'General'},
            {'width':100, 'title':'Postscript'},
            {'width':100, 'title':'Opentype'}
            ]

        self.w.fontInfo.showTables = SegmentedButton((150, 0, 310, 20), self.tables, callback=self.switchTables)

        # establishing lists to order attributes
        self.attributeOrders = {
            'general': [
                'familyName',
                'styleName',
                'styleMapFamilyName',
                'styleMapStyleName',
                'versionMajor',
                'versionMinor',
                'unitsPerEm',
                'descender',
                'xHeight',
                'capHeight',
                'ascender',
                'italicAngle',
                'copyright',
                'trademark',
                'openTypeNameLicense',
                'openTypeNameLicenseURL',
                'openTypeNameDesigner',
                'openTypeNameDesignerURL',
                'openTypeNameManufacturer',
                'openTypeNameManufacturerURL',
                'note'
            ],

            'postscript' : [
                'postscriptFontName',
                'postscriptFullName',
                'postscriptWeightName',
                'postscriptUniqueID',
                'postscriptBlueValues',
                'postscriptOtherBlues',
                'postscriptFamilyBlues',
                'postscriptStemSnapH',
                'postscriptStemSnapV',
                'postscriptBlueFuzz',
                'postscriptBlueShift',
                'postscriptBlueScale',
                'postscriptForceBold',
                'postscriptSlantAngle',
                'postscriptUnderlineThickness',
                'postscriptUnderlinePosition',
                'postscriptIsFixedPitch',
                'postscriptDefaultWidthX',
                'postscriptNominalWidthX',
                'postscriptDefaultCharacter',
                'postscriptWindowsCharacterSet'
            ],

            'opentype': [
                'openTypeHeadCreated',
                'openTypeHeadLowestRecPPEM',
                'openTypeHeadFlags',
                'openTypeNamePreferredFamilyName',
                'openTypeNamePreferredSubfamilyName',
                'openTypeNameCompatibleFullName',
                'openTypeNameWWSFamilyName',
                'openTypeNameWWSSubfamilyName',
                'openTypeNameVersion',
                'openTypeNameUniqueID',
                'openTypeNameDescription',
                'openTypeNameSampleText',
                'openTypeHheaAscender',
                'openTypeHheaDescender',
                'openTypeHheaLineGap',
                'openTypeHheaCaretSlopeRise',
                'openTypeHheaCaretSlopeRun',
                'openTypeHheaCaretOffset',
                'openTypeVheaVertTypoAscender',
                'openTypeVheaVertTypoDescender',
                'openTypeVheaVertTypoLineGap',
                'openTypeVheaCaretSlopeRise',
                'openTypeVheaCaretSlopeRise',
                'openTypeVheaCaretSlopeRun',
                'openTypeVheaCaretOffset',
                'openTypeOS2WidthClass',
                'openTypeOS2WeightClass',
                'openTypeOS2Selection',
                'openTypeOS2VendorID',
                'openTypeOS2Type',
                'openTypeOS2UnicodeRanges',
                'openTypeOS2CodePageRanges',
                'openTypeOS2TypoAscender',
                'openTypeOS2TypoDescender',
                'openTypeOS2TypoLineGap',
                'openTypeOS2WinAscent',
                'openTypeOS2WinDescent',
                'openTypeOS2SubscriptXSize',
                'openTypeOS2SubscriptYSize',
                'openTypeOS2SubscriptXOffset',
                'openTypeOS2SubscriptYOffset',
                'openTypeOS2SuperscriptXSize',
                'openTypeOS2SuperscriptYSize',
                'openTypeOS2SuperscriptXOffset',
                'openTypeOS2SuperscriptYOffset',
                'openTypeOS2StrikeoutSize',
                'openTypeOS2StrikeoutPosition',
                'openTypeOS2Panose'
            ]
        }

        self.columnDescriptions = [
            {'title': u'\u2192', 'cell': CheckBoxListCell(), 'width': 25},
            {'title': 'attribute', 'cell': None, 'width': 200},
            {'title': 'value', 'cell': None}
            ]
        self.buildTables()
        self.w.fontInfo.postscript.show(False)
        self.w.fontInfo.opentype.show(False)
        self.w.transfer = Button((m, -m-20, -m, 20), 'Transfer font info data', callback=self.transferFontInfoData)
        self.w.selectionFilter = CheckBox((m, -m-60, -m, 18), 'De/Select All', value=False, callback=self.selectAll, sizeStyle='small')
        self.updateTargetFontsList()
        addObserver(self, 'updateFontsLists', 'fontDidOpen')
        addObserver(self, 'updateFontsLists', 'newFontDidOpen')
        addObserver(self, 'updateFontsLists', 'fontDidClose')
        self.w.bind("close", self.windowClose)
        self.w.open()

    def switchSourceFont(self, sender):
        self.updateTargetFontsList()
        self.buildTables()

    def updateFontsLists(self, notification):
        if len(AllFonts()) == 0:
            self.w.close()
            return
        self.w.source.font.setItems(listFontNames(AllFonts()))
        self.updateTargetFontsList()

    def updateTargetFontsList(self):
        sourceFont = self.getSourceFont()
        targetFontsList = AllFonts()
        if sourceFont in targetFontsList:
            targetFontsList.remove(sourceFont)
        self.w.target.fonts.update(targetFontsList)

    def getSourceFont(self):
        i = self.w.source.font.get()
        fontListNames = self.w.source.font.getItems()
        fontName = fontListNames[i].split(' > ')
        return AllFonts().getFontsByFamilyNameStyleName(fontName[0], fontName[1])

    def transferFontInfoData(self, sender):
        fontInfoAttributes = self.attributeOrders['general'] + self.attributeOrders['postscript'] + self.attributeOrders['opentype']
        fontInfos = []
        for tableName in self.tables:
            table = getattr(self.w.fontInfo, tableName)
            tableList = table.get()
            fontInfos += tableList

        attributesToTransfer = {}
        sourceFont = self.getSourceFont()
        targetFonts = self.w.target.fonts.selectedFonts()

        for i, attribute in enumerate(fontInfoAttributes):
            willTransfer = bool(fontInfos[i][u'\u2192'])
            if willTransfer:
                value = getattr(sourceFont.info, attribute)
                attributesToTransfer[attribute] = value

        for font in targetFonts:
            for attrName, value in attributesToTransfer.items():
                setattr(font.info, attrName, value)

        digest = [
            '\n\n////////////////////\nFont Info Copy Agent\n////////////////////',
            '\n** FROM **\n',
            ' '.join(fontName(sourceFont)),
            '\n** TO **\n',
            '\n'.join([' '.join(fontName(font)) for font in targetFonts]),
            '\n** TRANSFERED **\n',
            '\n'.join(attributesToTransfer.keys())
        ]

        print '\n'.join(digest)


    def buildTables(self, selectAll=False):

        # extracting source font info
        sourceFont = self.getSourceFont()
        tableFontInfo = splitFontInfo(sourceFont.info.asDict(), selectAll)

        # building tables
        for table in self.tables:
            tableName = table['title'].lower()
            if not hasattr(self.w.fontInfo, tableName):
                setattr(self.w.fontInfo, tableName, List((0, 32, 0, -18), [], selectionCallback=None, columnDescriptions=self.columnDescriptions))
            order = self.attributeOrders[tableName]
            table = getattr(self.w.fontInfo, tableName)
            table.set([tableFontInfo[key] for key in order])

    def switchTables(self, sender):
        tableIndex = sender.get()
        thisTableName = self.tables[tableIndex]['title'].lower()
        thisTable = getattr(self.w.fontInfo, thisTableName)
        for otherTableRef in self.tables:
            otherTableName = otherTableRef['title'].lower()
            if otherTableName != thisTableName:
                otherTable = getattr(self.w.fontInfo, otherTableName)
                otherTable.show(False)
        thisTable.show(True)

    def selectAll(self, sender):
        self.buildTables(sender.get())

    def windowClose(self, notification):
        removeObserver(self, 'fontDidOpen')
        removeObserver(self, 'newFontDidOpen')
        removeObserver(self, 'fontDidClose')

FontInfoTransferController()