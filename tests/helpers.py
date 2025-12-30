from functools import lru_cache

from wakepy import Method, MethodInfo

TEST_MODE = "test-mode"


@lru_cache(maxsize=None)
def get_test_method(name: str, mode_name: str = TEST_MODE) -> Method:
    class TestMethod(Method): ...

    TestMethod.mode_name = mode_name
    TestMethod.name = name

    return TestMethod()


def get_method_info(method_name: str, mode_name: str = TEST_MODE) -> MethodInfo:
    """Get a MethodInfo object for the given method name."""
    method = get_test_method(method_name, mode_name=mode_name)
    return MethodInfo._from_method(method)
