# coding=utf-8
# Loïc Sander — 2014
from baseParameter import SingleValueParameter
from vanilla import Group, Slider, EditText, TextBox, CheckBox

class BaseParameterVanillaInput:

    vanillaInputs = []

    def __init__(self, parameter, posSize, callback=None):
        self.parameter = parameter
        self.callback = callback

    def get(self):
        return self.parameter.get()

    def enable(self, value):
        for item in self.vanillaInputs:
            item.enable(value)

    def valueInput(self, sender):
        value = sender.get()
        parameter = self.parameter
        if value == 'R':
            parameter.reset()
            parameter.update()
            if self.callback is not None:
                self.callback(self)
            return
        elif value != '*':
            parameter.setInput(value, sender=sender)
            parameter.update()
            if self.callback is not None:
                self.callback(self)

    def setFree(self, sender):
        value = bool(sender.get())
        self.parameter.setFree(value)


class ParameterTextInput(Group):

    def __init__(self, parameter, posSize, text='', callback=None, continuous=False, showRelativeValue=False):
        super(ParameterTextInput, self).__init__(posSize)
        self.parameter = parameter
        rel = self._relValue()
        self.callback = callback
        self.textInput = EditText((0, 0, -40, -0), text=text, callback=self._valueInput, continuous=continuous)
        self.relInfo = TextBox((-35, 5, -0, -0), rel, alignment='left', sizeStyle='small')
        self.showRelativeValue(showRelativeValue)
        self.vanillaInputs = [self.textInput]
        self.parameter.bind(self)

    def set(self, value):
        self.parameter.set(value)
        self.update(None)

    def get(self):
        return self.parameter.get()

    def enable(self, value):
        for item in self.vanillaInputs:
            item.enable(value)

    def _valueInput(self, sender):
        value = sender.get()
        parameter = self.parameter
        if value == 'R' and parameter.hasMaster:
            parameter.reset()
            parameter.update()
            if self.callback is not None:
                self.callback(self)
            return
        elif value != '*':
            parameter.setInput(value, sender=sender)
            parameter.update()
            if self.callback is not None:
                self.callback(self)
        rel = self._relValue()
        self.relInfo.set(rel)

    def showRelativeValue(self, b):
        self.relInfo.show(b)

    def setFree(self, sender):
        value = bool(sender.get())
        self.parameter.setFree(value)

    def update(self, sender):
        value = self.parameter.get()
        self.textInput.set(str(value))
        self._updateRelValue()

    def _updateRelValue(self):
        rel = self._relValue()
        self.relInfo.set(rel)

    def _relValue(self):
        parameter = self.parameter
        rel = '-'
        if parameter.hasMaster:
            if parameter.mode == 'ratio':
                rel = '%s' % (parameter.getRatio())
            elif parameter.mode == 'offset':
                offsetValue = int(parameter.getOffset())
                sign = '+' if offsetValue >= 0 else ''
                rel = '%s%s' % (sign, offsetValue)
        return rel


class ParameterSliderTextInput(Group):

    '''
    Custom Vanilla object consisting mainly of a Slider & and text input linked together (through a parameter object)
    '''

    def __init__(self, parameter, posSize, title=None, callback=None):
        super(ParameterSliderTextInput, self).__init__(posSize)
        self.parameter = parameter
        self.callback = callback
        editTextPosSize = (-65, 0, 40, 22)
        if title is None:
            sliderPosSize = (5, 3, -80, 15)
        elif title is not None:
            title = title.capitalize()
            sliderPosSize = (70, 3, -80, 15)
            self.title = TextBox((0, 3, 65, 30), title, sizeStyle='small')
        if parameter.dissociable:
            editTextPosSize = (-65, 0, 40, 22)
            self.checkBox = CheckBox((-22, 5, 22, 25), u'∞', callback=self.setFree, value=True, sizeStyle='mini')
        self.slider = Slider(sliderPosSize, minValue=parameter.limits[0], maxValue=parameter.limits[1], value=parameter.value, callback=self.valueInput, sizeStyle='small')
        self.textInput = EditText(editTextPosSize, str(parameter.value), callback=self.valueInput, continuous=False, sizeStyle='small')
        self.parameter.bind(self)

    def get(self):
        return self.parameter.get()

    def enable(self, b):
        self.slider.enable(b)
        self.textInput.enable(b)
        if hasattr(self, checkBox):
            self.checkBox.enable(b)

    def valueInput(self, sender):
        value = sender.get()
        parameter = self.parameter
        if value == 'R':
            parameter.reset()
            parameter.update()
            if self.callback is not None:
                self.callback(self)
            return
        elif value != '*':
            parameter.setInput(value, sender=sender)
            parameter.update()
            if self.callback is not None:
                self.callback(self)

    def update(self, sender):
        value = self.parameter.get()
        self.textInput.set(str(value))
        if (value != '*'):
            self.slider.set(value)
        if hasattr(self, 'checkBox'):
            free = self.parameter.hasMaster
            self.checkBox.set(free)

    def setFree(self, sender):
        value = not bool(sender.get())
        self.parameter.setFree(value)

class VanillaParameterWrap(object):

    '''
    Base class, to be subclassed,
    making it easy to link a Parameter object
    with Vanilla UI input objects (Slider, EditText, CheckBox)
    '''

    def __init__(self):
        self.controls = []
        self.sender = None
        self.master = None

    def bind(self, vanillaObject):
        self.controls.append(vanillaObject)

    def unbind(self, vanillaObject):
        if vanillaObject in self.controls:
            self.controls.remove(vanillaObject)

    def updateControls(self):
        for vanillaObject in self.controls:
            vanillaObject.update(self.sender)

class VanillaSingleValueParameter(SingleValueParameter, VanillaParameterWrap):

    '''
    Subclass implementing a link between a vanilla UI and parameter object
    '''

    def __init__(self, name, defaultValue=None, limits=None, numType='float', master=None, mode=None, enable=True, dissociable=False):
        VanillaParameterWrap.__init__(self)
        SingleValueParameter.__init__(self, name, defaultValue=defaultValue, limits=limits, numType=numType, master=master, mode=mode)
        self.enable = enable
        self.dissociable = dissociable
        self.formerMaster = None

    def setInput(self, value, sender):
        self.sender = sender
        self.set(value)

    def setFree(self, b):
        if b:
            self.formerMaster = self.master
            if self.master is not None:
                self.master.affranchise(self)
            self.master = None
        elif not b:
            if self.formerMaster is not None:
                self.master = self.formerMaster
                self.master.enslave(self)

    def update(self):
        self.relationValue = self._getRelationValue()
        self.propagate()
        self.updateControls()
