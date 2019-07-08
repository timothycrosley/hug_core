"""Simple 1 endpoint Fake HUG API module usable for testing importation of modules"""
import hug_core


class FakeSimpleException(Exception):
    pass


@hug_core.get()
def made_up_hello():
    """for science!"""
    return "hello"


@hug_core.get("/exception")
def made_up_exception():
    raise FakeSimpleException("test")
