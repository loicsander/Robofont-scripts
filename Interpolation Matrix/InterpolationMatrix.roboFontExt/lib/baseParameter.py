# coding=utf-8
# Loïc Sander — 2014
from __future__ import division
import re

class ParameterModeError(Exception):

    def __init__(self, msg, mode):
        self.msg = msg
        self.mode = mode

    def __str__(self):
        return self.msg + repr(self.mode)

def valueToRatio(referenceValue, value, rounding=8):
    if referenceValue:
        return round((value/referenceValue), rounding)
    return 1

def ratioToValue(reference, ratio, rounding=8):
    return round(reference * ratio, rounding)

class SingleValueParameter(object):

    '''
    Base parameter object built to connect numerical values
    on a _ratio_ or _offset_ basis, dynamically.
    '''

    def __init__(self, name, defaultValue, limits=None, numType='float', master=None, mode=None):
        self.name = name
        self.value = defaultValue
        self.master = master
        self.mode = mode
        self.numType = numType
        self.validModes = ['ratio', 'offset']
        self.limits = limits
        if master is not None:
            master.slaves.append(self)
            if mode not in self.validModes:
                raise ParameterModeError('A slave parameter’s mode cannot be ', mode)
                return
            self.limits = master.limits
        self.relationValue = self._getRelationValue()
        self.slaves = []
        self.defaultValue = defaultValue

    def __repr__(self):
        if self.master is not None: master = self.master.name
        else: master = None
        return '<Parameter %s value:%s master:%s mode:%s>' % (self.name, self.value, master, self.mode)

    def __add__(self, other):
        return self.mathOperate(other, 'add')

    __radd__ = __add__

    def __sub__(self, other):
        return self.mathOperate(other, 'sub')

    __rsub__ = __sub__

    def __mul__(self, other):
        return self.mathOperate(other, 'mul')

    __rmul__ = __mul__

    def __div__(self, other):
        return self.mathOperate(other, 'div')

    __rdiv__ = __rtruediv__ = __truediv__ = __div__

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.name == other.name) and (self.mode == other.mode) and (self.master == other.master) and (self.limits == other.limits) and (self.numType == other.numType)
        return False

    def mathOperate(self, other, operation):
        firstValue = self.get()
        secondValue = None
        if self == other:
            secondValue = other.get()
        elif isinstance(other, (float, int)):
            secondValue = other
        if secondValue is not None:
            p = self.clone()
            if operation == 'add':
                value = firstValue + secondValue
            elif operation == 'sub':
                value = firstValue - secondValue
            elif operation == 'mul':
                value = firstValue * secondValue
            elif operation == 'div':
                value = firstValue / secondValue
            p.set(value)
            return p
        else:
            raise TypeError


    def clone(self):
        return self.__class__(self.name, self.defaultValue, self.limits, self.numType, self.master, self.mode)

    def asDict(self):
        return dict(
            name = self.name,
            numType = self.numType,
            limits = self.limits,
            master = self.master,
            defaultValue = self.defaultValue,
            mode = self.mode,
            value = self.value
            )

    def asShortDict(self):
        return dict(name = self.name, value = [self.value, self.master])

    def digest(self):
        d = []
        d.append('Parameter: %s'%(self.name))
        d.append('Value: %s'%(self.get()))
        if (self.master is not None) and (self.mode is not None):
            d.append('mode: %s'%(self.mode))
            d.append('ratio: %s'%(self.getRatio()))
            d.append('offset: %s'%(self.getOffset()))
            d.append('Master: %s [%s]'%(self.master.name, self.master.get()))
        d.append('\n')
        return '\n'.join(d)

    def set(self, value):
        self.value = self._checkValue(value)
        if self.master is not None:
            self.relationValue = self._getRelationValue()
        self.propagate()

    def setRatio(self, ratio):
        if self.master is not None:
            self.value = ratioToValue(self.master.get(), ratio)
            self.relationValue = self._getRelationValue()
        self.propagate()

    def setOffset(self, offset):
        if self.master is not None:
            self.value = self.master.get() + offset
            self.relationValue = self._getRelationValue()
        self.propagate()

    def setMode(self, mode):
        if mode in self.validModes:
            self.mode = mode
            self.relationValue = self._getRelationValue()

    def get(self):
        master = self.master
        mode = self.mode
        if (master is not None) and (mode is not None):
            relationValue = self.relationValue
            if mode == 'ratio':
                value = ratioToValue(master.get(), relationValue)
            elif mode == 'offset':
                value = master.get() + relationValue
        elif (master is None):
            value = self.value

        return self._constrainValue(value)

    def getRatio(self):
        if self.master is not None:
            masterValue = self.master.get()
            value = self.value
            return valueToRatio(masterValue, value)
        return 1

    def getOffset(self):
        if self.master is not None:
            masterValue = self.master.get()
            value = self.value
            return self._formatValue(value - masterValue)
        return 0

    def _getRelationValue(self):
        if self.mode == 'ratio':
            ratio = self.getRatio()
            return ratio
        elif self.mode == 'offset':
            offset = self.getOffset()
            return offset
        return

    def getInt(self):
        return int(round(self.get()))

    def update(self):
        self.relationValue = self._getRelationValue()
        self.propagate()

    def propagate(self):
        for slave in self.slaves:
            slave.value = slave.get()
            slave.update()

    def reset(self):
        master = self.master
        if master is None:
            self.value = self.defaultValue
        elif master is not None:
            self.value = master.get()
        self.relationValue = self._getRelationValue()

    def setDefault(self, value):
        value = self._checkValue(value)
        if value is not None:
            self.defaultValue = value

    def getDefault(self):
        if self.master is None:
            return self.defaultValue
        elif self.master is not None:
            return self.master.get()

    def enslave(self, parameter):
        if parameter not in self.slaves:
            if parameter.mode in ['ratio', 'offset']:
                self.slaves.append(parameter)
                parameter.master = self
                parameter.relationValue = parameter._getRelationValue()
                parameter.limits = self.limits
                parameter.value = parameter.get()
                parameter.update()
            else:
                raise ParameterModeError('A slave parameter’s mode cannot be ', mode)

    def affranchise(self, slave):
        if slave in self.slaves:
            self.slaves.remove(slave)

    def setMaster(self, master):
        # if this parameter already has a master
        # free it first
        if self.master is not None:
            self.master.affranchise(self)
        if master is not None:
            master.enslave(self)
        elif master is None:
            self.master = None

    def setLimits(self, (minValue, maxValue)):
        self.limits = (minValue, maxValue)
        for slave in self.slaves:
            slave.limits = (minValue, maxValue)
            slave.value = slave.get()
            slave.update()

    def _checkValue(self, value):
        if value == 'R':
            self.reset()
        elif isinstance(value, str) or isinstance(value, unicode):
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
            return self._constrainValue(value)
        elif isinstance(value, float) or isinstance(value, int):
            return self._constrainValue(value)
        return

    def _constrainValue(self, value):
        limits = self.limits
        if limits is not None:
            minValue, maxValue = limits
            if value < minValue: value = minValue
            elif value > maxValue: value = maxValue
        return self._formatValue(value)

    def _formatValue(self, value):
        if self.numType == 'int':
            value = int(round(value))
        elif self.numType == 'float':
            value = round(value, 2)
        return value

# Testing stuff
# fontWeight = SingleValueParameter('fontWeight', 80, (1,500), 'int')
# capWeight = SingleValueParameter('capWeight', 100, (1,500), 'int', mode='ratio', master=fontWeight)
# smallCapsWeight = SingleValueParameter('smallCapsWeight', 90, (1,500), 'int', mode='ratio', master=fontWeight)

# fontWeight.set(100)

# print fontWeight.digest()
# print capWeight.digest()
# print smallCapsWeight.digest()
