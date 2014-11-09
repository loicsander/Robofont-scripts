import re

class PointLabelDict(object):

    def __init__(self, pointName):
        if pointName is not None:
            rawlabels = pointName.split(',')
        elif pointName is None:
            rawlabels = []
        self.labels = {}
        for rawLabel in rawlabels:
            label = self.parseLabel(rawLabel)
            if isinstance(label, tuple):
                self.labels[label[0]] = label[1]
            elif isinstance(label, str) or isinstance(label, unicode):
                self.labels[label] = True

    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.mathOperateLabels(other, 'add')
        return self.mathOperate(other, 'add')

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return self.mathOperateLabels(other, 'sub')
        return self.mathOperate(other, 'sub')

    __rsub__ = __sub__

    def __div__(self, other):
        if isinstance(other, self.__class__):
            return self.mathOperateLabels(other, 'div')
        return self.mathOperate(other, 'div')

    __rdiv__ = __truediv__ = __rtruediv__ = __div__

    def __mul__(self, other):
        if isinstance(other, self.__class__):
            return self.mathOperateLabels(other, 'mul')
        return self.mathOperate(other, 'mul')

    __rmul__ = __mul__

    def __setitem__(self, key, value):
        self.labels[key] = value

    def __getitem__(self, key):
        if self.labels.has_key(key):
            return self.labels[key]
        return False
        raise KeyError

    def keys(self):
        return self.labels.keys()

    def mathOperateLabels(self, other, operation):
        compatibleLabels = self.getCompatibleLabels(other)
        newPointLabelDict = self.__class__('')
        for labelName in compatibleLabels:
            value1 = self[labelName]
            value2 = other[labelName]
            if isinstance(value1, bool) and isinstance(value2, bool):
                iValue = bool(value1 * value2)
            elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                if operation == 'add':
                    iValue = value1 + value2
                elif operation == 'sub':
                    iValue = value1 - value2
                elif operation == 'div' and value2 != 0:
                    iValue = value1 / value2
                elif operation == 'mul':
                    iValue = value1 * value2
            else:
                iValue = False
            newPointLabelDict[labelName] = iValue
        return newPointLabelDict

    def mathOperate(self, value, operation):
        newPointLabelDict = self.__class__('')
        for labelName in self.labels:
            value1 = self[labelName]
            value2 = value
            if isinstance(value1, bool):
                iValue = value1
            elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                if operation == 'add':
                    iValue = value1 + value2
                elif operation == 'sub':
                    iValue = value1 - value2
                elif operation == 'div' and value2 != 0:
                    iValue = value1 / value2
                elif operation == 'mul':
                    iValue = value1 * value2
            else:
                iValue = False
            newPointLabelDict[labelName] = iValue
        return newPointLabelDict

    def getCompatibleLabels(self, other):
        otherLabelNames = other.keys()
        labelNames = self.keys()
        return list(set(otherLabelNames) & set(labelNames))

    def parseLabel(self, label):
        p = re.search('_[a-zA-Z]([a-zA-Z])?_', label)
        if p is not None:
            label = label[len(p.group(0)):]
            if ':' in label:
                terms = label.split(':')
                return terms[0], float(terms[1])
            return label
        return

    def update(self, key, value):
        self.labels[key] = value

    def clear(self):
        self.labels = {}

    def write(self, pointName):
        if pointName is None:
            allLabels = []
        elif pointName is not None:
            allLabels = pointName.split(',')
            labelsToRemove = [label for label in allLabels if (re.search('_[a-zA-Z]([a-zA-Z])?_', label) is not None) or (label == '')]
            for label in labelsToRemove:
                allLabels.remove(label)
        parameters = [':'.join(['_p_'+str(key), str(round(value, 4))]) for key, value in self.labels.items() if isinstance(value, (float, int))]
        marks = ['_m_'+str(key) for key, value in self.labels.items() if isinstance(value, bool) and value is True]
        return ','.join(allLabels+parameters+marks)

    def get(self, key):
        if self.labels.has_key(key):
            return self.labels[key]
        return False