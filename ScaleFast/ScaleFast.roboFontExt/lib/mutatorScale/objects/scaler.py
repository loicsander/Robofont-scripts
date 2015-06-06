#coding=utf-8
from __future__ import division

from robofab.world import RGlyph
from mutatorMath.objects.location import Location
from mutatorMath.objects.mutator import buildMutator

from mutatorScale.objects.fonts import MutatorScaleFont
from mutatorScale.objects.errorGlyph import ErrorGlyph
from mutatorScale.utilities.fontUtils import makeListFontName, joinFontName
from mutatorScale.utilities.numbersUtils import mapValue

class MutatorScaleEngine:
    """
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

    >>> scaler = MutatorScaleEngine(ListOfFonts)
    >>> scaler.set({
        'scale': (1.03, 0.85)
        })
    >>> scaler.getScaledGlyph('a', ())
    """

    errorGlyph = ErrorGlyph()

    def __init__(self, masterFonts=[], stemsWithSlantedSection=False):
        self.masters = {}
        self._currentScale = None
        self._workingStems = None
        self._transformations = {}
        self.stemsWithSlantedSection = stemsWithSlantedSection
        self._availableGlyphs = []
        for font in masterFonts:
            self.addMaster(font)
        self.mutatorErrors = []

    def __repr__(self):
        return 'MutatorScaleEngine # {0} masters\n- {1}\n'.format(len(self.masters), '\n- '.join([str(master) for master in self.masters]))

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

    def getMaster(self, font):
        """Returning a master by parsing a fonts name and returning it if it’s among masters."""
        name = makeListFontName(font)
        if name in self.masters:
            return self.masters[name]
        return

    def getMasterByName(self, familyName, styleName):
        name = joinFontName(familyName, styleName)
        if name in self:
            return self[name]

    def hasTwoAxes(self):
        if self._workingStems == 'both':
            return True
        else:
            return False

    def hasGlyph(self, glyphName):
        """Checking for glyph availability in all masters."""
        return glyphName in self._availableGlyphs

    def getReferenceGlyphNames(self):
        """Returning a list of glyphNames for valid reference glyphs,
        i.e., glyphs that are not empty so they can serve as height reference.
        """
        masters = self.masters.values()
        glyphNames = self._availableGlyphs
        validGlyphs_names = reduce(lambda a, b: list(set(a) & set(b)), [[glyphName for glyphName in glyphNames if len(master.glyphSet[glyphName])] for master in masters])
        return validGlyphs_names

    def set(self, scalingParameters):
        """Define scaling parameters.

        Collect relevant data in the various forms it can be input,
        produce a scale definition relevant to a ScaleFont object.
        """
        scale = (1, 1)
        width = 1

        if scalingParameters.has_key('width'):
            width = scalingParameters['width']
            scale = (width, 1)

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

    def update(self):
        self._determineWorkingStems()

    def _parseStemsInput(self, stems):
        if stems is None:
            vstem, hstem = None, None
        else:
            try: vstem, hstem = stems
            except: vstem, hstem = stems, None

        return vstem, hstem

    def _makeMaster(self, font, vstem, hstem):
        """Return a MutatorScaleFont."""
        name = makeListFontName(font)
        master = MutatorScaleFont(font, vstem=vstem, hstem=hstem, stemsWithSlantedSection=self.stemsWithSlantedSection)
        return name, master

    def addMaster(self, font, stems=None):
        """Add a MutatorScaleFont to masters."""

        vstem, hstem = self._parseStemsInput(stems)
        if (vstem is None) and ('I' not in font):
            vstem = len(self.masters) * 100

        name, master = self._makeMaster(font, vstem, hstem)

        if not len(self._availableGlyphs):
            self._availableGlyphs = master.keys()
        elif len(self._availableGlyphs):
            self._availableGlyphs = list(set(self._availableGlyphs) & set(master.keys()))

        if self._currentScale is not None:
            master.setScale(self._currentScale)

        self.masters[name] = master
        self.update()

    def removeMaster(self, font):
        """Remove a MutatorScaleFont from masters."""
        name = makeListFontName(font)
        if self.masters.has_key(name):
            self.masters.pop(name, 0)
        self.update()

    def getScaledGlyph(self, glyphName, stemTarget, slantCorrection=True, attributes=None):
        """Return an interpolated & scaled glyph according to set parameters and given masters."""
        masters = self.masters.values()
        workingStems = self._workingStems
        mutatorMasters = []
        yScales = []
        angles = []

        """
        Gather master glyphs for interpolation:
        each master glyph is scaled down according to set parameter,
        it is then inserted in a mutator design space with scaled down stem values.
        Asking for the initial stem values of a scaled down glyphName
        will result in an scaled glyph which will retain specified stem widths.
        """

        if len(masters) > 1 and workingStems is not None:

            medianYscale = 1
            medianAngle = 0

            for master in masters:

                xScale, yScale = master.getScale()
                vstem, hstem = master.getStems()
                yScales.append(yScale)

                if glyphName in master and vstem is not None and hstem is not None:
                    masterGlyph = master[glyphName]

                    if workingStems == 'both':
                        axis = {
                            'vstem': vstem * xScale,
                            'hstem': hstem * yScale
                            }
                    else:
                        if workingStems == 'vstem':
                            stem = vstem
                        elif workingStems == 'hstem':
                            stem = hstem

                        if slantCorrection == True:
                            # if interpolation is an/isotropic
                            # skew master glyphs to upright angle to minimize deformations
                            angle = master.italicAngle

                            if angle:
                                masterGlyph.skewX(angle)
                                angles.append(angle)

                        axis = { 'stem': stem * xScale }

                    mutatorMasters.append((Location(**axis), masterGlyph))

            if len(angles) and slantCorrection == True:
                # calculate a median slant angle
                # in case there are variations among masters
                # shouldn’t happen, most of the time
                medianAngle = sum(angles) / len(angles)

            medianYscale = sum(yScales) / len(yScales)


            targetLocation = self._getTargetLocation(stemTarget, masters, workingStems, (xScale, medianYscale))
            instanceGlyph = self._getInstanceGlyph(targetLocation, mutatorMasters)

            if instanceGlyph.name == '_error_':
                if self.hasGlyph(glyphName):
                    instanceGlyph.unicodes = masters[0][glyphName].unicodes
                self.mutatorErrors[-1]['glyph'] = glyphName
                self.mutatorErrors[-1]['masters'] = mutatorMasters

            if medianAngle and slantCorrection == True:
                # if masters were skewed to upright position
                # skew instance back to probable slant angle
                instanceGlyph.skew(-medianAngle)

            instanceGlyph.round()

            if attributes is not None:
                for attributeName in attributes:
                    value = attributes[attributeName]
                    setattr(instanceGlyph, attributeName, value)

            return instanceGlyph
        return ErrorGlyph('None')

    def _getInstanceGlyph(self, location, masters):
        I = self._getInstance(location, masters)
        if I is not None:
            return I.extractGlyph(RGlyph())
        else:
            errorMessage = self.mutatorErrors[-1]['error']
            return ErrorGlyph('Interpolation', errorMessage)

    def _getInstance(self, location, masters):
        try:
            b, m = buildMutator(masters)
            if m is not None:
                instance = m.makeInstance(location)
                return instance
        except Exception as e:
            self.mutatorErrors.append({'error':e.message})
            return None

    def _getTargetLocation(self, stemTarget, masters, workingStems, (xScale, yScale)):
        """
        Return a proper Location object for a scaled glyph instance,
        the essential part lies in the conversion of stem values.
        so that in anisotropic mode, a MutatorScaleEngine can attempt to produce
        a glyph with proper stem widths without requiring two-axes interpolation.
        """

        targetVstem, targetHstem = None, None

        try: targetVstem, targetHstem = stemTarget
        except: targetVstem = stemTarget

        if targetHstem is not None:

            if workingStems == 'both':
                return Location(vstem=targetVstem, hstem=targetHstem)

            elif workingStems == 'vstem':
                vStems = [master.vstem * xScale for master in masters]
                hStems = [master.hstem * yScale for master in masters]
                (minVStem, minStemIndex), (maxVStem, maxStemIndex) = self._getExtremes(vStems)
                vStemSpan = (minVStem, maxVStem)
                hStemSpan = hStems[minStemIndex], hStems[maxStemIndex]
                newHstem = mapValue(targetHstem, hStemSpan, vStemSpan)
                return Location(stem=(targetVstem, newHstem))

            elif workingStems == 'hstem':
                return Location(stem=targetHstem)

        else:

            return Location(stem=targetVstem)

    def _getExtremes(self, values):
        """
        Return the minimum and maximum in a list of values with indices,
        this implementation was necessary to distinguish indices when min and max value happen to be equal (without being the same value per se).
        """
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

    def _determineWorkingStems(self):
        """
        Check conditions are met for two-axis interpolation in MutatorMath:
        1. At least two identical values (to bind a new axis to the first axis)
        2. At least a third and different value (to be able to have a differential on second axis)
        """
        masters = self.masters.values()
        twoAxes = False
        stemMode = None
        stems = {
            'vstem': [master.vstem for master in masters],
            'hstem': [master.hstem for master in masters]
        }

        if len(masters) > 2:
            twoAxes = self._checkForTwoAxes(stems)

        if twoAxes == True:
            stemMode = 'both'

        elif twoAxes == False:
            for stemName in stems:
                stemValues = stems[stemName]
                diff = self._numbersHaveDifferential(stemValues)
                if diff == True:
                    stemMode = stemName
                    break

        self._workingStems = stemMode

    def _checkForTwoAxes(self, stemsList):
        """
        Check conditions are met for two-axis interpolation in MutatorMath:
        1. At least two identical values (to bind a new axis to the first axis)
        2. At least a third and different value (to be able to have a differential on second axis)
        """
        twoAxes = []
        vstems = stemsList['vstem']
        hstems = stemsList['hstem']
        twoAxes.append(self._numbersHaveDifferential(vstems))
        twoAxes.append(self._numbersHaveSplitDifferential(hstems))

        return bool(reduce(lambda a,b: a*b, twoAxes))

    def _numbersHaveSplitDifferential(self, values):
        """Looking for at least two similar values and one differing from the others."""
        length = len(values)
        if length > 1:
            identicalValues = 0
            differentValues = 0
            for i, value in enumerate(values):
                if i < length-1:
                    nextValue = values[i+1]
                    if value is not None:
                        if nextValue == value: identicalValues += 1
                        if nextValue != value: differentValues += 1
            return bool(identicalValues) and bool(differentValues)
        return False

    def _numbersHaveDifferential(self, values):
        """Looking for at least two different values in a bunch."""
        length = len(values)
        if length > 1:
            differentValues = 0
            for i, value in enumerate(values):
                if i < length-1:
                    nextValue = values[i+1]
                    if nextValue != value and value is not None: return True
        return False

    def getMutatorReport(self):
        return self.mutatorErrors


if __name__ == '__main__':

    import os
    import unittest
    import glob
    from defcon import Font

    class MutatorScaleEngineTest(unittest.TestCase):

        def setUp(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            libFolder = os.path.join(libFolder, 'testFonts/')
            self.scalers = []
            self.loadedFonts = []
            self.glyphNames = ['H','I']
            for fontsFolder in ['two-axes','isotropic-anisotropic']:
                fonts = []
                fontsPath = os.path.join(libFolder, fontsFolder)
                os.chdir(fontsPath)
                for singleFontPath in glob.glob('*.ufo'):
                    font = Font(singleFontPath)
                    if 'Italic' not in font.info.styleName:
                        fonts.append(font)
                        self.loadedFonts.append(font)
                scaler = MutatorScaleEngine(fonts)
                self.scalers.append(scaler)

        def test_if_scalingEngine_has_glyph(self):
            """Checking if glyph is present among all scaling masters."""
            for scaler in self.scalers:
                for glyphName in self.glyphNames:
                    hasGlyph = scaler.hasGlyph(glyphName)
                    self.assertTrue(hasGlyph)

        def test_get_list_of_non_empty_glyph(self):
            """Checking if glyph is present among all scaling masters."""
            for scaler in self.scalers:
                scaler.getReferenceGlyphNames()

        def test_setting_up_simple_scale(self):
            """Test setting up simple scale on a MutatorScaleEngine."""
            for scaler in self.scalers:
                scaler.set({'scale':(0.5, 0.4)})
                for glyphName in self.glyphNames:
                    scaler.getScaledGlyph(glyphName, (100, 40))

        def test_setting_up_width(self):
            """Test setting up width scaling on a MutatorScaleEngine."""
            for scaler in self.scalers:
                scaler.set({'width':0.75})
                for glyphName in self.glyphNames:
                    scaler.getScaledGlyph(glyphName, (100, 40))

        def test_setting_up_scale_by_reference(self):
            """Test setting up scale on a MutatorScaleEngine."""
            testScales = [
                { 'targetHeight': 'A', 'referenceHeight': 'H' },
                { 'targetHeight': 'A', 'referenceHeight': 'capHeight' },
                { 'targetHeight': 490, 'referenceHeight': 'capHeight' },
                { 'targetHeight': 500, 'referenceHeight': 750 },
            ]
            for scale in testScales:
                for scaler in self.scalers:
                    scaler.set(scale)
                    for glyphName in self.glyphNames:
                        scaler.getScaledGlyph(glyphName, (100, 40))

        def test_adding_master(self):
            libFolder = os.path.dirname(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
            libFolder = os.path.join(libFolder, 'testFonts/')
            newFontPath = os.path.join(libFolder, 'isotropic-anisotropic/bold-mid-contrast.ufo')
            newFont = Font(newFontPath)
            scaler = self.scalers[0]
            scaler.addMaster(newFont)
            self.assertEqual(len(scaler), 5)

        def test_removing_master(self):
            scaler = self.scalers[0]
            fontToRemove = self.loadedFonts[0]
            scaler.removeMaster(fontToRemove)
            self.assertEqual(len(scaler), 3)

        def test_scaler_uses_hstem_as_main_value_from_single_values(self):
            scaler = MutatorScaleEngine()
            font1 = self.loadedFonts[2]
            font2 = self.loadedFonts[3]
            scaler.addMaster(font1, 15)
            scaler.addMaster(font2, 45)
            g = scaler.getScaledGlyph('A', 45)
            self.assertNotEqual(g.name, '_error_')

        def test_scaler_uses_hstem_as_main_value_from_tuples(self):
            scaler = MutatorScaleEngine()
            font1 = self.loadedFonts[2]
            font2 = self.loadedFonts[3]
            scaler.addMaster(font1, (100, 15))
            scaler.addMaster(font2, (100, 45))
            g = scaler.getScaledGlyph('A', 45)
            self.assertNotEqual(g.name, '_error_')

    unittest.main()