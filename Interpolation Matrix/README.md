## Interpolation Matrix (MutatorMath)
================

*Note! this version of the Interpolation Matrix script will work only from ROBOFONT v1.6 onward, for previous versions of Robofont, use either the extension or the previous script [see below].*

Script requiring at least two master fonts open in Robofont and interpolable glyphs which allows you to preview interpolation and extrapolation based on master position in an up to 20x20 matrix.

This version of the script (suffix -mutatormath) is a rewriting of the previous Interpolation Preview Matrix (see below) now using ![Letteror’s MutatorMath](https://github.com/LettError/MutatorMath) <3, whereas previous inter/extrapolations where  especially written for this script.

![alt tag](images/example-mutatormath-2.png)

The glyphs are updated (almost) at draw time [mouseUp, keyUp], so you can modify glyphs and see changes happen in the matrix. Theoretically, you can have a 15x15 matrix of 225 fonts, beyond, it would get to slow to use… Testing indicates that 7x7 is the ‘maximal-optimum’ use case.

![alt tag](images/example-mutatormath-1.png)

You can also generate instances, Font info (hinting and such) and kerning included. You can generate single instances by naming their ‘coordinates’ (A1, B4, C3, etc.), or you can generate instances by rows (A, 1, etc.), or all at once (*).

Demo on Vimeo:
http://vimeo.com/109734720


## Interpolation preview matrix
================

Script requiring at least two master fonts open in Robofont and interpolable glyphs which allows you to preview interpolation and extrapolation based on master position in a 3x3 matrix.

![alt tag](images/example.png)

The glyphs are updated at draw time, so you can modify glyphs and see changes happen live in the matrix (blue pill!). 
