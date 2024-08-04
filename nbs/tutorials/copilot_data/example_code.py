def f(x,y):
    x+y 

def g(x,y):
    return f(x,y)**2

class A:
    def __init__(self, x):
        self.x = x
    def method(self, y):
        return f(self.x, y)

print(f(2,3))