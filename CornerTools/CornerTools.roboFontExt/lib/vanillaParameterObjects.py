# coding=utf-8
# Loïc Sander — 2014
from baseParameter import SingleValueParameter
from vanilla import Group, Slider, EditText, TextBox, CheckBox

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
            if 'point' in title:
                title = title.lstrip('point')
                title = 'p. ' + title
            title = title.capitalize()
            sliderPosSize = (70, 3, -80, 15)
            self.title = TextBox((0, 3, 65, 30), title, sizeStyle='small')
        if parameter.dissociable:
            editTextPosSize = (-65, 0, 40, 22)
            self.checkBox = CheckBox((-22, 5, 22, 25), u'∞', callback=self.setFree, value=True, sizeStyle='mini')
            self.parameter.bind(self.checkBox)
        self.slider = Slider(sliderPosSize, minValue=parameter.limits[0], maxValue=parameter.limits[1], value=parameter.value, callback=self.valueInput, sizeStyle='small')
        self.textInput = EditText(editTextPosSize, str(parameter.value), callback=self.valueInput, continuous=False, sizeStyle='small')
        self.parameter.bind(self)
        self.parameter.bind(self.slider)
        self.parameter.bind(self.textInput)

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

    def setFree(self, sender):
        value = bool(sender.get())
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
        pass

    def setControls(self, value):
        for control in self.controls:
            if isinstance(control, EditText):
                if not isinstance(value, str):
                    value = str(value)
                control.set(value)
            elif isinstance(control, Slider) and (value != '*') and (control != self.sender):
                control.set(value)
            elif isinstance(control, CheckBox):
                free = self.master is None
                control.set(not free)

class VanillaSingleValueParameter(SingleValueParameter, VanillaParameterWrap):

    '''
    Subclass implementing a link between a vanilla UI and parameter object
    '''

    def __init__(self, name, defaultValue, limits, numType='float', master=None, mode=None, enable=True, dissociable=False):
        VanillaParameterWrap.__init__(self)
        SingleValueParameter.__init__(self, name, defaultValue=defaultValue, limits=limits, numType=numType, master=master, mode=mode)
        self.enable = enable
        self.dissociable = dissociable
        self.formerMaster = None

    def setInput(self, value, sender):
        self.sender = sender
        self.set(value)

    def setFree(self, b):
        if not b:
            self.formerMaster = self.master
            self.master.affranchise(self)
            self.master = None
        elif b:
            if self.formerMaster is not None:
                self.master = self.formerMaster
                self.master.enslave(self)

    def update(self):
        self.relationValue = self._getRelationValue()
        self.propagate()
        self.updateControls()

    def updateControls(self):
        value = self.get()
        self.setControls(value)
        self.sender = None