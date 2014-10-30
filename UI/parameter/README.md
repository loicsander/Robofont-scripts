# Dynamic Parameters
================

## SingleValueParameter
*(baseParameter.py)*

This is an almost simple & independent object built to help defining values in relation to others, on a master/slave basis.
Each instance of the SingleValueParameter bears a value and is either a master or a slave (or both). There’s no ideology in the choice of words, you can also call them parent and children. The value of a parameter that is enslaved to another will change with its master’s value, based on a ratio, or an offset value.
The whole point of this object was primarily to make it easier to have dynamically linked values in a basic UI, but it can be used without any UI.

At the least, a parameter object requires a name and a default value.

```python
p = SingleValueParameter('myParameter', 40)
```

and here’s the whole object:
```python
SingleValueParameter(name, defaultValue, limits=None, numType='float', master=None, mode=None)
```

+ *limits* should be a tuple in the form (minValue, maxValue)
+ *numType* can be either ‘int’ or ‘float’ (used to format the output)
+ *master* would be another parameter object
+ *mode* the type of relationship to the master parameter, ‘ratio’ or ‘offset’

Defining a parameter’s value goes trough the **set()** method:
```python
p.set(40)
```

If the parameter happens to be the master of other parameters, all the slave parameters will be modified as well, based on their ratio/offset. A parameter given a master but no mode will fail.

The relationship can be changed at any time **setMode()**, and a slave parameter can be freed at any time as well with **setMaster(None)**.

Independently from the chosen mode, 'ratio' or 'offset', the ratio and offset values can be retrieved with **getRatio()** and **getOffset**. Inversely, and still independent of the mode, ratio and offset can be set, **setRatio()**, **setOffset()**.

Similarly, values of a parameter can be set relatively through the **set()** method: adding ('++20') or substracting ('--20'). Note that these inputs have to be strings for the ++ and -- operators to be considered.

## VanillaSingleValueParameter
*(vanillaParameterObjects.py)*

This is the UI linked implementation of the SingleValueParameter object. Specifically, it is made to function with ![vanilla](https://github.com/typesupply/vanilla) based UI elements for use inside of Robofont or DrawBot (or any application using ![vanilla](https://github.com/typesupply/vanilla), I guess).

![alt tag](slider-parameters.png)

## ParameterSliderTextInput
*(vanillaParameterObjects.py)*

And here’s a bunch of ![vanilla](https://github.com/typesupply/vanilla) object grouped together (a slider, text input and checkbox), linking the slider and text input values through the ways of a parameter object.
