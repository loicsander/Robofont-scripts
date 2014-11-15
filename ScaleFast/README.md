## ScaleFast
================

This script’s mission is simple: keep stem widths consistent while you fiddle with proportions of a glyph. It manages that by trying to compensate for scale deformations through interpolation. To do that, it requires at least two masters (a regular and bold for instance). This way, you can easily produce scaled versions of existing glyph for any purpose you see fit, small capitals, superiors, extended or condensed styles, scaled up, down, etc. 
*The tool’s flexibility comes a great deal from its relying on ![MutatorMath](https://github.com/LettError/MutatorMath), written by Erik van Blokland.*

![alt tag](images/example-scalefast-6.png)


### How it works

To get the best possible results, here’s a few explanations about how this script works. 

When you add masters (as many as you like), they are analysed for vertical & horizontal stem width (based on I’s stem and the horizontal bar of H). These values are then used as reference point to build an interpolation space (with help of MutatorMath). 

It doesn’t really matter that these values are the right ones for stem width. These values are used as reference points when you put values in the stem input fields. So if the reference values are actual stem values, this means that you can put in stem values in the stem field as well, and that’s what you get as output. Remember, the value you ask for corresponds to the widths of a capital H’s stem (horizontal, or vertical). That’s the way the tool was built to be used, ideally. But if you’d rather make your masters stem values on a 0 to 1000 scale, it will work all the same, only you won’t ask for a stem of 120 units between masters that have stems of 80 and 200, you’ll be asking a instance of 700 between masters of say, 300 and 1000.

#### The first master

The font from which glyphs are scaled and worked on is always the first in the masters list. If you wish to work on another font in the list, just drag and drop it on top of the list.

#### Scaling

With ScaleFast, what you scale firstly are reference heights. This is why you’ll find a text input requiring a value in units (per em) and a popup menu with predefined reference heights. What you’re asking when you ask for [300]/[xHeight] is that ScaleFast scales glyphs with a ratio of 300/500 if you’re xHeight is 500 units high, for instance. The ratio part is taken care of, all you need to know is the change in dimensions you want. This will effectively result in lowercase letters having a 300 units height xHeight themselves.

#### Stems

As I mentioned in a previous paragraph, the whole point of ScaleFast is allowing you to scale glyphs while defining the exact stem width, be it vertical or horizontal, you wish to obtain on the scaled glyphs. This being, be aware that these glyphs suffer quite a lot of mathematical operations and rounding, so don’t be surprised if the results display some little inaccuracies (shouldn’t be beyond 2 or 3 units though).
The way you define stem values depends on the mode you’re working with.

#### Modes

ScaleFast can work according to three modes, the default being isotropic.

**Isotropic**
This is the simplest interpolation, one that moves values linearly between two reference points, or masters. With this mode, the script will only be able to retain vertical stem width while you scale glyphs; which is not so bad to begin with. This means that serif thickness, for instance, will be smaller than the original size. With this mode, you can only define vertical stem values, which will effectively define the interpolation factor between master stem values. If the masters stem values are accurate, the result will be as well. Only vertical stem width will be correct though, remember.

**Anisotropic**
The anistotropic mode distinguishes interpolation on the X and Y axes. It provides the possibility of deformation along each of those two axes. Practically, it means that — to a certain extent — the script can compensate for reduction on the Y axis also and try to maintain horizontal stem width as well. Depending on the design, you might not need to correct serif thickness or contrast for instance. This mode requires two values for vertical and horizontal stems, with that and to the best of its capabilities, the tool will try to maintain these values for the stems of the scaled glyphs. Be aware that the result will strongly depend on your design, if you spot inconsistencies, please start by checking that these aren’t due to your masters’ stem widths.

**Bi-dimensional**
Being able to work in two-dimensional interpolation was the actual reason that pushed me to write this tool. Thanks to MutatorMath, handling interpolation along multiple axis has become incredibly easy, and it’s also incredibly powerful. The best use case (and the one I initially wrote this tool for) is the case of a contrasted type family with optical sizes. For type of which the weight evolves in the ‘usual’ way — that is to say relative contrast lessens while weight becomes heavier, effectively making horizontal stems thicker — working with isotropic or anisotropic interpolation will probably be sufficient to generate scaled glyphs that require little or no correction. 

But in the case of a family of which contrast and serif thickness do not change with weight (random example: a Didot face), anisotropic interpolation can’t do anything for you because there’s no difference in contrast to work from. But if you have been working with optical sizes and your optical sizes are compatible for interpolation, then you do have a difference in contrast you can work from. This situation allows you to work both with separate weight & contrast axes, and in that case you can use bi-dimensional interpolation to solve your scaling problems. To be honest, you could work out an an/isotropic interpolation with your optical sizes, but that would be to the expense of much time spent generating intermediary masters. Not very practical.

Now back to ScaleFast, if you provide at least three masters that allow the script to build a two axis interpolation scheme, then you can generate whatever scaled glyphs you need, and it’s actually the case in which the tool performs the best.

NB: ScaleFast figures out on its own if it has all that is required for bi-dimensional interpolation, it will switch automatically to this mode if it can.

![alt tag](images/example-scalefast-1.png)
![alt tag](images/example-scalefast-2.png)
![alt tag](images/example-scalefast-3.png)
![alt tag](images/example-scalefast-4.png)