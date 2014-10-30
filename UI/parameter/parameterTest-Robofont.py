from vanillaParameterObjects import ParameterSliderTextInput, VanillaSingleValueParameter
from vanilla import Window, Group

class ParameterTester:
    
    def __init__(self):
        self.w = Window((300, 100))
        self.w.inner = Group((10, 10, -10, -10))
        
        p1 = VanillaSingleValueParameter('main', 10, (0, 100), 'int')
        p2 = VanillaSingleValueParameter('ratio', 10, (0, 100), 'int', master=p1, mode='ratio', dissociable=True)
        p3 = VanillaSingleValueParameter('offset', 10, (0, 100), 'int', master=p1, mode='offset', dissociable=True)
        
        self.w.inner.p1 = ParameterSliderTextInput(p1, (0, 0, -0, 22), 'master')
        self.w.inner.p2 = ParameterSliderTextInput(p2, (0, 25, -0, 22), 'ratio')
        self.w.inner.p3 = ParameterSliderTextInput(p3, (0, 50, -0, 22), 'offset')
        self.w.open()
        
ParameterTester()