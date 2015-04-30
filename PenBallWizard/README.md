PenBall Wizard
================

# Overview

This extension is a helper for the wielding of [robofab pens](http://www.robofab.org/objects/pen.html) and functions that transform a glyphs outline. The interface is thought to manage ‘filters’, and see a preview of their effects. A filter is added either by indicating a module importation string that links to existing & installed pens or functions, or by pointing to a file from which a pen or function will be imported on the fly. For each new filter, you also indicate the name of the pen or function as well as possible arguments, which will result in UI controls for each argument.

If you provide pens, they should work according to this pattern: ```pen = MyFilterPen(otherPen, **arguments)```, if you want to use a pen that doesn’t receive another pen as argument, you should provide an intermediary function that handles the pen and returns a filtered glyph.

Alternatively, filters can be added by other extensions inside Robofont. An extension that has a pen or filter functions can add it to the filters list when a PenBallWizard is started. This is done by suscribing to the ```"PenBallWizardSubscribeFilter"``` event. The callback dictionary will contain a method allowing you to add your filter object to PenBallWizard’s list:

```python
from mojo.events import addObserver

def myFilterFunction(glyph, arg1=True, arg2=20):
    # does stuff on a glyph
    return filteredGlyph

class MyExtension:

    def __init__(self):
        addObserver(self, 'addFilterToPenBallWizard', 'PenBallWizardSubscribeFilter')

    def addFilterToPenBallWizard(self, notification):
        subscribeFilter = notification['subscribeFilter']
        # provide a filter name
        # and a dictionnary with the filterObject and arguments
        subscribeFilter('MyFilter', {
            'filterObject': myFilterFunction,
            'arguments': {
                'arg1': True,
                'arg2': 20
            }
        })


```

# Usage

## Single filter

![alt tag](images/penBallWizard-singlefilter.jpg)
![alt tag](images/penBallWizard-1.jpg)

## Group filter
Filters can be defined as a succession of filters:

![alt tag](images/penBallWizard-groupfilter.jpg)
![alt tag](images/penBallWizard-2.jpg)

When defining a filter group, you call existing single filters by name and you have a couple of options for each filter in the process. By default, at each step, the glyph is filtered and returned to be passed to the next filter. The ```mode``` option allows you to define how the glyph is passed on to the next step. 

Here are the possible arguments for the mode option:
+ ‘add’: add filtered glyph on top of the existing glyph instead of filtering the existing
+ ‘union’: (see [BooleanOperations](http://doc.robofont.com/api/robofab-extras/boolean-glyph/))
+ ‘intersection’: (see [BooleanOperations](http://doc.robofont.com/api/robofab-extras/boolean-glyph/))
+ ‘difference’: [BooleanOperations](http://doc.robofont.com/api/robofab-extras/boolean-glyph/))

The ```initial``` value is used to tell a specific filter to use the original glyph instead of the previously filtered one (if some filters have already been used in the process).
