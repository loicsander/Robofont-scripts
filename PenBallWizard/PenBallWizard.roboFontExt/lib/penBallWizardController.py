#coding=utf-8
__version__ = 0.69

from collections import OrderedDict

from AppKit import NSMenuItem

from robofab.world import RFont
from defconAppKit.tools.textSplitter import splitText
from vanilla import *
from vanilla.dialogs import getFile, message
from mojo.UI import MultiLineView
from mojo.extensions import getExtensionDefault, setExtensionDefault
from mojo.events import addObserver, removeObserver, postEvent

from penBallWizard.objects.penBallFilters import PenBallFiltersManager
from penBallWizard.parameterObjects.vanillaParameterObjects import ParameterSliderTextInput, VanillaSingleValueParameter


# LOCALPATH = '/'.join(__file__.split('/')[:-1])
# JSONFILE = 'filters.json'
PENBALLWIZARD_EXTENSIONKEY = 'com.loicsander.penBallWizard'


def makeListFontName(font):
    familyName = font.info.familyName
    styleName = font.info.styleName
    if familyName is None:
        familyName = font.info.familyName = 'Unnamed'
    if styleName is None:
        styleName = font.info.styleName = 'Unnamed'
    return ' > '.join([familyName, styleName])


class PenBallWizardController(object):

    def __init__(self):
        self.filters = PenBallFiltersManager()
        # self.filters.loadFiltersFromJSON('/'.join([LOCALPATH, JSONFILE]))
        filtersList = getExtensionDefault('{0}.filtersList'.format(PENBALLWIZARD_EXTENSIONKEY), [])
        self.filters.loadFiltersList(filtersList)
        self.glyphNames = []
        self.observedGlyphs = []
        self.currentFont = CurrentFont()
        self.initCachedFont()
        filtersList = self.filters.keys()
        if len(filtersList) > 0:
            self.currentFilterName = filtersList[0]
        else:
            self.currentFilterName = None
        self.fill = True

        self.observers = [
            ('fontChanged', 'fontBecameCurrent'),
            ('fontChanged', 'fontDidOpen'),
            ('fontChanged', 'fontDidClose'),
        ]

        self.displaySettingsRecord = {
            1: (u'✓ Fill', True),
            2: (u'Stroke', False),
            3: (u'Inverse', False),
        }

        self.w = Window((100, 100, 800, 500), 'PenBall Wizard v{0}'.format(__version__), minSize=(500, 400))
        self.w.filtersPanel = Group((0, 0, 300, -0))
        self.w.filtersPanel.filtersList = List((0, 0, -0, -80), filtersList, selectionCallback=self.filterSelectionChanged, doubleClickCallback=self.filterEdit, allowsMultipleSelection=False, allowsEmptySelection=False, rowHeight=22)
        self.w.filtersPanel.controls = Group((0, -80, -0, 0))
        self.w.filtersPanel.addFilter = SquareButton((0, -80, 100, 40), 'Add filter', sizeStyle='small', callback=self.addFilter)
        self.w.filtersPanel.addFilterChain = SquareButton((100, -80, 100, 40), 'Add operations', sizeStyle='small', callback=self.addFilterChain)
        self.w.filtersPanel.removeFilter = SquareButton((-100, -80, 100, 40), 'Remove filter', sizeStyle='small', callback=self.removeFilter)
        self.w.textInput = EditText((300, 0, -75, 22), '', callback=self.stringInput)
        self.w.generate = SquareButton((0, -40, 300, -0), 'Generate', callback=self.buildGenerationSheet, sizeStyle='small')
        self.w.displaySettings = PopUpButton(
            (-70, 3, -10, 15),
            self.makeDisplaySettingsMenuItems(),
            sizeStyle='mini',
            callback=self.changeDisplaySettings)
        self.w.displaySettings.getNSPopUpButton().setPullsDown_(True)
        self.w.displaySettings.getNSPopUpButton().setBordered_(False)
        self.w.preview = MultiLineView((300, 22, -0, -0))
        displayStates = self.w.preview.getDisplayStates()
        for key in ['Show Metrics','Upside Down','Stroke','Beam','Inverse','Water Fall','Multi Line']:
            displayStates[key] = False
        for key in ['Fill','Single Line']:
            displayStates[key] = True
        self.w.preview.setDisplayStates(displayStates)

        for callback, event in self.observers:
            addObserver(self, callback, event)

        self.updateControls()

        self.w.bind('close', self.end)
        self.launchWindow()
        self.w.open()

    def changeDisplaySettings(self, sender):
        selection = sender.get()
        name, state = self.displaySettingsRecord[selection]
        self.setDisplayOption(selection, name, state)

    def setDisplayOption(self, index, name, value):
        if u'✓' in name: name = name[2:]
        self.displaySettingsRecord[index] = (name if value is True else u'{0} {1}'.format(u'✓', name), not value)
        displayStates = self.w.preview.getDisplayStates()
        if name in ['Fill', 'Stroke', 'Inverse']:
            displayStates[name] = not value
        # elif name in ['Negative']:

        self.w.preview.setDisplayStates(displayStates)
        self.w.displaySettings.setItems(self.makeDisplaySettingsMenuItems())

    def makeDisplaySettingsMenuItems(self):
        displaySettingsMenuItems = [NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(self.displaySettingsRecord[key][0], None, '') for key in sorted(self.displaySettingsRecord.keys())]
        displaySettingsMenuItems.insert(0, 'Settings')
        return displaySettingsMenuItems

    def generateGlyphsToFont(self, exportFont=None, layerName=None):
        font = RFont(showUI=False) if exportFont is None else exportFont
        currentFont = self.currentFont
        filterName = self.currentFilterName
        currentFilter = self.filters[filterName]
        if currentFont is not None and len(currentFont.selection):
            glyphs = [currentFont[glyphName] for glyphName in currentFont.selection if glyphName in currentFont]
            for glyph in glyphs:
                if len(glyph.components) > 0:
                    for comp in glyph.components:
                        baseGlyphName = comp.baseGlyph
                        baseGlyph = currentFont[baseGlyphName]
                        baseFilteredGlyph = currentFilter(baseGlyph)
                        newFont.insertGlyph(baseFilteredGlyph, baseGlyphName)
                        newFont[baseGlyphName].unicode = baseFilteredGlyph.unicode
                filteredGlyph = currentFilter(glyph)
                if filteredGlyph is not None:
                    if exportFont is None:
                        font.insertGlyph(filteredGlyph, glyph.name)
                    else:
                        glyph = font[glyph.name] if layerName is None else font[glyph.name].getLayer(layerName)
                        glyph.clearContours()
                        glyph.clearComponents()
                        glyph.appendGlyph(filteredGlyph)
            font.showUI()
        else:
            message(u'PenBallWizard', 'No selected glyphs to generate')

    def generateGlyphsToLayer(self, font, layerName):
        filterName = self.currentFilterName
        currentFilter = self.filters[filterName]
        if font is not None:
            glyphs = [font[glyphName] for glyphName in font.selection if glyphName in font]
            for glyph in glyphs:
                if len(glyph.components) == 0:
                    layerGlyph = glyph.getLayer(layerName)
                    filteredGlyph = currentFilter(glyph)
                    if filteredGlyph is not None:
                        layerGlyph.appendGlyph(filteredGlyph)

    def updateFiltersList(self, selectedIndex=0):
        filtersList = self.filters.keys()
        self.w.filtersPanel.filtersList.set(filtersList)
        self.w.filtersPanel.filtersList.setSelection([selectedIndex])

    def setArgumentValue(self, sender):
        value = sender.get()
        valueType = sender.type
        if valueType == 'bool':
            value = bool(value)
        key = sender.name
        if self.currentFilterName is not None:
            self.filters.setArgumentValue(self.currentFilterName, key, value)
            self.resetRepresentations()
        self.updatePreview()

    def resetRepresentations(self):
        font = self.currentFont
        self.initCachedFont()
        if font is not None:
            for glyphName in self.glyphNames:
                if glyphName in font:
                    font[glyphName].naked().destroyAllRepresentations()

    def processGlyphs(self):
        font = self.currentFont
        if font is not None:
            sourceGlyphs = []
            for glyphName in self.glyphNames:
                if glyphName in font:
                    glyph = font[glyphName]
                    if glyph not in self.observedGlyphs:
                        glyph.addObserver(self, 'glyphChanged', 'Glyph.Changed')
                        self.observedGlyphs.append(glyph)
                    sourceGlyphs.append(glyph)
            filterName = self.currentFilterName
            filteredGlyphs = self.filterGlyphs(filterName, sourceGlyphs, self.cachedFont)
            return filteredGlyphs
        return []

    def filterGlyphs(self, filterName, glyphs, font):
        currentFilter = self.filters[filterName]
        filteredGlyphs = []
        for glyph in glyphs:
            if len(glyph.components) > 0:
                for comp in glyph.components:
                    baseGlyphName = comp.baseGlyph
                    baseGlyph = glyph.getParent()[baseGlyphName]
                    baseFilteredGlyph = currentFilter(baseGlyph)
                    if baseFilteredGlyph is not None:
                        font.insertGlyph(baseFilteredGlyph, baseGlyphName)
            filteredGlyph = currentFilter(glyph)
            if filteredGlyph is not None:
                font.insertGlyph(filteredGlyph, glyph.name)
                filteredGlyphs.append(font[glyph.name])
        return filteredGlyphs

    def updatePreview(self, notification=None):
        glyphs = self.processGlyphs()
        self.w.preview.setFont(self.cachedFont)
        self.w.preview.set(glyphs)

    def updateControls(self):
        if self.currentFilterName is not None:
            if hasattr(self.w.filtersPanel, 'controls'):
                delattr(self.w.filtersPanel, 'controls')
            currentFilter = self.filters[self.currentFilterName]
            self.w.filtersPanel.controls = Group((0, 0, 0, 0))
            hasSubfilters = self.filters.hasSubfilters(self.currentFilterName)

            if hasSubfilters:
                argumentBlocks = [(subfilterName, self.filters[subfilterName].arguments) for subfilterName, mode, source in currentFilter.subfilters]
            else:
                argumentBlocks = [(currentFilter.name, currentFilter.arguments)]

            gap = 5
            height = gap
            end = 0
            lineheight = 27
            top = 35
            boxes = 0

            for j, (filterName, arguments)  in enumerate(argumentBlocks):
                if len(arguments) > 0:
                    blockfilterName = '{0}{1}'.format(filterName, j)
                    setattr(self.w.filtersPanel.controls, blockfilterName, Box((5, 5, 0, 0)))
                    block = getattr(self.w.filtersPanel.controls, blockfilterName)
                    if hasSubfilters:
                        _, filterMode, filterSource = currentFilter.subfilters[j]
                        modes = '({0}) [{1}]'.format(filterMode, filterSource)
                        block.modes = TextBox((-150, 11, -8, 12), modes, alignment='right', sizeStyle='mini')
                    block.title = TextBox((8, 8, -150, 22), filterName.upper())
                    start = height
                    boxHeight = top

                    for i, (arg, value) in enumerate(arguments.items()):
                        valueType = None

                        if hasSubfilters:
                            argumentName = currentFilter.joinSubfilterArgumentName(filterName, arg, j)
                            if argumentName in currentFilter.arguments:
                                value = currentFilter.arguments[argumentName]
                            else:
                                value = self.filters[filterName].arguments[argumentName]
                                currentFilter.setArgumentValue(argumentName, value)
                        else:
                            argumentName = arg

                        limits = currentFilter.getLimits(argumentName)
                        if limits is None: limits = (0, 100)

                        if isinstance(value, bool):
                            setattr(block, arg, CheckBox((8, top + (i*lineheight), -8, 22), arg, value=value, callback=self.setArgumentValue, sizeStyle='small'))
                            valueType = 'bool'
                        elif isinstance(value, (str, unicode)):
                            setattr(block, arg, EditText((8, top + (i*lineheight), -8, 22), value, callback=self.setArgumentValue, sizeStyle='small'))
                        elif isinstance(value, (int, float)):
                            parameter = VanillaSingleValueParameter(arg, value, limits=limits)
                            setattr(block, arg, ParameterSliderTextInput(parameter, (8, top + (i*lineheight), -8, 22), title=arg, callback=self.setArgumentValue))

                        control = getattr(block, arg)
                        control.name = argumentName
                        control.type = valueType

                        boxHeight += lineheight

                    boxHeight += 12
                    block.setPosSize((5, start, -5, boxHeight))
                    height += boxHeight + gap

            height += 80

            self.w.filtersPanel.filtersList.setPosSize((0, 0, -0, -height))
            self.w.filtersPanel.controls.setPosSize((0, -height, -0, -85))

    def stringInput(self, sender):
        text = sender.get()
        if self.currentFont is not None:
            cmap = self.currentFont.getCharacterMapping()
            self.glyphNames = splitText(text, cmap)
        else:
            self.glyphNames = []
        self.updatePreview()

    def filterEdit(self, sender):
        filterName = self.currentFilterName
        if self.filters.hasSubfilters(filterName):
            self.buildFilterGroupSheet(filterName)
        else:
            self.buildFilterSheet(filterName)
        self.filterSheet.open()

    def buildGenerationSheet(self, sender):
        self.generationSheet = Sheet((0, 0, 400, 140), self.w)
        self.generationSheet.inner = Group((15, 20, -15, -15))
        self.generationSheet.inner.fontChoiceTitle = TextBox((0, 0, 100, 22), u'Destination Font')
        self.generationSheet.inner.fontChoice = PopUpButton((110, 0, -0, 22), ['New font']+[makeListFontName(font) for font in AllFonts()])
        self.generationSheet.inner.layerNameTitle = TextBox((0, 35, 100, 22), u'Layer name')
        self.generationSheet.inner.layerName = EditText((110, 35, -0, 22), '')

        self.generationSheet.inner.generate = Button((-200, -22, -0, 22), 'Generate selected glyphs', callback=self.proceedToGeneration)
        self.generationSheet.open()

    def proceedToGeneration(self, sender):
        fontNames = self.generationSheet.inner.fontChoice.getItems()
        selection = self.generationSheet.inner.fontChoice.get()
        selectedFontName = fontNames[selection]
        if selectedFontName == 'New font':
            font = None
        else:
            familyName, styleName = selectedFontName.split(' > ')
            font = AllFonts().getFontsByFamilyNameStyleName(familyName, styleName)
        layerName = self.generationSheet.inner.layerName.get()
        if len(layerName) == 0: layerName = None
        self.generationSheet.close()
        self.generateGlyphsToFont(font, layerName)

    def buildFilterSheet(self, filterName='', makeNew=False):
        sheetFields = {
            'file': '',
            'module': '',
            'filterObjectName': '',
            'limits': {},
            'arguments': {},
        }
        if filterName != '':
            filterDict = self.filters[filterName].getFilterDict()
            for key in filterDict:
                if key == "arguments":
                    entry = OrderedDict(filterDict[key])
                else:
                    entry = filterDict[key]
                sheetFields[key] = entry

        self.filterSheet = Sheet((0, 0, 400, 350), self.w)
        self.filterSheet.new = makeNew
        self.filterSheet.index = self.filters[filterName].index if not makeNew else -1
        applyTitle = 'Add Filter' if filterName == '' else 'Update Filter'
        self.filterSheet.apply = SquareButton((-115, -37, 100, 22), applyTitle, callback=self.processFilter, sizeStyle='small')
        self.filterSheet.cancel = SquareButton((-205, -37, 80, 22), 'Cancel', callback=self.closeFilterSheet, sizeStyle='small')

        y = 20
        self.filterSheet.nameTitle = TextBox((15, y, 100, 22), 'Filter Name')
        self.filterSheet.name = EditText((125, y, -15, 22), filterName)
        y += 22

        tabs = ['module','file']
        selectedTab = 0 if len(sheetFields['module']) >= len(sheetFields['file']) else 1
        filterObjectName = sheetFields['filterObjectName']

        y += 20
        self.filterSheet.importPath = Tabs((15, y, -15, 75), tabs)
        self.filterSheet.importPath.set(selectedTab)
        modulePathTab = self.filterSheet.importPath[0]
        filePathTab = self.filterSheet.importPath[1]

        modulePathTab.pathInput = EditText((10, 10, -10, -10), sheetFields['module'])
        filePathTab.pathInput = EditText((10, 10, -110, -10), sheetFields['file'])
        filePathTab.fileInput = SquareButton((-100, 10, 90, -10), u'Add File…', sizeStyle='small', callback=self.getFile)
        y += 75

        y += 10
        self.filterSheet.filterObjectTitle = TextBox((15, y, 100, 22), 'Filter Object (pen, function)')
        self.filterSheet.filterObject = EditText((125, y, -15, 22), filterObjectName)
        y += 22

        y += 20
        columns = [
            {'title': 'argument', 'width': 160, 'editable':True},
            {'title': 'value', 'width': 71, 'editable':True},
            {'title': 'min', 'width': 49, 'editable':True},
            {'title': 'max', 'width': 49, 'editable':True}
        ]

        arguments = sheetFields['arguments']
        limits = sheetFields['limits']

        argumentItems = []

        for key, value in arguments.items():
            if isinstance(value, bool):
                value = str(value)
            elif isinstance(value, float):
                value = round(value, 2)
            argItem = {
                'argument': key,
                'value': value
                }
            if key in limits:
                minimum, maximum = sheetFields['limits'][key]
                argItem['min'] = minimum
                argItem['max'] = maximum

            argumentItems.append(argItem)

        buttonSize = 20
        gutter = 7
        self.filterSheet.arguments = List((15 + buttonSize + gutter, y, -15, -52), argumentItems, columnDescriptions=columns, allowsMultipleSelection=False, allowsEmptySelection=False)
        self.filterSheet.addArgument = SquareButton((15, -52-(buttonSize*2)-gutter, buttonSize, buttonSize), '+', sizeStyle='small', callback=self.addArgument)
        self.filterSheet.removeArgument = SquareButton((15, -52-buttonSize, buttonSize, buttonSize), '-', sizeStyle='small', callback=self.removeArgument)
        if len(argumentItems) == 0:
            self.filterSheet.removeArgument.enable(False)

        if filterName == '':
            self.currentFilterName = ''

    def buildFilterGroupSheet(self, filterName='', makeNew=False):

        subfilters = self.filters[filterName].subfilters if filterName in self.filters else []
        subfilterItems = [{'filterName': subfilterName, 'mode': subfilterMode if subfilterMode is not None else '', 'source': source if source is not None else ''} for subfilterName, subfilterMode, source in subfilters]

        self.filterSheet = Sheet((0, 0, 400, 350), self.w)
        self.filterSheet.new = makeNew
        self.filterSheet.index = self.filters[filterName].index if not makeNew else -1
        applyTitle = 'Add Operation' if filterName == '' else 'Update Operation'
        self.filterSheet.apply = SquareButton((-145, -37, 130, 22), applyTitle, callback=self.processFilterGroup, sizeStyle='small')
        self.filterSheet.cancel = SquareButton((-210, -37, 60, 22), 'Cancel', callback=self.closeFilterSheet, sizeStyle='small')

        y = 20
        self.filterSheet.nameTitle = TextBox((15, y, 100, 22), 'Filter Name')
        self.filterSheet.name = EditText((125, y, -15, 22), filterName)
        y += 22

        columns = [
            {'title': 'filterName', 'editable': True, 'width': 140},
            {'title': 'mode', 'editable': True, 'width': 89},
            {'title': 'source', 'editable': True, 'width': 100}
        ]

        buttonSize = 20
        gutter = 7

        y += 20
        self.filterSheet.subfilters = List((15 + buttonSize + gutter, y, -15, -52), subfilterItems, columnDescriptions=columns, allowsMultipleSelection=False, allowsEmptySelection=False)
        self.filterSheet.addSubfilter = SquareButton((15, -52-(buttonSize*2)-gutter, buttonSize, buttonSize), '+', sizeStyle='small', callback=self.addSubfilter)
        self.filterSheet.removeSubfilter = SquareButton((15, -52-buttonSize, buttonSize, buttonSize), '-', sizeStyle='small', callback=self.removeSubfilter)
        if len(subfilters) == 0:
            self.filterSheet.removeSubfilter.enable(False)
        y += 75
        self.filterSheet.moveSubfilterUp = SquareButton((15, y, buttonSize, buttonSize), u'⇡', sizeStyle='small', callback=self.moveSubfilterUp)
        self.filterSheet.moveSubfilterDown = SquareButton((15, y + buttonSize + gutter, buttonSize, buttonSize), u'⇣', sizeStyle='small', callback=self.moveSubfilterDown)

        if filterName == '':
            self.currentFilterName = ''

    def addArgument(self, sender):
        argumentsList = self.filterSheet.arguments.get()
        argumentsList.append({'argument': 'rename me', 'value': 50, 'min': 0, 'max': 100})
        if len(argumentsList) > 0:
            self.filterSheet.removeArgument.enable(True)
        self.filterSheet.arguments.set(argumentsList)

    def removeArgument(self, sender):
        argumentsList = self.filterSheet.arguments.get()
        if len(argumentsList) == 0:
            self.filterSheet.removeArgument.enable(False)
        selection = self.filterSheet.arguments.getSelection()[0]
        argumentsList.pop(selection)
        self.filterSheet.arguments.set(argumentsList)

    def addSubfilter(self, sender):
        subfiltersList = self.filterSheet.subfilters.get()
        subfilterDict = {'filterName': 'get', 'mode': '', 'source': ''}
        subfiltersList.append(subfilterDict)
        if len(subfiltersList) > 0:
            self.filterSheet.removeSubfilter.enable(True)
        self.filterSheet.subfilters.set(subfiltersList)
        if not self.filterSheet.new:
            self.filters[self.currentFilterName].addSubfilter('get')

    def removeSubfilter(self, sender):
        subfiltersList = self.filterSheet.subfilters.get()
        if len(subfiltersList) == 0:
            self.filterSheet.removeSubfilter.enable(False)
        selection = self.filterSheet.subfilters.getSelection()[0]
        subfiltersList.pop(selection)
        self.filterSheet.subfilters.set(subfiltersList)
        if not self.filterSheet.new:
            self.filters[self.currentFilterName].removeSubfilter(selection)

    def moveSubfilterUp(self, sender):
        subfiltersList = self.filterSheet.subfilters.get()
        nItems = len(subfiltersList)
        if nItems > 1:
            selection = self.filterSheet.subfilters.getSelection()[0]
            if selection > 0:
                itemToMove = subfiltersList.pop(selection)
                subfiltersList.insert(selection-1, itemToMove)
                self.filterSheet.subfilters.set(subfiltersList)
                if not self.filterSheet.new:
                    self.filters[self.currentFilterName].reorderSubfilters(selection, selection-1)

    def moveSubfilterDown(self, sender):
        subfiltersList = self.filterSheet.subfilters.get()
        nItems = len(subfiltersList)
        if nItems > 1:
            selection = self.filterSheet.subfilters.getSelection()[0]
            if selection < nItems-1:
                itemToMove = subfiltersList.pop(selection)
                subfiltersList.insert(selection+1, itemToMove)
                self.filterSheet.subfilters.set(subfiltersList)
                if not self.filterSheet.new:
                    self.filters[self.currentFilterName].reorderSubfilters(selection, selection+1)

    def getFile(self, sender):
        path = getFile(fileTypes=['py'], allowsMultipleSelection=False, resultCallback=self.loadFilePath, parentWindow=self.filterSheet)

    def loadFilePath(self, paths):
        path = paths[0]
        self.filterSheet.importPath[1].pathInput.set(path)

    def closeFilterSheet(self, sender):
        self.filterSheet.close()
        delattr(self, 'filterSheet')

    def processFilter(self, sender):
        argumentsList = self.filterSheet.arguments.get()
        filterName = self.filterSheet.name.get()
        index = self.filterSheet.index
        filterDict = {}

        if len(filterName) > 0:
            sourceIndex = self.filterSheet.importPath.get()
            mode = ['module','file'][sourceIndex]
            importString = self.filterSheet.importPath[sourceIndex].pathInput.get()

            if len(importString) > 0:
                filterDict[mode] = importString

                filterObjectName = self.filterSheet.filterObject.get()
                filterDict['filterObjectName'] = filterObjectName

                if len(filterObjectName) > 0:

                    for argItem in argumentsList:
                        if 'argument' in argItem:
                            key = argItem['argument']
                            if 'value' in argItem:
                                value = self.parseValue(argItem['value'])
                                if 'arguments' not in filterDict:
                                    filterDict['arguments'] = OrderedDict()
                                filterDict['arguments'][key] = value
                                if 'min' in argItem and 'max' in argItem and isinstance(value, (float, int)):
                                    try:
                                        mini, maxi = float(argItem['min']), float(argItem['max'])
                                        if 'limits' not in filterDict:
                                            filterDict['limits'] = {}
                                        filterDict['limits'][key] = (mini, maxi)
                                    except:
                                        pass

                    if filterName in self.filters:
                        self.filters.setFilter(filterName, filterDict)

                    elif self.filterSheet.new == False:
                        index = self.filterSheet.index
                        self.filters.changeFilterNameByIndex(index, filterName)
                        self.filters.setFilter(filterName, filterDict)

                    elif self.filterSheet.new == True:
                        self.filters.setFilter(filterName, filterDict)

                    self.closeFilterSheet(sender)
                    self.updateFiltersList(index)
                    self.updateControls()
                    self.resetRepresentations()
                    self.updatePreview()
                    self.saveFiltersToExtensionDefault()

    def processFilterGroup(self, sender):
        filterName = self.filterSheet.name.get()
        subfiltersList = self.filterSheet.subfilters.get()
        isNew = self.filterSheet.new
        index = self.filterSheet.index
        subfilters = []

        for item in subfiltersList:
            subfilterName = item['filterName'] if 'filterName' in item else ''
            mode = item['mode'] if 'mode' in item else None
            source = item['source'] if 'source' in item else None
            try:
                source = int(source)
            except:
                pass
            subfilters.append((subfilterName, mode, source))

        if filterName in self.filters:
            self.filters.updateFilterChain(filterName, subfilters)
        elif not isNew:
            self.filters.changeFilterNameByIndex(index, filterName)
            self.filters.updateFilterChain(filterName, subfilters)
        elif isNew:
            self.filters.setFilterChain(filterName, subfilters)

        self.closeFilterSheet(sender)
        self.updateFiltersList(index)
        self.updateControls()
        self.resetRepresentations()
        self.updatePreview()
        self.saveFiltersToExtensionDefault()

    def addFilter(self, sender):
        self.buildFilterSheet(makeNew=True)
        self.filterSheet.open()

    def addFilterChain(self, sender):
        self.buildFilterGroupSheet(makeNew=True)
        self.filterSheet.open()

    def addExternalFilter(self, filterName, filterDict):
        self.filters.addFilter(filterName, filterDict)
        self.updateFiltersList()

    def removeFilter(self, sender):
        filterName = self.currentFilterName
        self.filters.removeFilter(filterName)
        self.updateFiltersList()

    def filterSelectionChanged(self, sender):
        selectedFilterName = self.getSelectedFilterName()
        self.initCachedFont()
        self.currentFilterName = selectedFilterName
        self.updateControls()
        self.updatePreview()

    def getSelectedFilterName(self):
        filtersList = self.w.filtersPanel.filtersList
        filterNamesList = filtersList.get()
        if len(filterNamesList):
            selectedIndices = filtersList.getSelection()
            if len(selectedIndices):
                selection = filtersList.getSelection()[0]
                return filterNamesList[selection]
        return None

    def parseValue(self, value):
        if isinstance(value, bool):
            value = bool(value)
        elif isinstance(value, (str, unicode)) and value.lower() == 'true':
            value = True
        elif isinstance(value, (str, unicode)) and value.lower() == 'false':
            value = False
        elif value is not '' or value is not None:
            try:
                value = float(value)
            except:
                pass
        return value

    def initCachedFont(self):
        currentFont = self.currentFont
        self.cachedFont = RFont(showUI=False)
        if currentFont is not None:
            for metric in ['ascender','descender','unitsPerEm']:
                setattr(self.cachedFont.info, metric, getattr(currentFont.info, metric))

    def fontChanged(self, notification):
        if 'font' in notification:
            self.releaseObservedGlyphs()
            self.stringInput(self.w.textInput)
            self.currentFont = notification['font']
            self.initCachedFont()
            self.updatePreview()

    def releaseObservedGlyphs(self):
        for glyph in self.observedGlyphs:
            glyph.removeObserver(self, 'Glyph.Changed')
        self.observedGlyphs = []

    def glyphChanged(self, notification):
        glyph = notification.object
        glyph.destroyAllRepresentations()
        self.updatePreview()

    def launchWindow(self):
        postEvent("PenBallWizardSubscribeFilter", subscribeFilter=self.addExternalFilter)

    def saveFiltersToExtensionDefault(self):
        setExtensionDefault('{0}.filtersList'.format(PENBALLWIZARD_EXTENSIONKEY), self.filters.asList())

    def end(self, notification):
        #self.filters.saveFiltersToJSON('/'.join([LOCALPATH, JSONFILE]))
        self.saveFiltersToExtensionDefault()
        self.releaseObservedGlyphs()
        for callback, event in self.observers:
            removeObserver(self, event)

PenBallWizardController()

# if __name__ == '__main__':

#     import unittest