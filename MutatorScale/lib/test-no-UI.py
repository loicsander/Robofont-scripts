#coding=utf-8

import mutatorScale.utilities.fontUtils
reload(mutatorScale.utilities.fontUtils)

from mutatorScale.objects.scaler import MutatorScaleEngine
from mutatorScale.utilities.fontUtils import intersect
from robofab.world import RFont

paths = [
    '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/regular-low-contrast.ufo',
    '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/bold-low-contrast.ufo'
]

outputPath = '/Users/loicsander/Documents/80 Resources/20 Typetools/20 Robofont/50 Github-Robofont-scripts/MutatorScale/testFonts/two-axes/scaled-italic-low-contrast.ufo'

fonts = []

for p in paths:
    fonts.append(RFont(p))

# print intersect(fonts[1]['H'], 375, False)

scaler = MutatorScaleEngine(fonts)
# scaler = MutatorScaleEngine()
# scaler.addMaster(fonts[0], (100, 75))
# scaler.addMaster(fonts[1], (200, 105))
scaler.set({
    'scale' : (0.85, 0.8)
    })

outputFont = RFont()

for glyphName in 'AHIO':
    glyph = scaler.getScaledGlyph(glyphName, (95, 75))
    outputFont.insertGlyph(glyph, glyphName)

outputFont.save(outputPath)


