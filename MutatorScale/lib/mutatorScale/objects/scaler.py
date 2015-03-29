#coding=utf-8
from __future__ import division

from robofab.world import RGlyph
from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator

from time import time

from meus.mutatorScale.objects.fonts import MutatorScaleFont
from meus.mutatorScale.objects.glyphs import errorGlyph
from meus.mutatorScale.utilities.font import makeListFontName
from meus.mutatorScale.utilities.numbers import mapValue

operationalTime = []

class MutatorScaleEngine:

    '''
    This object is built to handle the interpolated scaling of glyphs using MutatorMath.
    It requires a list of fonts (at least two) from which it determines which kind of interpolation it can achieve.
    Maybe I should state the obvious: the whole process is based on the assumption that the provided fonts are compatible for interpolation.
    With existing masters, the object is then set to certain parameters that allow for specific glyph scaling operations,
    while scaling, a MutatorScaleEngine attempts to obtain specified weight and contrast for the scaled glyph
    by interpolating accordingly and to the best possible result with available masters.

    Each master in a MutatorScaleEngine is an instance of a MutatorScaleFont for which stem values are defined.
    If not specifically provided, these stem values are measured on capital letters I and H for vertical and horizontal stems respectively.
    The stem values obtained are only meant to be reference value and do not reflect the stem values of all glyphs but only of I and H.
    While scaling, if you ask for a scaled glyph with stem values (80, 60), you’re effectively asking for a scaledGlyph interpolated
    as to have the vertical stem of a I equal to 80 and the horizontal stem of a H equal to 60. It is not akin to ask that these stem values
    are applied to the exact glyph you asked for, that’s not how interpolation works.

    When a MutatorScaleEngine is asked for a scaled glyph with specific horizontal and vertical stem values,
    here’s what happens:
    – it collects glyphs corresponding to the glyphName passed to .getScaledGlyph() in the available masters;
    – it scales all the master glyphs to the proportions to which the MutatorScaleEngine is set;
    – it then builds a MutatorMath space in which masters are placed according to their horizontal and vertical stem values scaled down;
    – finally, it returns a scaled down (as all masters are) interpolated glyph with the asked for stem values.

    #####

    Here’s how it goes:

    > scaler = MutatorScaleEngine(ListOfFonts)
    > scaler.set({
        'scale': (1.03, 0.85)
        })
    > scaler.getScaledGlyph('a', ())
    '''

    errorGlyph = errorGlyph()

    def __init__(self, masterFonts=[], stemsWithSlantedSection=False):
        self.masters = {}
        self._currentScale = None
        self.stemsWithSlantedSection = stemsWithSlantedSection
        for font in masterFonts:
            self.addMaster(font)

    def __repr__(self):
        return 'MutatorScaleEngine # %s masters\n- %s\n' % (len(self.masters), '\n- '.join([str(master) for master in self.masters]))

    def __getitem__(self, key):
        if key in self.masters.keys():
            return self.masters[key]
        else:
            raise KeyError(key)

    def __iter__(self):
        for master in self.masters.values():
            yield master

    def __len__(self):
        return len(self.masters)

    def __contains__(self, fontName):
        return fontName in self.masters

    def set(self, scalingParameters):
        '''
        Defining the scaling parameters.
        '''

        scale = (1, 1)

        if scalingParameters.has_key('width'):
            width = scalingParameters['width']
            scale = (width, 1)
        else:
            width = 1

        if scalingParameters.has_key('scale'):
            scale = scalingParameters['scale']
            if isinstance(scale, (float, int)):
                scale = (scale, scale)

        elif  scalingParameters.has_key('targetHeight') and scalingParameters.has_key('referenceHeight'):
            targetHeight = scalingParameters['targetHeight']
            referenceHeight = scalingParameters['referenceHeight']
            scale = (width, targetHeight, referenceHeight)

        for master in self.masters.values():
            master.setScale(scale)

        self._currentScale = scale

    def makeMaster(self, font, stems=None):
        '''
        Returning a MutatorScaleEngine master.
        '''
        name = makeListFontName(font)
        master = MutatorScaleFont(font, stems, stemsWithSlantedSection=self.stemsWithSlantedSection)
        return name, master

    def addMaster(self, font, stems=None):
        name, master = self.makeMaster(font, stems)
        if self._currentScale is not None:
            master.setScale(self._currentScale)
        self.masters[name] = master

    def removeMaster(self, font):
        name = makeListFontName(font)
        if self.masters.has_key(name):
            self.masters.pop(name, 0)

    def getScaledGlyph(self, glyphName, stemTarget):
        '''
        Returns an interpolated & scaled glyph according to set parameters and given masters.
        '''
        masters = self.masters.values()
        twoAxes = self.checkForTwoAxes(masters)
        mutatorMasters = []
        yScales = []

        '''
        Gather master glyphs for interpolation:
        each master glyph is scaled down according to set parameter,
        it is then inserted in a mutator design space with scaled down stem values
        so asking for the initial stem values of a scaled down glyphName
        will result in an scaled glyph which will retain specified stem widths.
        '''

        if len(masters) > 1:

            for master in masters:

                xScale, yScale = master.getScale()
                yScales.append(yScale)

                if glyphName in master:
                    masterGlyph = master[glyphName]

                    if twoAxes == True:
                        axis = {
                            'vstem': master.vstem * xScale,
                            'hstem': master.hstem * yScale
                            }
                    else:
                        axis = {
                            'stem': master.vstem * xScale
                        }

                    mutatorMasters.append((Location(**axis), masterGlyph))

            medianYscale = sum(yScales) / len(yScales)
            targetLocation = self._getTargetLocation(stemTarget, masters, twoAxes, (xScale, medianYscale))

            instanceGlyph = self._getInstanceGlyph(targetLocation, mutatorMasters)
            instanceGlyph.round()

            return instanceGlyph
        return

    def _getInstanceGlyph(self, location, masters):
        I = self._getInstance(location, masters)
        if I is not None:
            return I.extractGlyph(RGlyph())
        else:
            return self.errorGlyph

    def _getInstance(self, location, masters):
        try:
            b, m = buildMutator(masters)
            if m is not None:
                instance = m.makeInstance(location)
                return instance
        except:
            return

    def _getTargetLocation(self, stemTarget, masters, twoAxes, (xScale, yScale)):
        '''
        Returns a proper Location object for a scaled glyph instance,
        the essential part lies in the conversion of stem values,
        so that in anisotropic mode, a MutatorScaleEngine can attempt to produce
        a glyph with proper stem widths without requiring two-axes interpolation.
        '''

        targetVstem, targetHstem = None, None

        try: targetVstem, targetHstem = stemTarget
        except: targetVstem = stemTarget

        if targetHstem is not None:

            if twoAxes == False:
                vStems = [master.vstem*xScale for master in masters]
                hStems = [master.hstem*yScale for master in masters]
                (minVStem, minStemIndex), (maxVStem, maxStemIndex) = self._getExtremes(vStems)
                vStemSpan = (minVStem, maxVStem)
                hStemSpan = hStems[minStemIndex], hStems[maxStemIndex]
                newHstem = mapValue(targetHstem, hStemSpan, vStemSpan)
                return Location(stem=(targetVstem, newHstem))

            elif twoAxes == True:
                return Location(vstem=targetVstem, hstem=targetHstem)

        else:

            return Location(stem=targetVstem)

    def _getExtremes(self, values):
        '''
        Returns the minimum and maximum in a list of values with indices,
        this implementation was necessary to distinguish indices when min and max value happen to be equal (without being the same value per se).
        '''
        if len(values) > 1:
            baseValue = (values[0], 0)
            smallest, largest = baseValue, baseValue
            for i, value in enumerate(values[1:]):
                if value >= largest[0]:
                    largest = (value, (i+1))
                elif value < smallest[0]:
                    smallest = (value, (i+1))
            return smallest, largest
        return

    def checkForTwoAxes(self, masters=None):

        if masters is None:
            masters = self.masters.values()
        values = [master.hstem for master in masters]

        '''
        Checking if the conditions are met to have two-axis interpolation:
        1. At least two identical values (to bind a new axis to the first axis)
        2. At least one value different from the others (to be able to build a second axis)
        '''
        length = len(values)
        if length:
            identicalValues = 0
            differentValues = 0
            for i, value in enumerate(values):
                if i < length-1:
                    nextValue = values[i+1]
                    if nextValue == value: identicalValues += 1
                    if nextValue != value: differentValues += 1
            return bool(identicalValues) and bool(differentValues)
        return