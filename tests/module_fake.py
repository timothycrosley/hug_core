"""Fake HUG API module usable for testing importation of modules"""
import hug_core


class FakeException(BaseException):
    pass


@hug_core.directive(apply_globally=False)
def my_directive(default=None, **kwargs):
    """for testing"""
    return default


@hug_core.default_input_format("application/made-up")
def made_up_formatter(data):
    """for testing"""
    return data


@hug_core.default_output_format()
def output_formatter(data):
    """for testing"""
    return hug_core.output_format.json(data)


@hug_core.get()
def made_up_api(hug_core_my_directive=True):
    """for testing"""
    return hug_core_my_directive


@hug_core.directive(apply_globally=True)
def my_directive_global(default=None, **kwargs):
    """for testing"""
    return default


@hug_core.default_input_format("application/made-up", apply_globally=True)
def made_up_formatter_global(data):
    """for testing"""
    return data


@hug_core.default_output_format(apply_globally=True)
def output_formatter_global(data, request=None, response=None):
    """for testing"""
    return hug_core.output_format.json(data)


@hug_core.request_middleware()
def handle_request(request, response):
    """for testing"""
    return


@hug_core.startup()
def on_startup(api):
    """for testing"""
    return


@hug_core.static()
def static():
    """for testing"""
    return ("",)


@hug_core.sink("/all")
def sink(path):
    """for testing"""
    return path


@hug_core.exception(FakeException)
def handle_exception(exception):
    """Handles the provided exception for testing"""
    return True


@hug_core.not_found()
def not_found_handler():
    """for testing"""
    return True
