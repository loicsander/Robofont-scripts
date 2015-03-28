# MutatorScale

[work in progress…]

Here’s an introduction to MutatorScale, a code extension to Letterror’s MutatorMath and a scripting tool meant to be used inside Robofont.

It consists of a little set of object — I wouldn’t go as far as to call it a library —, the most important and central one being what I called a MutatorScaleEngine.

Its function is to build an interpolation design space, based on MutatorMath, with which it is rendered easier to scale glyphs while compensating for the loss of weight and/or contrast by interpolating. Such operations imply that you have at least two interpolatable fonts to begin with.

Nota Bene: It is the same idea as in my ScaleFast extension for Robofont, only this version of the code is better written and can be used via scripting. I intend to update ScaleFast with this in a not too distant future.

## Overview

Here’s how it goes. Supposing you have a couple of interpolatable fonts, that’s all you need to produce a range of derivative glyphs that are basically scaled down versions of other; the infamous example being small capitals (I’ll leave the  ‘Small caps should be drawn’ purists to their romantic views and assume you’d love to hear more about generating small caps, among other things).

You start by building a MutatorScaleEngine, feeding it fonts it can interpolate from:

```python
scaler = MutatorScaleEngine(fonts)
```

Next, you provide information about the scaling you wish to perform. This can go two ways. The first and most direct one:

```python
scaler.set({ ’scale’: 0.8 })
```

At all times, the .set() method of a MutatorScaleEngine is fed a dictionary containing scaling information. The second way to define your scaling goes like this:

```python
scaler.set({
	‘width’: 1.03,
	‘referenceHeight’: ‘capHeight’,
	‘targetHeight’: 520
})
```

This way is less straightforward in terms of code but closer to the design. You provide the required elements that allow the MutatorScaleEngine to compute contextual scaling values.

*width* corresponds to simple horizontal scaling and should be a float value akin to a percentage (100% == 1).

*referenceHeight* can be either a string or an number (float or int), but if it is a string, it should be a height reference meaningful to a font, vertical metrics for instances or glyph names (of which it will take the whole height).

*targetHeight* is the height you wish to see your scaled glyphs have; should be a number (float or int).

From these values, the MutatorScaleEngine computes proper scaling ratios. The interesting aspect in this approach is that the scaling ratios may vary among interpolation masters so that you can effectively interpolate glyphs from font with slightly different vertical metrics values for instance, and still obtain scaled glyphs at the exact proportion you asked for.

Once scale is set and has fonts to work with, the MutatorScaleEngine is ready to produce scaled glyphs, on demand.

Now if we ask:

```python
scaledGlyph = scaler.getScaledGlyph(‘H’, stems)
```

We get a new scaled letter H. With the glyphName, I’ve provided a stems variable and it is a crucial part of the process, so I’ll elaborate on that.

When fonts are provided to a MutatorScaleEngine, it does a quick analysis on them to be able to place them in an interpolation scheme. It measures reference stems for each font so that you can later ask for scaled glyphs with a specific stem value. Working with stem values is arbitrary and you can actually override this if you’d rather work with some other values, but I’ll get into that later on.

Stems are measured on uppercase I and H, to get both a vertical and horizontal stem value of reference. Stem values aren’t collected for each and every glyph, that would require coding capabilities I don’t have. But you can still work your way out pretty well with these.

As the reference values automatically gathered by the scaling engine are based on an H’s vertical and horizontal stems, you should use these as a reference when you scale glyphs and ask for specific stem values.

In effet, if you ask:

```python
scaler.getScaledGlyph(‘H’, (100, 20))
```

You’re asking for a scaled glyph ‘H’ that has 100 units for its vertical stems and 20 for its horizontal stems. If you ask for another glyph with these same values, you’re not asking to obtain that glyph with exactly these stem values but you’re asking for a scaled glyph, say ‘A’ with stems as they should be for an H with stem values of 100 and 20, vertically and horizontally, respectively. It may sound a bit confusing, but in fact, it’s relatively easy to get a hang of; all you have to do is keep track of an H’s stem values, the rest follows.