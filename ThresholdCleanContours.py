from robofab.pens.filterPen import thresholdGlyph

font = CurrentFont()
glyph = CurrentGlyph()
#Units per em value passed to the ThresholdPen
threshold = 4

class CleanOutline:
    
    def __init__(self, glyph):
        self.glyph = glyph
        self.glyph.prepareUndo("cleanOutline")
        # storing and clearing anchors in current glyph
        self.storedAnchors = self.saveAnchors(glyph)
        # clean outline through the ThresholdPen
        self.cleanOutline(self.glyph)
        # putting stored anchors back in place
        self.replaceAnchors(self.storedAnchors)
        self.glyph.update()
        self.glyph.performUndo()
        
        
    def saveAnchors(self, glyph):
    
        anchorList = []
    
        for anchor in glyph.anchors:
            anchorList.append((anchor.name, (anchor.x, anchor.y)))
            glyph.removeAnchor(anchor)
    
        return anchorList
    
    def replaceAnchors(self, anchorList):
    
        for i in range(len(anchorList)):
            thisAnchor = anchorList[i]
            self.glyph.appendAnchor(thisAnchor[0], thisAnchor[1])


    def cleanOutline(self, glyph):

        for contour in glyph:
    
            for i in range(len(contour.points)):
        
                if i > 0:

                    if i < len(contour.points)-1:
                
                        if (contour.points[i-1].x == contour.points[i].x) and (contour.points[i+1].x == contour.points[i].x) and (contour.points[i].type == "line") and (contour.points[i-1].type == "line") and (contour.points[i+1].type == "line"):
                            contour.points[i].y = contour.points[i-1].y
                        if (contour.points[i-1].y == contour.points[i].y) and (contour.points[i+1].y == contour.points[i].y) and (contour.points[i].type == "line") and (contour.points[i-1].type == "line") and (contour.points[i+1].type == "line"):
                            contour.points[i].x = contour.points[i-1].x
                    
        thresholdGlyph(glyph, threshold)

if len(font.selection) != 0:
    for glyph in font.selection:
        CleanOutline(font[glyph])
    print "_ Done cleaning _"
else:
    print "You must have at least one glyph selected."

