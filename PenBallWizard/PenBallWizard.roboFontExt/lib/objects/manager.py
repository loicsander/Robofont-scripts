#coding=utf-8
import json
import os

from defcon import addRepresentationFactory
from glyphFilter import GlyphFilter

LOCALPATH = '/'.join(__file__.split('/')[:-1])
FACTORYKEYPREFIX = 'glyphFilter.'

def makeKey(filterName):
    return '{0}{1}'.format(FACTORYKEYPREFIX, filterName)

def getFileName(path):
    fileName = path.split('/')
    return fileName[-1][:-3]

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
    def __init__(self):
        self._loadFiltersList()
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
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return key in self.filterNames

    def __len__(self):
        return len(self.filterNames)

    def get(self):
        return self.filterNames

    def update(self):
        self._saveFiltersList()

    def setFilterArgument(self, filterName, argument, value):
        self.filters[filterName]['arguments'][argument] = value

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
        importString = None

        if filterDict.has_key('modulePath'):
            importString = 'from {modulePath} import {filterObject}'.format(**filterDict)

        elif filterDict.has_key('fileName'):
            fileName = filterDict['fileName']
            importString = 'from filterObjects.{fileName} import {filterObject}'.format(**filterDict)

        if importString is not None:
            extractArgumentsString = 'arguments = filterDict["arguments"] if filterDict.has_key("arguments") else {}'
            buildFilterString = 'newFilter = GlyphFilter({filterObject})'.format(**filterDict)
            key = makeKey(filterName)
            buildFactoryString = 'addRepresentationFactory("{0}", newFilter)'.format(key)
            for execString in [importString, extractArgumentsString, buildFilterString, buildFactoryString]:
                exec execString

    def _duplicateSourceFile(self, sourcePath, fileName):
        sourceFile = file(sourcePath).read()
        copiedFile = file('filterObjects/{0}.py'.format(fileName), 'w+')
        copiedFile.write(sourceFile)

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
        filterList = ( self.filterNames, self.filters )
        with open('/'.join((LOCALPATH, 'filtersList.json')), 'w') as f:
            j = json.dumps(filterList, indent=4)
            f.write(j)
            f.close()