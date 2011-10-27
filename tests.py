#!/usr/bin/env python
#-*- coding: utf-8 -*-

import swallow

test = swallow.Swallow()

@test
def singletest():
    @swallow.singletest()
    def a():
        assert True

    assert a.run() == (True, None, None)

    @swallow.singletest(ZeroDivisionError)
    def b():
        1 // 0

    assert b.run() == (True, None, None)

    @swallow.singletest(ValueError, setup=lambda: int(''))
    def c():
        pass

    assert c.run()[0] is False

    @swallow.singletest(ValueError, setup=lambda: int(''))
    def d():
        pass

    assert d.run()[0] is False

    @swallow.singletest()
    def e():
        1 // 0

    assert e.run()[0] is False
    assert e.run()[2][0] is ZeroDivisionError

    @swallow.singletest(TypeError)
    def f():
        pass

    assert f.run()[1] is not None

@test
def takes_no_positional_arguments():
    assert swallow.takes_no_positional_arguments(print) is None
    assert swallow.takes_no_positional_arguments(len) is None
    assert swallow.takes_no_positional_arguments(callable) is None

    def a():
        pass

    assert swallow.takes_no_positional_arguments(a) is True

    def b(a):
        pass

    assert swallow.takes_no_positional_arguments(b) is False

    def c(a=0):
        pass

    assert swallow.takes_no_positional_arguments(c) is True

    def d(*l):
        pass

    assert swallow.takes_no_positional_arguments(d) is True

    def e(a=0, *l):
        pass

    assert swallow.takes_no_positional_arguments(e) is True

    def f(*l, **k):
        pass

    assert swallow.takes_no_positional_arguments(f) is True

    def g(**k):
        pass

    assert swallow.takes_no_positional_arguments(g) is True

    def h(a=0, b=1):
        pass

    assert swallow.takes_no_positional_arguments(h) is True

    def i(a=0, b=1, *l, **k):
        pass

    assert swallow.takes_no_positional_arguments(i) is True

    def j(a, b):
        pass

    assert swallow.takes_no_positional_arguments(j) is False

    def k(a, b, l=0, *ll):
        pass

    assert swallow.takes_no_positional_arguments(k) is False

@test
def swallow_class():
    t = swallow.Swallow()

    @t(3 > 2)
    def a():
        pass

    @t(3 < 2)
    def b():
        pass

    @t
    def c():
        assert True

    @t.expect(ZeroDivisionError)
    def d():
        1 // 0

    @t
    def e():
        1 // 0

    @t.expect(TypeError)
    def f():
        1 // 0

    @t.expect(TypeError)
    def g():
        pass

    l = [x for x, _, _ in t]
    assert l == [True, None, True, True, False, False, False]

@test.expect(ValueError)
def uncorrect_fn():
    @swallow.singletest(setup=42)
    def a():
        pass

@test.expect(ValueError)
def uncorrect_fn2():
    @swallow.singletest(teardown=1337)
    def a():
        pass

@test.expect(ValueError)
def uncorrect_fn3():
    @swallow.singletest(setup=lambda x: x)
    def a():
        pass

if __name__ == '__main__':
    test.run()

