#coding=utf-8
from __future__ import division

from mutatorScale.objects.glyphs import MathGlyph
from mutatorScale.utilities.font import makeListFontName, getRefStems

class ScaleFont(object):
    '''
    Object acting partly like a font, i.e. a collection of glyphs.
    Receives transformation parameters that are applied indistinctly to all of its glyphs.
    '''

    def __init__(self, font, scale=None):
        self.font = font
        self.glyphs = {glyph.name:glyph for glyph in font}
        self.heights = {heightName:getattr(font.info, heightName) for heightName in ['capHeight','ascender','xHeight','descender']}
        self.name = '%s > %s' % (font.info.familyName, font.info.styleName)
        italicAngle = font.info.italicAngle
        if italicAngle is None: italicAngle = 0
        self.italicAngle = italicAngle
        self.scale = scale
        if scale is not None:
            self.setScale(scale)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name, self.scale)

    def __getitem__(self, key):
        return self.getGlyph(key)

    def __contains__(self, glyphName):
        return glyphName in self.glyphs

    def getXScale(self):
        if self.scale is not None:
            return self.scale[0]
        return

    def getYScale(self):
        if self.scale is not None:
            return self.scale[1]
        return

    def getScale(self):
        return self.scale

    def setScale(self, scale):
        '''
        Setting scale for the font:
        – either a simple (x, y) scale tuple
        – or a tuple in the form (width/x, targetHeight, referenceHeight)
        '''

        if len(scale) == 2:
            self.scale = scale

        elif len(scale) == 3:
            x, targetHeight, referenceHeight = scale
            xy = None

            try:
                xy = targetHeight / referenceHeight

            except:
                if referenceHeight in self.heights:
                    referenceHeightValue = self.heights[referenceHeight]
                    xy = targetHeight / referenceHeightValue

                elif referenceHeight in self.font:
                    g = self.font[referenceHeight]
                    if g.box is not None:
                        referenceHeightValue = g.box[3] - g.box[1]
                        xy = targetHeight / referenceHeightValue
            finally:
                if xy is not None:
                    self.scale = (x * xy, xy)

    def getGlyph(self, glyphName):
        if glyphName in self.glyphs:
            glyph = self.glyphs[glyphName]
            scale = self.scale
            scaledGlyph = self.scaleGlyph(glyph, scale)
            return scaledGlyph
        else:
            return KeyError

    def scaleGlyph(self, glyph, scale):
        '''
        Custom implementation of a glyph scaling method that doesn’t scale components
        but does scale their offset coordinates.
        '''
        glyph = MathGlyph(glyph)
        italicAngle = self.italicAngle
        # Skew to an upright position to prevent the slant angle from changing because of scaling
        if italicAngle:
            glyph.skewX(italicAngle)
        # Do the scaling
        glyph *= scale
        # Cancel scaling effect on components except for their offset values
        for i, component in enumerate(glyph.components):
            baseGlyph, matrix = component
            xx, yx, xy, yy, x, y = matrix
            xx, yx, xy, yy = 1, 0, 0, 1
            glyph.components[i] = (baseGlyph, (xx, yx, xy, yy, x, y))
        # Reverting to initial slant angle
        if italicAngle:
            glyph.skewX(-italicAngle)
        return glyph

class MutatorScaleFont(ScaleFont):
    '''
    Subclass of a ScaleFont that has reference values allowing its use in a MutatorMath context.
    '''

    def __init__(self, font, stems=None, scale=(1, 1), stemsWithSlantedSection=False):
        super(MutatorScaleFont, self).__init__(font, scale)
        self.stemsWithSlantedSection = stemsWithSlantedSection
        self.processDimensions(stems)

    def __repr__(self):
        return '<%s %s refStems:%s,%s>' % (self.__class__.__name__, self.name, self._refVstem, self._refHstem)

    def processDimensions(self, stems):
        font = self.font
        refVstem, refHstem = getRefStems(font, self.stemsWithSlantedSection)
        if stems is None:
            self._refVstem, self._refHstem = refVstem, refHstem
        else:
            vstem, hstem = stems
            self._refVstem = vstem if vstem is not None else refVstem
            self._refHstem = hstem if hstem is not None else refHstem

    def getStems(self):
        return self.vstem, self.hstem

    def setStems(self, stems):
        vstem, hstem = stems
        self.vstem = vstem
        self.hstem = hstem

    @property
    def vstem(self):
        return self._refVstem
    @vstem.setter
    def vstem(self, stem):
        self._refVstem = stem

    @property
    def hstem(self):
        return self._refHstem
    @hstem.setter
    def hstem(self, stem):
        self._refHstem = stem