# Spacing Observer
## Script for Robofont

This script implements an observer that monitors the editing of glyph sidebearings in the space center and propagates these sidebearing modifications among all glyphs belonging to a common metrics group. 

A metrics group is created through the ‘Group’ function of Robofont. By default, the nomenclature for metrics groups is the following:
+ .mtrx_L_a (i.e. left sidebearing of glyph 'a', as a reference)
+ .mtrx_R_H (i.e. right sidebearing of glyph 'H', as a reference)

You can edit this nomenclature quite easily inside the script file (see ‘metricsPrefix’, ‘leftIndicator’ and ‘rightIndicator’ variables).

Group spacing can be turned on and off with a checkbox added at the bottom of the space center window. It is off by default.

### Disclaimer
I post this without having tried it extensively yet, let’s say it’s an alpha version. You can have composite glyphs in spacing groups, it works ok (even keeps diacritics in place) but trying to modify a group’s metrics by changing sidebearings on a composite glyph that belongs to a metrics group (why would you) will wreak havoc!