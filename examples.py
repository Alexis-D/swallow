#!/usr/bin/env python
#-*- coding: utf-8 -*-

import swallow

t = swallow.Swallow()

def get_answer_to_the_life():
    return 42

@t
def answer_to_the_life():
    assert 42 == get_answer_to_the_life()

@t.expect(ZeroDivisionError)
def division_by_zero():
    1 // 0

if __name__ == '__main__':
    # Swallow also support setup & teardown methods
    # and the ability to make optionnal test, for instance:
    #
    # import sys
    # @t(sys.version_info() > (3, 0, 0))
    # def py3():
    #     pass
    #
    # the test will be run only on Python 3 and greater.
    t.run()

    # Testing answer_to_the_life: PASS
    # Testing division_by_zero: PASS

    # 2 tests, 2 PASS, 0 NOT RUN, 0 FAIL
    # Executed in 0.00 seconds.


