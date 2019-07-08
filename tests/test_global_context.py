import hug_core


def test_context_global_decorators(hug_core_api):
    custom_context = dict(context="global", factory=0, delete=0)

    @hug_core.context_factory(apply_globally=True)
    def create_context(*args, **kwargs):
        custom_context["factory"] += 1
        return custom_context

    @hug_core.delete_context(apply_globally=True)
    def delete_context(context, *args, **kwargs):
        assert context == custom_context
        custom_context["delete"] += 1

    @hug_core.get(api=hug_core_api)
    def made_up_hello():
        return "hi"

    @hug_core.extend_api(api=hug_core_api, base_url="/api")
    def extend_with():
        import tests.module_fake_simple

        return (tests.module_fake_simple,)

    assert hug_core.test.get(hug_core_api, "/made_up_hello").data == "hi"
    assert custom_context["factory"] == 1
    assert custom_context["delete"] == 1
    assert hug_core.test.get(hug_core_api, "/api/made_up_hello").data == "hello"
    assert custom_context["factory"] == 2
    assert custom_context["delete"] == 2
