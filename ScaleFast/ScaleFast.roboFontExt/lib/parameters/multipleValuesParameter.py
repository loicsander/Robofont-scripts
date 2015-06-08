# coding=utf-8
from __future__ import division
import re

def valueToRatio(referenceValue, value, rounding=4):
    return round((value/referenceValue)-1, rounding)

def ratioToValue(reference, ratio, rounding=4):
    return round(reference * (1 + ratio), rounding)

class BaseParameter(object):

    def __init__(self, name, numType='float', defaultValue=0, value=0, limits=None, master=None, mode=None, free=False):
        self.name = name
        self.values = [value]
        self.relationValues = [self.getRelationValue()]
        self.masters = []
        self.values.append(value)
        if (master is not None) and (isinstance(master, self.__class__)):
            self.masters.append(master)
            if mode is None:
                print 'A slave parameter requires a mode (type of relationship to its master parameter).'
                return
        elif master is None:
            self.free = True
        self.slaves = []
        self.limits = limits
        self.defaultValue = defaultValue
        self._value = defaultValue
        self._multipleValues = []
        self.numType = numType
        self.mode = mode
        self.sender = None

    def __repr__(self):
        if self.master is not None:
            master = self.master.name
        else: master = None
        return '<Parameter %s master:%s free:%s mode:%s>' % (self.name, master, self.free, self.mode)

    def clone(self):
        return self.__class__(self.name, self.numType, self.limits, self.defaultValue, self.mode, self._value, self.master, self.free)

    def asDict(self):
        if self.master is not None:
            masterName = self.master.name
        elif self.master is None:
            masterName = None
        return dict(
            name = self.name,
            numType = self.numType,
            limits = self.limits,
            master = masterName,
            free = self.free,
            defaultValue = self.defaultValue,
            mode = self.mode,
            value = self._value
            )

    def asShortDict(self):
        return dict(name = self.name, value = [self._value, self.free])

    def set(self, value, index=0):
        value = self._checkValue(value)
        if value is not None:
            self.values[index] = value
            relValue = self.getRelationValue(index)
            if relValue is not None:
                self.relationValues[index] = relValue

        length = self.valuesLength()
        if length > 0:
            multipleValues = self._multipleValues
            for clone in multipleValues:
                clone._setValue(value)
                clone.update()

        self.update()

    def _setValue(self, value):
        value = self._checkValue(value)
        relValue = None
        if (value  is not None) and (mode is not None):
            if self.mode == 'ratio':
                self._ratioValue = self.getRatio()
            elif self.mode == 'offset':
                self._offsetValue = self.getOffset()

    def setRelativeValue(self, value):
        if mode == 'ratio':
            self.setRatio(value)
        elif mode == 'offset':
            self.setOffset(value)

    def setRatio(self, value):
        if value is not None:
            self._ratioValue = value
            self._value = self.get()

    def setOffset(self, value):
        if value is not None:
            self._offsetValue = value
            self._value = self.get()

    def get(self, index=None):

        if (index is not None) and (index < self.valuesLength()):
            multipleValues = self._multipleValues
            return multipleValues[index].get()

        if (self.master is None) or (self.master is not None and self.free):
            return self._formatValue(self._value)

        elif (self.master is not None) and (not self.free):
            if self.mode == 'ratio':
                return self._formatValue(ratioToValue(self.master.get(), self._ratioValue))
            elif self.mode == 'offset':
                return self._formatValue(self.master.get() + self._offsetValue)
            elif self.mode in [None, 'percentage']:
                return self._formatValue(self._value)

    def getSubValue(self, index=None):
        mode = self.mode
        if (index is not None) and (index < self.valuesLength()):
            multipleValues = self._multipleValues
            if mode == 'ratio':
                return multipleValues[index].getRatio()
            elif mode == 'offset':
                return multipleValues[index].getOffset()
            elif mode in [None,'percentage']:
                return multipleValues[index].get()

    def getRatio(self, index=0):
        if self.master is not None:
            masterValue = self.master.get(index)
            value = self.values[index]
            return valueToRatio(masterValue, value)
        return 1

    def getOffset(self, index=0):
        if self.master is not None:
            masterValue = self.master.get(index)
            value = self.values[index]
            return value - masterValue
        return 0

    def getRelationValue(self, index=0):
        if self.mode == 'ratio':
            return self.getRatio(index)
        elif self.mode == 'offset':
            return self.getOffset(index)
        return

    def getInt(self):
        return int(round(self.get()))

    def append(self, value, master):
        clone = self.clone()
        if master is not None:
            clone.master = master
        if self.mode == 'ratio':
            clone.setRatio(value)
        elif self.mode == 'offset':
            clone.setOffset(value)
        elif self.mode in [None, 'percentage']:
            clone._setValue(value)
        self._multipleValues.append(clone)

    def update(self):
        self.propagate()

    def propagate(self):
        for slave in self.slaves:
            if not slave.free:
                slave._value = slave.get()
                slave.update()

    def effect(self):
        self._value = self.get()
        self.update()
        if self.callback is not None:
            self.callback(self)

    def clearMultipleValues(self):
        self._multipleValues = []

    def valuesLength(self):
        return len(self._multipleValues)

    def reset(self):
        self.sender = None

        if (self.master is None) or (self.master is not None and self.free):
            self._value = self.defaultValue
        elif (self.master is not None and not self.free):
            self._value = self.master.get()
        if self.mode == 'ratio':
            self._ratioValue = self.getRatio()
        elif self.mode == 'offset':
            self._offsetValue = 0

        if self.valuesLength() > 0:
            multipleValues = self._multipleValues
            for clone in multipleValues:
                clone.reset()

    def setDefault(self, value):
        value = self._checkValue(value)
        if value is not None:
            self.defaultValue = self._formatValue(value)

    def getDefault(self):
        return self.defaultValue

    def setFree(self, b):
        if self.master is not None:
            self.free = b
            if self.free:
                self.master.affranchise(self)
            elif not self.free:
                self.master.enslave(self)
                self._value = self.get()
        self.update()

    def enslave(self, parameter):
        if parameter not in self.slaves:
            self.slaves.append(parameter)
            parameter.free = False
            parameter.master = self
            if parameter.mode == 'ratio':
                parameter._ratioValue = parameter.getRatio()
            elif parameter.mode == 'offset':
                parameter._offsetValue = parameter._value - self.get()
            parameter._value = self.get()
            parameter.update()

    def affranchise(self, parameter):
        if parameter in self.slaves:
            self.slaves.remove(parameter)

    def retake(self, parameter):
        if parameter not in self.slaves:
            self.slaves.append(parameter)

    def submit(self, parameter):
        if parameter is not None:
            if self.master is not None:
                self.master.affranchise(self)
            parameter.enslave(self)

    def _checkValue(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            s = re.search('(\+\+|--)(\d*\.?\d*)', value)
            if s is not None:
                offset = float(s.group(2))
                if s.group(1) == '++':
                    value = self.get() + offset
                elif s.group(1) == '--':
                    value = self.get() - offset
            elif s is None:
                try: value = float(value)
                except: value = 0
            return self._formatValue(value)
        elif isinstance(value, float) or isinstance(value, int):
            return self._formatValue(value)
        return

    def _formatValue(self, value):
        limits = self.limits
        if limits is not None:
            minValue, maxValue = limits
            if value < minValue: value = minValue
            elif value > maxValue: value = maxValue
        if self.numType == 'int':
            value = int(round(value))
        elif self.numType == 'float':
            value = round(value, 2)
        return value

# Testing stuff
fontWeight = BaseParameter('fontWeight', 'int', (1,500), 80)
capWeight = BaseParameter('capWeight', 'int', (1,500), 90, mode='ratio', master=fontWeight)
smallCapsWeight = BaseParameter('capWeight', 'int', (1,500), 85, mode='ratio', master=fontWeight)

fontWeight.set(105)
#smallCapsWeight.setFree(True)
#smallCapsWeight.setRatio(0.1)
#smallCapsWeight.submit(fontWeight)
print fontWeight.get(), capWeight.get(), smallCapsWeight.get()
print fontWeight.getRatio(), capWeight.getRatio(), smallCapsWeight.getRatio()
print fontWeight.asDict()

