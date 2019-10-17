"""
Support for interacting between a GATE (java) process and a gatenlp (Python) process.
Make this specifically work with gatelib-interaction!
TODO: check if we can somehow do this: save the original stdout and 
create our own handle, then for transmitting data, use that handle 
so that any stdout from library calls does not interfere with the 
data interchange??
It may be possible to this via
# at this point we should have nothing on the stdout buffer, i.e.
# initialisation should never write anything to stdout, so we should 
# do this before any more intensive initialisation!
old_stdout = sys.stdout  # this is where we want to send the data
# (actually this is always available as sys.__stdout__ )
sys.stdout = some outher destination we want everything else to go to, 
  maybe just sys.stderr? Or to io.StrinIO()?
# before terminating: close the new stdout and do whatever needed with it
# before terminating, flush and close the old stdout in a finally block
# to make sure
# the other side receives an end of file, also in the finally block, terminate


"""

# This provides the class and decorator for turning user-classes and
# functions into PRs and a main that can be used to run the
# user's code after importing it


import sys
import traceback
import gatenlp
from argparse import ArgumentParser
from loguru import logger
import inspect
from gatenlp.document import Document
from gatenlp.changelog import ChangeLog


class _PrWrapper:
    def __init__(self):
        self.func_execute = None   # the function to process each doc
        self.func_execute_allowkws = False
        self.func_start   = None   # called when processing starts
        self.func_start_allowkws = False
        self.func_finish  = None   # called when processing finishes
        self.func_finish_allowkws = False
        self.func_reduce = None    # function for combining results
        self.func_reduce_allowkws = False
        self.script_parms = None   # Script parms to pass to each execute

    def execute(self, doc):
        if self.func_execute_allowkws:
            ret = self.func_execute(doc, **self.script_parms)
        else:
            ret = self.func_execute(doc)
        if ret is None:
            if doc.changelog is None:
                ret = doc
            else:
                ret = doc.changelog
        return ret

    def start(self, script_params):
        self.script_parms = script_params
        # TODO: amend the script params with additional data from here?
        if self.func_start is not None:
            if self.func_start_allowkws:
                self.func_start(**self.script_parms)
            else:
                self.func_start()

    def finish(self):
        if self.func_finish is not None:
            if self.func_finish_allowkws:
                self.func_finish(**self.script_parms)
            else:
                self.func_finish()

    def reduce(self, resultslist):
        if self.func_reduce is not None:
            if self.func_reduce_allowkws:
                ret = self.func_reduce(resultslist, **self.script_parms)
            else:
                ret = self.func_reduce(resultslist, **self.script_parms)
            return ret


def _check_exec(func):
    """
    Check the signature of the func to see if it is a proper
    execute function: must accept one (or more optional) args
    and can accept kwargs. This returns true of kwargs are accepted
    :param func: the function to check
    :return: true if the function accepts kwargs
    """
    argspec = inspect.getfullargspec(func)
    if len(argspec.args) == 1 \
          or len(argspec.args) == 2 and argspec.args[0] == "self" \
          or argspec.varargs is not None:
        pass
    else:
        raise Exception("Processing resource execution function does not accept exactly one or any number of arguments")
    if argspec.varkw is not None:
        return True
    else:
        return False


def _has_method(theobj, name):
    """
    Check if the object has a callable method with the given name,
    if yes return the method, otherwise return None
    :param theobj: the object that contains the method
    :param name: the name of the method
    :return: the method or None
    """
    tmp = getattr(theobj, name, None)
    if tmp is not None and callable(tmp):
        return tmp
    else:
        return None


def _pr_decorator(what):
    """
    This is the decorator to identify a class or function as a processing
    resource. This is made available with the name PR in the gatenlp
    package.

    This creates an instance of PRWrapper and registers all the relevant
    functions of the decorated class or the decorated function in the
    wrapper.
    """
    gatenlp.gate_python_plugin_pr = "The PR from here!!!"

    wrapper = _PrWrapper()
    if inspect.isclass(what):
        execmethod = _has_method(what, "execute")
        if not execmethod:
            execmethod = _has_method(what, "__call__")
        if not execmethod:
            raise Exception("PR does not have an execute(doc) or __call__(doc) method.")
        allowkws = _check_exec(execmethod)
        wrapper.func_execute_allowkws = allowkws
        startmethod = _has_method(what, "start")
        if startmethod:
            wrapper.func_start = startmethod
            if inspect.getfullargspec(startmethod).varkw:
                wrapper.func_start_allowkws = True
        finishmethod = _has_method(what, "finish")
        if finishmethod:
            wrapper.func_finish = finishmethod
            if inspect.getfullargspec(finishmethod).varkw:
                wrapper.func_finish_allowkws = True
        reducemethod = _has_method(what, "reduce")
        if reducemethod:
            wrapper.func_reduce = reducemethod
            if inspect.getfullargspec(reducemethod).varkw:
                wrapper.func_reduce_allowkws = True

    elif inspect.isfunction(what):
        allowkws = _check_exec(what)
        wrapper.func_execute = what
        wrapper.func_execute_allowkws = allowkws
    else:
        raise Exception("Decorator applied to something that is not a function or class")
    gatenlp.gate_python_plugin_pr = wrapper
    return wrapper


class DefaultPr:
    def __call__(self, doc, **kwargs):
        logger.info(f"called __call__ with doc={doc}, kwargs={kwargs}")
        return doc

    def start(self, **kwargs):
        logger.info(f"called start with kwargs={kwargs}")
        return None

    def finish(self, **kwargs):
        logger.info(f"called finish with kwargs={kwargs}")
        return None

    def reduce(self, resultlist, **kwargs):
        logger.info(f"called finish with results {resultlist} and kwargs={resultlist}")
        return None


def interact():
    """
    Starts and handles the interaction with a GATE python plugin process.
    This will get started by the GATE plugin if the interaction uses
    pipes, but can also be started separately for http/websockets.

    This MUST be called in the user's python file!
    The python file should also have one class or function decorated
    with the @gatenlp.PR  decorator to identify it as the
    processing resource to the system.

    :return:
    """

    # before we do anything we need to check if a PR has actually
    # been defined. If not, use our own default debugging PR
    if gatenlp.gate_python_plugin_pr is None:
        logger.warning("No processing resource defined with @gatenlp.PR decorator, using default do-nothing")
        _pr_decorator(DefaultPr())

    pr = gatenlp.gate_python_plugin_pr

    argparser = ArgumentParser()
    argparser.add_argument("--mode", default="pipe",
                           help="Interaction mode: pipe|http|websockets")
    argparser.add_argument("--format", default="json",
                           help="Exchange format: json|flatbuffers")
    argparser.add_argument("-d", action="store_true",
                           help="Enable debugging: log to stderr")
    args = argparser.parse_args()

    if args.format == "json":
        from gatenlp.docformats.simplejson import loads, dumps
    elif args.format == "flatbuffers":
        raise Exception("Not implemented yet!")
    else:
        raise Exception(f"Not a supported interchange format: {args.format}")

    if args.mode == "pipe":
        # save the current stdout, assign stderr to sys.stdout
        # use saved stdout or internal stdout for pipe
        # loop: read commands from the python plugin
        #   - when we hit EOF, terminate
        #   - when we get the stop command, ackgnowledge and terminate
        #   - when we catch an exception: how to avoid deadlock?
        #   - process the commands by calling the appropriate function
        instream = sys.stdin
        ostream = sys.stdout
        for line in instream:
            request = loads(line)
            cmd = request.get("cmd", None)
            stop_requested = False
            ret = None
            try:
                if cmd == "execute":
                    doc = request.get("document")
                    doc.set_changelog(ChangeLog())
                    pr.execute(doc)
                    # NOTE: for now we just discard what the method returns and always return
                    # the changelog instead!
                    ret = doc.changelog
                elif cmd == "start":
                    parms = request.get("parameters")
                    pr.func_start(parms)
                elif cmd == "finish":
                    pr.func_finish()
                elif cmd == "reduce":
                    results = request.get("results")
                    ret = pr.func_reduce(results)
                elif cmd == "stop":
                    stop_requested = True
                else:
                    raise Exception(f"Odd command receive: {cmd}")
                response = {
                    "return": ret,
                    "status": "ok",
                }
            except Exception as ex:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                error = repr(ex)
                info = "\n".join(traceback.format_tb(exc_traceback))
                response = {
                    "return": None,
                    "status": "error",
                    "error": error,
                    "info": info
                }
            print(dumps(response), file=ostream)
            ostream.flush()
            if stop_requested:
                break
        # TODO: do any cleanup/restoring needed
    elif args.mode == "http":
        raise Exception("Mode http not implemented yet")
    elif args.mode == "websockets":
        raise Exception("Mode websockets not implemented yet")
    else:
        raise Exception(f"Not a valid mode: {args.mode}")

