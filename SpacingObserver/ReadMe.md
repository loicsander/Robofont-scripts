# Spacing Observer
## Script for Robofont

This script implements an observer that monitors the editing of glyph sidebearings in the space center and propagates these sidebearing modifications among all glyphs belonging to a common metrics group. 

A metrics group is created through the ‘Group’ function of Robofont. By default, the nomenclature for metrics groups is the following:
+ .mtrx_L_a (i.e. left sidebearing of glyph 'a', as a reference)
+ .mtrx_R_H (i.e. right sidebearing of glyph 'H', as a reference)

You can edit this nomenclature quite easily inside the script file (see ‘metricsPrefix’, ‘leftIndicator’ and ‘rightIndicator’ variables).

It doesn’t matter what name you give to the group, for any glyph you modify, the script gets the appropriate group if there’s one, then applies the sidebearing modification to all other members of this group, no exceptions.

Group spacing can be turned on and off with a checkbox added at the bottom of the space center window. It is off by default.

### Disclaimer
I post this without having tried it extensively yet, let’s say it’s an alpha version. You can have composite glyphs in spacing groups, it works ok (even keeps diacritics in place), but in an attempt to modify spacing by changing sidebearings of a composite glyph belonging to a metrics group, the script will wreak havoc! You’ve been warned. Plus, I’d say you don’t need to do that anyway.