"""Fake HUG API module usable for testing importation of modules"""
import hug_core


@hug_core.get()
def made_up_hello():
    """GETting for science!"""
    return "hello from GET"


@hug_core.post()
def made_up_hello():
    """POSTing for science!"""
    return "hello from POST"
