from __future__ import division

def getValueForKey(ch):
    try: return 'abcdefghijklmnopqrstuvwxyz'.index(ch)
    except: return

def getKeyForValue(i):
    try: return 'abcdefghijklmnopqrstuvwxyz'[i]
    except: return

def splitSpotKey(spotKey):
    try:
        ch = spotKey[0]
        j = int(spotKey[1:])
        return ch, j
    except:
        return None

from baseParameter import SingleValueParameter

class baseMatrixSpot(object):

    def __init__(self, spot=None):
        self.x, self.y = 0, 0
        if spot is not None:
            a, b = spot
            self._setX(a)
            self._setY(b)
        elif spot is None:
            self.spot = (getKeyForValue(self.x), self.y)
        self.fontPath = None

    def __setitem__(self, index, value):
        if index == 0:
            self._setX(value)
        elif index == 1:
            self._setY(value)
        else:
            raise IndexError

    def __getitem__(self, index):
        if index == 0:
            return self.spot[0]
        elif index == 1:
            return self.spot[1]
        else:
            raise IndexError

    def moveTo(self, x, y):
        self._setX(x)
        self._setY(y)

    def shift(self, (xAdd, yAdd)):
        self.x += xAdd
        self.y += yAdd
        self.spot = (getKeyForValue(self.x), self.y)

    def set(self, (x, y)):
        self._setX(x)
        self._setY(y)

    def _setX(self, x):
        if isinstance(x, int):
            self.x = x
            self.spot = (getKeyForValue(x), self.y)
        elif isinstance(x, (str, unicode)):
            self.x = getValueForKey(x)
            self.spot = (x, self.y)
        else:
            raise ValueError

    def _setY(self, y):
        if isinstance(y, int):
            self.y = y
            self.spot = (self.spot[0], self.y)
        else:
            raise ValueError

    def get(self):
        return self.spot

    def getRaw(self):
        return self.x, self.y

    def getDict(self, name1, name2):
        return {name1:self.x, name2:self.y}

    def getString(self):
        return '%s,%s' % (self.x, self.y)

    def getSpotKey(self):
        return self.spot[0] + str(self.spot[1])

    def getReadableSpot(self):
        return self.spot[0].upper() + str(self.spot[1]+1)

    def getFontPath(self):
        return self.fontPath


class MatrixMaster(baseMatrixSpot):

    def __init__(self, spot, font):
        super(MatrixMaster, self).__init__(spot)
        self.font = font
        if (font is not None) and hasattr(font, 'path'):
            self.fontPath = font.path

    def __repr__(self):
        return '<MatrixMaster %s.%s key:%s readable:%s' % (self.x, self.y, self.getSpotKey(), self.getReadableSpot())

    def items(self):
        return self.spot, self.font

    def setFont(self, font):
        self.font = font

    def getFont(self):
        return self.font


class MatrixSpot(baseMatrixSpot):

    def __init__(self, spot, weights=None, fontPath=None, familyName=None, styleName=None):
        super(MatrixSpot, self).__init__(spot)
        self.fontPath = fontPath
        if weights is None:
            self.xWeight = self._setWeight('x', self.x)
            self.yWeight = self._setWeight('y', self.y)
        elif weights is not None:
            self.xWeight = self._setWeight('x', weights[0])
            self.yWeight = self._setWeight('y', weights[1])
        if familyName is None:
            self.familyName = ''
        elif familyName is not None:
            self.familyName = familyName + ' '
        if styleName is None:
            self.styleName = self.getReadableSpot()
        elif styleName is not None:
            self.styleName = styleName
        self.resetOffsetWeights()

    def __repr__(self):
        return '<MatrixSpot %s.%s key:%s readable:%s' % (self.x, self.y, self.getSpotKey(), self.getReadableSpot())

    def _setWeight(self, name, value):
        one, value = self._normalize(name, value)
        weight = SingleValueParameter(name, value, limits=(value-one, value+one), numType='int')
        return weight

    def _normalize(self, name, value):
        base = getattr(self, name)+1
        one = value / base
        value = one*base
        return one, value

    def setWeights(self, weights):
        for i, name in enumerate(['x', 'y']):
            value = weights[i]
            one, value = self._normalize(name, value)
            weight = getattr(self, '%sWeight'%(name))
            weight.setLimits((value-one, value+one))
            weight.set(value)

    def getWeights(self):
        return self.xOffsetWeight.get(), self.yOffsetWeight.get()

    def shiftWeights(self, (xWeightShift, yWeightShift)):
        self.xOffsetWeight.set(xWeightShift)
        self.yOffsetWeight.set(yWeightShift)

    def resetOffsetWeights(self):
        self.xOffsetWeight = SingleValueParameter('xOffset', self.xWeight.get(), limits=self.xWeight.limits, master=self.xWeight, mode='ratio', numType='int')
        self.yOffsetWeight = SingleValueParameter('yOffset', self.yWeight.get(), limits=self.yWeight.limits, master=self.yWeight, mode='ratio', numType='int')

    def getWeightsAsDict(self, name1, name2):
        return {name1: self.xOffsetWeight.get(), name2: self.yOffsetWeight.get()}

    def getWeightsAsString(self):
        return '%s/%s' % (self.xOffsetWeight.get(), self.yOffsetWeight.get())

    def setFontPath(self, path):
        self.fontPath = path

    def getFontPath(self):
        return self.fontPath

    def getFullName(self):
        return self.familyName + self.styleName

    def getNames(self):
        return self.familyName, self.styleName
