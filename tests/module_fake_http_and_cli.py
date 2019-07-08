import hug_core


@hug_core.get()
@hug_core.cli()
def made_up_go():
    return "Going!"
