from mutatorScale.objects.scaler import MutatorScaleEngine

# To test this, open some interpolatable fonts (test fonts in TestFonts)

fonts = [font for font in AllFonts() if font.info.familyName != 'Output']

scaler = MutatorScaleEngine(fonts)
scaler.set({
    'scale':(0.85, 0.8)
    })
scaler.setAnisotropic(True)
    
f = RFont(showUI=False)
f.info.familyName = 'Output'

for glyphName in ['A','H','I','O']:
    stemValues = (100, 70)
    g = scaler.getScaledGlyph(glyphName, stemValues)
    f.insertGlyph(g, glyphName)
    
f.showUI()