#coding=utf-8
import sys
import imp
import json
from collections import OrderedDict

from robofab.world import RGlyph
from defcon import addRepresentationFactory, removeRepresentationFactory
from booleanOperations.booleanGlyph import BooleanGlyph

from errorGlyph import ErrorGlyph
from glyphFilter import GlyphFilter
from glyphUtils import passThrough, removeOverlap, reverseContours

FACTORYKEYPREFIX = 'com.loicsander.glyphFilter.factory'
FILTERARGSEPARATOR = '.'
_addedRepresentationFactories = []


def makeFilterKey(filterName):
    return '{0}.{1}'.format(FACTORYKEYPREFIX, filterName)


class PenBallBaseFilter(object):


    def __init__(self, filterName):
        self._name = filterName
        self.arguments = {}


    def __call__(self, glyph):
        return self.filterGlyph(glyph, self.arguments)


    def _get_index(self):
        assert self._parent is not None
        return self._parent.filterNames.index(self._name)

    index = property(_get_index)

    def filterGlyph(self, glyph, arguments={}):
        key = makeFilterKey(self.name)
        return glyph.getRepresentation(key, **arguments)


    def _get_publicName(self):
        return self._name
    name = property(_get_publicName, doc="Return the official filter name.")


    def _makeGlyphFilter(self):
        pass


    def hasArguments(self):
        return len(self.arguments) > 0


    def getArguments(self):
        return self.arguments.keys()


    def setArguments(self, arguments, keepExisting=False):
        for arg, value in arguments.items():
            if keepExisting == False or (keepExisting == True and arg not in self.arguments):
                self.setArgumentValue(arg, value)


    def setArgumentValue(self, argumentName, argumentValue):
        self.arguments[argumentName] = argumentValue


    def getArgumentValue(self, argumentName):
        if argumentName in self.arguments:
            return self.arguments[argumentName]
        else:
            raise KeyError(argumentName)


    def getLimit(self, argumentName):
        if argumentName in self.limits:
            return self.limits[argumentName]
        return None


    def _filterObjectToRepresentationFactory(self):
        theFilter = self._makeGlyphFilter()

        key = makeFilterKey(self.name)
        if key in _addedRepresentationFactories:
            removeRepresentationFactory(key)
        elif key not in _addedRepresentationFactories:
            _addedRepresentationFactories.append(key)
        addRepresentationFactory(key, theFilter)



class PenBallFilter(PenBallBaseFilter):
    """Convenience object handling glyphFilter meta/data."""

    _inputDataKeys = ['arguments', 'limits', 'module', 'file', 'filterObjectName', 'filterObject']


    def __init__(self, parent, filterName, filterDict):
        self._parent = parent
        self._name = filterName
        self.arguments = {}
        self.limits = {}
        for key in self._inputDataKeys:
            if key in filterDict:
                if key == 'arguments':
                    entry = OrderedDict(filterDict[key])
                else:
                    entry = filterDict[key]
                setattr(self, key, entry)
        if not hasattr(self, 'filterObjectName') and hasattr(self, 'filterObject'):
            self.filterObjectName = self.filterObject.__name__
        self._loadFilterObject()
        self._filterObjectToRepresentationFactory()


    def __repr__(self):
        return "('{0}', {1})".format(*self.asTuple())


    def __str__(self):
        return 'PenBallFilter {name} ({objectName})'.format(
                name = self.name,
                objectName = self.objectName
            )


    def __contains__(self, key):
        return key in self.arguments.keys()


    def __getitem__(self, key):
        if key in self.arguments:
            return self.arguments[key]
        else:
            raise KeyError


    def asTuple(self):
        return (self.name, self.getFilterDict())


    def getFilterDict(self):
        filterDict = {
                    'filterObjectName': self.objectName,
                    'arguments': [(arg, value) for arg, value in self.arguments.items()],
                    'limits': self.limits,
                }
        source = 'module' if hasattr(self, 'module') else 'file' if hasattr(self, 'file') else None
        if source is not None:
            filterDict[source] = getattr(self, source)
        return filterDict


    def _get_privateName(self):
        return self.filterObjectName
    objectName = property(_get_privateName, doc="Return the name of the filter object: pen or function.")


    def _get_filterObject(self):
        return self.filterObject
    object = property(_get_filterObject, doc="Return the filter object: pen or function.")


    def _makeGlyphFilter(self):
        return GlyphFilter(self.object, self.arguments)

    def getLimits(self, argumentName):
        if argumentName in self.arguments:
            if argumentName in self.limits:
                return self.limits[argumentName]
            else:
                return None
        else:
            raise KeyError(argumentName)


    def _loadFilterObject(self):
        if hasattr(self, 'module'):
            self.filterObject = self._loadFilterFromModule(self.module, self.objectName)
        elif hasattr(self, 'file'):
            self.filterObject = self._loadFilterFromPath(self.file, self.objectName)


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



class PenBallFilterChain(PenBallBaseFilter):
    """A shallow filter that accumulates effects from a series of subfilters by referencing them."""


    def __init__(self, parent, filterName, subfilters=[], arguments={}):
        self._parent = parent
        self._name = filterName
        self.arguments = OrderedDict(arguments)
        self.subfilters = []
        for subfilterName, mode, source in subfilters:
            self.setSubfilter(subfilterName, mode, source, True)
        self._filterObjectToRepresentationFactory()


    def __repr__(self):
        return '("{0}", {1}, {2})'.format(*self.asTuple())


    def __str__(self):
        return 'PenBallOperation {name} [{subfilters}])'.format(
                name = self.name,
                subfilters = ', '.join([str(subfilter) for subfilter in self.subfilters])
                )


    def __len__(self):
        return len(self.subfilters)


    def asTuple(self):
        return (self.name, self.subfilters, self.arguments)


    def setParent(self, manager):
        self._parent = manager


    def getParent(self):
        assert self._parent is not None
        return self._parent


    def addSubfilter(self, filterName):
        self.setSubfilter(filterName, None, None)


    def removeSubfilter(self, index):
        self.subfilters.pop(index)
        for arg in self.arguments:
            subfilterName, argumentName, filterOrder = self.splitSubfilterArgumentName(arg)
            if filterOrder == index:
                self.arguments.pop(arg, 0)


    def reorderSubfilters(self, previousIndex, newIndex):
        if previousIndex < newIndex:
            movedSubftiler = self.subfilters.pop(previousIndex)
            self.subfilters.insert(newIndex, movedSubftiler)
        elif previousIndex > newIndex:
            movedSubftiler = self.subfilters.pop(previousIndex)
            self.subfilters.insert(newIndex, movedSubftiler)

        changedArguments = {}

        for arg in self.arguments:
            subfilterName, argumentName, filterOrder = self.splitSubfilterArgumentName(arg)
            if filterOrder == previousIndex:
                newArg = self.joinSubfilterArgumentName(subfilterName, argumentName, newIndex)
                changedArguments[newArg] = self.arguments[arg]
                self.arguments.pop(arg, 0)
            elif previousIndex < filterOrder < newIndex:
                newArg = self.joinSubfilterArgumentName(subfilterName, argumentName, filterOrder-1)
                changedArguments[newArg] = self.arguments[arg]
                self.arguments.pop(arg, 0)
            elif previousIndex > filterOrder > newIndex:
                newArg = self.joinSubfilterArgumentName(subfilterName, argumentName, filterOrder+1)
                changedArguments[newArg] = self.arguments[arg]
                self.arguments.pop(arg, 0)
            elif filterOrder == newIndex and previousIndex < newIndex:
                newArg = self.joinSubfilterArgumentName(subfilterName, argumentName, filterOrder-1)
                changedArguments[newArg] = self.arguments[arg]
                self.arguments.pop(arg, 0)
            elif filterOrder == newIndex and previousIndex > newIndex:
                newArg = self.joinSubfilterArgumentName(subfilterName, argumentName, filterOrder+1)
                changedArguments[newArg] = self.arguments[arg]
                self.arguments.pop(arg, 0)

        for key in changedArguments:
            self.setArgumentValue(key, changedArguments[key])


    def setSubfilter(self, filterName, mode, source, keepExisting=False):
        assert self._parent is not None
        if filterName in self._parent and self._parent.hasSubfilters(filterName) == False:
            filterOrder = len(self)
            theFilter = self.getSubfilter(filterName)
            arguments = {self.joinSubfilterArgumentName(filterName, arg, filterOrder): value for arg, value in theFilter.arguments.items()}
            if len(arguments):
                self.setArguments(arguments, keepExisting)
            self.subfilters.append((filterName, mode, source))


    def getSubfilter(self, subfilterName):
        return self._parent.getFilter(subfilterName)


    def getLimits(self, argumentName):
        subfilterName, argumentName, filterOrder = self.splitSubfilterArgumentName(argumentName)
        if (subfilterName, argumentName) != (None, None):
            subfilter = self.getSubfilter(subfilterName)
            return subfilter.getLimit(argumentName)
        return None


    def joinSubfilterArgumentName(self, subfilterName, argumentName, filterOrder):
        return '{1}{0}{2}{0}{3}'.format(FILTERARGSEPARATOR, subfilterName, argumentName, filterOrder)


    def splitSubfilterArgumentName(self, argumentName):
        try:
            subfilterName, argumentName, order = argumentName.split(FILTERARGSEPARATOR)
            return subfilterName, argumentName, int(order)
        except ValueError:
            print 'Invalid argument: {0}, should be in the form <subfilter{1}argumentName{1}order>'.format(argumentName, FILTERARGSEPARATOR)
            return None, None, None
        except Exception as e:
            print e

    def _makeGlyphFilter(self):

        def filterGroup(glyph, font=None, **overrideGlobalArguments):
            globalArguments = {self.splitSubfilterArgumentName(argumentName): self.arguments[argumentName] for argumentName in self.arguments}
            for key in overrideGlobalArguments:
                _subfilterName_, _overrideArgumentName_, _filterOrder_ = self.splitSubfilterArgumentName(key)
                if (_subfilterName_, _overrideArgumentName_) != (None, None):
                    globalArguments[(_subfilterName_, _overrideArgumentName_, _filterOrder_)] = overrideGlobalArguments[key]

            subfilters = [(self.getSubfilter(subfilterName), mode, source) for subfilterName, mode, source in self.subfilters]
            error = False
            canvasGlyph = RGlyph()
            canvasPen = canvasGlyph.getPen()
            canvasGlyph.width = glyph.width
            glyph.draw(canvasPen)

            steps = []

            for i, (currentFilter, mode, source) in enumerate(subfilters):

                if error == True:
                    continue

                if not source:
                    sourceGlyph = canvasGlyph
                else:
                    try:
                        sourceGlyph = steps[source-1]
                    except:
                        layerGlyph = glyph.getLayer(source)
                        if len(layerGlyph) > 0:
                            sourceGlyph = RGlyph()
                            pen = sourceGlyph.getPen()
                            layerGlyph.draw(pen)
                        else:
                            sourceGlyph = canvasGlyph

                sourceGlyph.name = glyph.name

                arguments = {argumentName: globalArguments[(subfilterName, argumentName, filterOrder)] for subfilterName, argumentName, filterOrder in globalArguments if subfilterName == currentFilter.name and filterOrder == i}
                processedGlyph = currentFilter.filterGlyph(sourceGlyph, arguments)

                steps.append(processedGlyph)

                if mode == 'ignore' and len(steps) > 1:
                    processedGlyph = steps[-2]
                elif mode == 'ignore':
                    processedGlyph = sourceGlyph

                if mode in ['union', 'difference', 'intersection', 'xor']:
                    try:
                        b1 = BooleanGlyph(canvasGlyph)
                        b2 = BooleanGlyph(processedGlyph)
                        operation = getattr(b1, mode)
                        processedGlyph = operation(b2)
                    except:
                        error = True

                if mode != 'add':
                    canvasGlyph.clear()

                processedGlyph.draw(canvasPen)

                if processedGlyph.width:
                    canvasGlyph.width = processedGlyph.width

            if error == True:
                canvasGlyph = ErrorGlyph()
            elif error == False:
                canvasGlyph.name = glyph.name

            canvasGlyph.unicode = glyph.unicode
            if canvasGlyph.width is None:
                canvasGlyph.width = glyph.width
            return canvasGlyph

        return filterGroup



class PenBallFiltersManager(object):
    """Handling a collection of filters, the manager is in charge of retrieving/storing them"""

    internalFilters = {
        'get': { 'filterObject': passThrough, },
        'reverse': { 'filterObject': reverseContours, },
        'removeOverlap': { 'filterObject': removeOverlap, }
    }

    def __init__(self, filtersList=[]):
        self.filterNames = []
        self.filters = {}
        for key in self.internalFilters:
            self.setFilter(key, self.internalFilters[key])
        self.loadFiltersList(filtersList)


    def __contains__(self, key):
        return key in self.filterNames or key in self.internalFilters


    def __iter__(self):
        for key in self.filterNames:
            yield self.filters[key]


    def __getitem__(self, key):
        return self.getFilter(key)


    def __repr__(self):
        return repr(self.asList())


    def keys(self):
        return [filterName for filterName in self.filterNames if filterName not in self.internalFilters]


    def asList(self):
        return [self.filters[key].asTuple() for key in self.keys()]


    def hasSubfilters(self, filterName):
        if filterName in self:
            theFilter = self.getFilter(filterName)
            return hasattr(theFilter, 'subfilters')
        return False


    def getFilter(self, key):
        if key in self.filterNames:
            return self.filters[key]
        elif key in self.internalFilters:
            return self.filters[key]
        else:
            return self.filters['get']


    def setFilter(self, filterName, filterDict):
        if filterName not in self.filterNames and filterName not in self.internalFilters:
            self.filterNames.append(filterName)
        self.filters[filterName] = PenBallFilter(self, filterName, filterDict)


    def setFilterChain(self, filterName, subfilters, arguments={}):
        if filterName not in self.filterNames:
            self.filterNames.append(filterName)
        filterChain = PenBallFilterChain(self, filterName, subfilters, arguments)
        self.filters[filterName] = filterChain


    def updateFilterChain(self, filterName, subfilters):
        if filterName not in self.filterNames:
            self.filterNames.append(filterName)
        arguments = self.filters[filterName].arguments
        filterChain = PenBallFilterChain(self, filterName, subfilters, arguments)
        self.filters[filterName] = filterChain


    def removeFilter(self, filterName):
        if filterName in self.filterNames:
            self.filterNames.remove(filterName)
            self.filters.pop(filterName, 0)


    def changeFilterName(self, oldName, newName):
        index = self.filterNames.index(oldName)
        if index is not None:
            self.changeFilterNameByIndex(index, newName)


    def changeFilterNameByIndex(self, index, newName):
        if index < len(self.filterNames):
            oldName = self.filterNames[index]
            self.filterNames[index] = newName
            movedFilter = self.filters[oldName]
            self.filters[newName] = movedFilter
            self.filters.pop(oldName, 0)


    def setFilterArguments(self, filterName, arguments, keepExisting=False):
        if filterName in self:
            theFilter = self.getFilter(filterName)
            theFilter.setArguments(arguments, keepExisting)


    def setArgumentValue(self, filterName, argumentName, argumentValue):
        theFilter = self.getFilter(filterName)
        theFilter.setArgumentValue(argumentName, argumentValue)


    def loadFiltersList(self, filtersList):
        filtersList.sort(key=lambda a: len(a))
        for filterList in filtersList:
            if len(filterList) == 2:
                try:
                    filterName, filterDict = filterList
                    self.setFilter(filterName, filterDict)
                except:
                    continue
            elif len(filterList) == 3:
                try:
                    filterName, subfilters, arguments = filterList
                    self.setFilterChain(filterName, subfilters, arguments)
                except:
                    continue


    def loadFiltersFromJSON(self, filePath):
        try:
            filtersFile = open(filePath, 'r')
            rawFilters = filtersFile.read()
            filtersList = json.loads(rawFilters)
            self.loadFiltersList(filtersList)
            filtersFile.close()
        except IOError as e:
            print 'Could not open file {0}'.format(e)

    def saveFiltersToJSON(self, filePath):
        filtersToFile = self.asList()
        with open(filePath, 'w+') as f:
            j = json.dumps(filtersToFile, indent=4)
            f.write(j)
            f.close()



if __name__ == '__main__':

    import unittest
    from defcon import Glyph
    import robofab.pens.filterPen as filterPens


    class TestPenBallFilterManager(unittest.TestCase):

        # def setUp(self):
        #     self.manager = PenBallFiltersManager()

        def test_FiltersManager(self):
            manager = PenBallFiltersManager()
            manager.setFilter('Flatten', {
                'module': 'robofab.pens.filterPen',
                'filterObjectName': 'FlattenPen',
                'arguments': {
                    'approximateSegmentLength': 5
                }
                })
            manager.setFilter('Spike', {
                'module': 'robofab.pens.filterPen',
                'filterObjectName': 'spikeGlyph',
                'arguments': {
                    'spikeLength': 20,
                    'segmentLength': 20,
                    }
                })
            manager.setFilter('Threshold', {
                'module': 'robofab.pens.filterPen',
                'filterObjectName': 'ThresholdPen',
                'arguments': {
                    'threshold': 20,
                    }
                })
            manager.setFilterChain(
                'Flatten&Spike',
                [
                    ('Flatten', None, None),
                    ('Spike', None, None),
                    ('Threshold', None, None)
                ]
                )

    unittest.main()
