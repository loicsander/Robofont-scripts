#coding=utf-8
import json
import os
import sys
import imp

from robofab.pens.reverseContourPointPen import ReverseContourPointPen
from defcon import addRepresentationFactory, removeRepresentationFactory
import glyphFilter
reload(glyphFilter)
from glyphFilter import GlyphFilter

LOCALPATH = '/'.join(__file__.split('/')[:-1])
FACTORYKEYPREFIX = 'glyphFilter.'
_addedRepresentationFactories = []

def copyContours(glyph):
    from robofab.world import RGlyph
    glyphCopy = RGlyph()
    glyphCopy.width = glyph.width
    pen = glyphCopy.getPen()
    glyph.draw(pen)
    return glyphCopy

def reverseContours(glyph):
    from robofab.world import RGlyph
    glyphCopy = RGlyph()
    glyphCopy.width = glyph.width
    pointPen = glyphCopy.getPointPen()
    reversePen = ReverseContourPointPen(pointPen)
    glyph.drawPoints(reversePen)
    return glyphCopy

def makeKey(filterName):
    return '{0}{1}'.format(FACTORYKEYPREFIX, filterName)

class FiltersManager(object):
    """
    Object that handles several glyphFilters.
    Each time a new filter is added to the manager,
    it is also added to defcon’s representation factories,
    so that any filtered representation can be called on any defcon based glyph.

    Filters are stored in a .json file next this .py file.
    Filters can be defined by two ways, either as modules or as paths to files.
    Linking to a file is an implicit request to move said file to a /pens folder next to this .py file.

    """

    internalGlyphMethods = {
        'copy': {
            'filterObject': copyContours,
            'arguments': {},
        },
        'reverse': {
            'filterObject': reverseContours,
            'arguments': {},
        }
    }

    def __init__(self):
        self._loadFiltersList()
        for key in self.internalGlyphMethods:
            self.filters[key] = self.internalGlyphMethods[key]
        for filterName, filterDict in self.filters.items():
            self._filterToReprFactory(filterName, filterDict)

    def __setitem__(self, key, value):
        if self.filters.has_key(key):
            self.filters[key] = value
        else:
            raise KeyError(key)

    def __getitem__(self, key):
        if self.filters.has_key(key):
            return self.filters[key]
        return None

    def __contains__(self, key):
        return key in self.filters.keys()

    def __len__(self):
        return len(self.filterNames)

    def isGroup(self, filterName):
        return self.filters[filterName].has_key('subfilters')

    def get(self):
        return self.filterNames

    def update(self):
        self._saveFiltersList()

    def setFilterArgument(self, filterName, argument, value):
        self.filters[filterName]['arguments'][argument] = value

    def addFilterGroup(self, filterName, filterNamesList):
        if filterName not in self.filterNames:
            self.filterNames.append(filterName)
        filterDict = { 'subfilters': filterNamesList }
        self.filters[filterName] = filterDict
        self.update()

    def addFilter(self, filterName, filterDict):
        if filterName not in self.filterNames:
            self.filterNames.append(filterName)
        self.filters[filterName] = filterDict
        self._filterToReprFactory(filterName, filterDict)
        self.update()

    def removeFilter(self, filterName):
        if self.filters.has_key(filterName):
            self.filterNames.remove(filterName)
            self.filters.pop(filterName, 0)
            self.update()

    def changeFilterName(self, oldName, newName):
        index = self.filterNames.index(oldName)
        if index is not None:
            self.changeFilterNameByIndex(index, newName)

    def changeFilterNameByIndex(self, index, newName):
        if index < len(self.filterNames):
            oldName = self.filterNames[index]
            self.filterNames[index] = newName
            filterDict = self.filters[oldName]
            self.filters[newName] = filterDict
            self._filterToReprFactory(newName, filterDict)
            self.filters.pop(oldName, 0)
            self._saveFiltersList()

    def _filterToReprFactory(self, filterName, filterDict):
        filterObjects = []

        if filterDict.has_key('subfilters'):
            filters = [(_filterName_, self.filters[_filterName_], _mode_, _source_) for _filterName_, _mode_, _source_ in filterDict['subfilters']]
        else:
            filters = [(filterName, filterDict, None, False)]

        for filterName_, filterDict_, mode_, source_ in filters:

            filterFunction = None
            argumentNames = filterDict_['arguments'].keys() if filterDict_.has_key('arguments') else []

            if filterDict_.has_key('filterObject'):
                filterObject = filterDict_['filterObject']

            elif filterDict_.has_key('module'):
                path, filterObjectName = filterDict_['module']
                filterObject = self._loadFilterFromModule(path, filterObjectName)

            elif filterDict_.has_key('file'):
                path, filterObjectName = filterDict_['file']
                filterObject = self._loadFilterFromPath(path, filterObjectName)

            if filterObject is not None:
                if not filterDict_.has_key('filterObject'):
                    filterDict_['filterObject'] = filterObject
                filterObjects.append((filterObject, argumentNames, mode_, source_))

        newFilter = GlyphFilter(*filterObjects)
        key = makeKey(filterName)
        if key in _addedRepresentationFactories:
            removeRepresentationFactory(key)
        elif key not in _addedRepresentationFactories:
            _addedRepresentationFactories.append(key)
        addRepresentationFactory(key, newFilter)

    def _loadFilterFromPath(self, path, functionName):
        """
        _loadFilterFromPath("path/to/a/python/file/withAPen.py", "myFilterPen")
        """
        try:
            f = open(path, "r")
            try:
                moduleName = "externalPenBallWizard{0}".format(path.split('/')[-1][:-3])
                if moduleName not in sys.modules:
                    module = imp.load_source(moduleName, path, f)
                else:
                    module = __import__(moduleName, fromlist=[functionName])
                result = getattr(module, functionName)
            except:
                result = None
            f.close()
            return result
        except IOError as e:
            print 'Couldn’t load file {0}'.format(e)

    def _loadFilterFromModule(self, module, functionName):
        """
        _loadFilterFromModule("robofab.pens.filterPen", "FlattenPen")
        """
        try:
            module = __import__(module, fromlist=[functionName])
            return getattr(module, functionName)
        except:
            return None

    def _loadFiltersList(self):
        filtersFile = open('/'.join((LOCALPATH, 'filtersList.json')), 'r')
        try:
            filtersList = filtersFile.read()
            if len(filtersList):
                self.filterNames, self.filters = json.loads(filtersList)
            else:
                self.filterNames, self.filters = [], {}
        except:
            self.filterNames, self.filters = [], {}
        filtersFile.close()

    def _saveFiltersList(self):
        filters = {filterName: filterDict for filterName, filterDict in self.filters.items() if filterDict.has_key('module') or filterDict.has_key('file') or filterDict.has_key('subfilters')}
        for fil in filters.values():
            if fil.has_key('filterObject'):
                fil.pop('filterObject', 0)
        filtersName = [filterName for filterName in self.filterNames if filterName in filters.keys()]
        filterList = ( filtersName, filters )
        with open('/'.join((LOCALPATH, 'filtersList.json')), 'w+') as f:
            j = json.dumps(filterList, indent=4)
            f.write(j)
            f.close()