#-*- coding: utf-8 -*-

"""Swallow is a simple unit test "framework", designed to be more
   friendly (imho) to use than unittest, and to not depend on the docstrings
   for the tests (like doctest)."""

import datetime
import functools
import inspect
import io
import os
import sys
import textwrap
import tokenize
import traceback

def get_meaningful_expression(tb):
    """Try to replace the variable names by their values to
       simplify the debugging process.

       tb is the traceback to inspect

       Return the error line and the expanded line ("dedented")"""

    # we only want the tb were the exception was raised
    while tb.tb_next:
        tb = tb.tb_next

    # get frame and dictionnary of locals(), globals() when
    # the exception was raised
    frame = tb.tb_frame
    local_vars, global_vars = frame.f_locals, frame.f_globals

    # err_lineno is the line number of where the error occured
    # lineno is the line number of the first line of source
    err_lineno = tb.tb_lineno
    source, lineno = inspect.getsourcelines(tb)

    # just remove the indentation
    err_line = textwrap.dedent(source[err_lineno - lineno])
    backup = err_line

    expanded = ''
    readline = io.BytesIO(err_line.encode('UTF-8')).readline

    for tok_type, tok_str, *_ in tokenize.tokenize(readline):
        # the first token is utf-8 and we don't want it
        if tok_type != tokenize.ENCODING:
            # restore whitespaces as tokenize doesn't yield them
            i = err_line.index(tok_str)
            expanded += ' ' * i

            # consume the error line
            err_line = err_line[i+len(tok_str):]

            if tok_type == tokenize.NAME:
                # if tok_str is in the locals, globals we add
                # its representation to expanded, otherwise
                # we just add tok_str
                if tok_str in local_vars:
                    v = local_vars[tok_str]
                    if callable(v):
                        expanded += tok_str
                    else:
                        try:
                            expanded += v.__name__
                        except AttributeError:
                            expanded += repr(v)
                elif tok_str in global_vars:
                    v = global_vars[tok_str]
                    if callable(v):
                        expanded += tok_str
                    else:
                        try:
                            expanded += v.__name__
                        except AttributeError:
                            expanded += repr(v)
                else:
                    expanded += tok_str
            else:
                expanded += tok_str

    return backup, expanded

def print_exception(type, value, tb, expand_errors=True):
    """Print the exception represented by (type, value, tb), and if
       expand_errors is True try to replace variables names by their
       values."""

    # remove the first tb, because that's just us catching the user exception
    tb = tb.tb_next
    traceback.print_exception(type, value, tb)

    if expand_errors:
        o, e = get_meaningful_expression(tb)
        if o != e:
            print(' ' * 4, e, file=sys.stderr, sep='')

def takes_no_positional_arguments(fn):
    """Return True if fn requires not positional arguments,
       False otherwise.

       May return None if it's impossible to know (try with
       the print function for instance, as it's built-in in
       C it won't work)."""

    try:
        pos, _, _, default = inspect.getargspec(fn)
    except TypeError:
        return None

    default = default or ()
    return len(default) - len(pos) == 0

def timer(fn):
    """This decorator compute the time needed to run a callable
       and print it on stdout."""

    @functools.wraps(fn)
    def wrapper(*args, **kwds):
        begin = datetime.datetime.now()
        r = fn(*args, **kwds)
        end = datetime.datetime.now()
        print('Executed in %.2f seconds.' % (end - begin).total_seconds())
        return r

    return wrapper

def singletest(expected=None, setup=None, teardown=None, run_if=True):
    """This decorator aims to be the fundamental unit of the tests.
       It return a new function with the same behaviour, + it add the
       run "method" to the function (which is the method which run the
       test).

       For instance:
       @singletest()
       def f():
           assert True

       we can do f() which will work as usual, plus f.run() to run the
       test.

       expected: is the type of exception that the function should raise
       setup: is a function to execute before executing the decorated
              function
       teardown: is a function to execute after executing the decorated
                 function
       run_if: if this condition is False, the test won't be run.

       run(no_output=True) will return a tuple (state, reason, exc) where:
         - state is True if the test was successful, False if it failed
           and None if run_if was False
         - reason (for now) is just a string saying that an exception
           was expected but none were raised.
         - exc is the return value of sys.exc_info()
       If no_output is True, then the test will redirect the output
       of the tested function to os.devnull."""

    def decorating_function(fn):
        for f in (fn, setup, teardown):
            # raise an exception if fn, setup, or teardown is not callable
            if f is not None and not callable(f):
                raise ValueError('%s isn\'t callable.' % f)

            # raise an exception if fn, setup, or teardown takes positional
            # args because if that's the case we don't know which arg value
            # to give them!
            if takes_no_positional_arguments(f) is False:
                raise ValueError('%s isn\'t callable without positional'
                        ' arguments.' % f)

        @functools.wraps(fn)
        def wrapper(*args, **kwds):
            return fn(*args, **kwds)

        def run(no_output=True):
            """See singletest for doc."""

            if not run_if:
                return None, None, None

            if setup:
                try:
                    with stdout_to_devnull(no_output):
                        setup()
                except Exception:
                    # we exit the function now because setup failed
                    # so we don't want to run fn(), or teardown()
                    return False, None, sys.exc_info()

            state, reason, exc = True, None, None

            try:
                with stdout_to_devnull(no_output):
                    fn()

                if expected:
                    try:
                        name = expected.__name__
                    except AttributeError:
                        name = str(expected)

                    state, reason = False, 'No exception was raised'\
                            ' (expected %s).' % name
            except Exception as e:
                if type(e) != expected:
                    state, exc = False, sys.exc_info()

            if teardown:
                try:
                    with stdout_to_devnull(no_output):
                        teardown()
                except Exception as e:
                    # set exc only if it's the first problem so far
                    if reason is None and exc is None:
                        state, exc = False, sys.exc_info()

            return state, reason, exc

        wrapper.run = run
        return wrapper
    return decorating_function

class stdout_to_devnull:
    """This class it aimed to be used with the with
       keyword to throw the stdout output of the with
       block to os.devnull."""

    def __init__(self, hide=True):
        """If hide is False this class will have no effect,
           otherwise just hide shadow sys.stdout by os.devnull."""

        self.stdout = None
        self.hide = hide

    def __enter__(self):
        """Map sys.stdout to os.devnull if needed, and backup
           sys.stdout (and return it)."""

        if self.hide:
            self.stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            return self.stdout

        return sys.stdout

    def __exit__(self, *_):
        """Restore sys.stdout if needed."""

        if self.hide:
            sys.stdout.close()
            sys.stdout = self.stdout


class Swallow:
    """An instance of this class may be used to collect testcase,
       and then execute them using run()."""

    def __init__(self, setup=None, teardown=None):
        """setup (resp. teardown) is a function which will be run before
           (resp. after) the test function."""

        self.tests = []
        self.setup = setup
        self.teardown = teardown

    def __call__(self, run_if=True):
        """This decorator may be used in two ways:

           t = Swallow()

           @t
           def a():
               pass

           @t(sys.version_info > (3, 0, 0))
           def b():
               pass

           In the first case it just add a to the list of testscases,
           in the second case it still add b to the list of testscases
           but it will be run only if the condition is fulfilled."""


        # dirty hack to see in which case we are
        if callable(run_if):
            fn = run_if
            t = singletest(setup=self.setup, teardown=self.teardown)(fn)
            self.tests.append(t)
            return t

        def wrapper(fn):
            t = singletest(setup=self.setup, teardown=self.teardown, run_if=run_if)(fn)
            self.tests.append(t)
            return t

        return wrapper

    def expect(self, expected, run_if=True):
        """This decorator add the underlying function to the list of testscases
           and the test is considered successful if the function raised an
           exception of type expected.

           If run_if is True the test will be run, otherwise, it won't be
           run."""

        def wrapper(fn):
            t = singletest(expected, self.setup, self.teardown, run_if=run_if)(fn)
            self.tests.append(t)
            return t

        return wrapper

    def __iter__(self):
        """Just allow someone to iterate over the result of the testscases
           instead of using run."""

        for t in self.tests:
            yield t.run(False)

    @timer
    def run(self, no_output=True, expand_errors=True):
        """Run the whole suite of test.

           no_output: if True the ouptut of the tested functions will be
                      discarded
           expand_errors: if True, we'll try to expand the values of the
                          variables where an exception is raised

           Return a tuple (passed, not_run, failed) which represent the
           number of successful tests, not runned test (because of the
           run_if parameter) and the number of failed tests."""

        passed = 0
        not_run = 0
        failed = 0

        for t in self.tests:
            print('Testing %s: ' % t.__name__, end='')

            state, reason, exc = t.run(no_output)
            if exc is not None:
                type, value, tb = exc

            if state:
                passed += 1
                print('PASS')
            elif state is None:
                not_run += 1
                print('NOT RUN')
            else:
                failed += 1
                print('FAIL')
                if reason:
                    print(reason, file=sys.stderr)
                else:
                    print_exception(type, value, tb, expand_errors)

        print()
        print('%d tests, %d PASS, %d NOT RUN, %d FAIL' % (len(self.tests), passed, not_run, failed,))
        return (passed, not_run, failed)

