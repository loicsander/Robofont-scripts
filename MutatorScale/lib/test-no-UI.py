#coding=utf-8

from mutatorScale.objects.scaler import MutatorScaleEngine
from mutatorScale.utilities.fontUtils import intersect
from robofab.world import RFont

paths = [
'testFonts/two-axes/regular-low-contrast.ufo',
'testFonts/two-axes/bold-low-contrast.ufo'
]
outputPath = 'testFonts/two-axes/scaled-italic-low-contrast.ufo'

fonts = []
for p in paths:
fonts.append(RFont(p))

scaler = MutatorScaleEngine(fonts)
scaler.set({
'scale' : (0.85, 0.8)
})

outputFont = RFont()
for glyphName in 'AHIO':
    glyph = scaler.getScaledGlyph(glyphName, (95, 75))
    outputFont.insertGlyph(glyph, glyphName)

outputFont.save(outputPath)