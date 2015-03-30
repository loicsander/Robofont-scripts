#coding=utf-8

from mutatorScale.objects.scaler import MutatorScaleEngine
from robofab.world import RFont

paths = [
    '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/regular-italic-low-contrast.ufo',
    '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/bold-italic-low-contrast.ufo'
]

outputPath = '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/scaled-italic-low-contrast.ufo'

fonts = []

for p in paths:
    fonts.append(RFont(p))

scaler = MutatorScaleEngine(fonts)
scaler.set({
    'scale' : (0.85, 0.8)
    })

outputFont = RFont()

for glyphName in 'AHIO':
    glyph = scaler.getScaledGlyph(glyphName, (105, 30))
    outputFont.insertGlyph(glyph, glyphName)

outputFont.save(outputPath)


