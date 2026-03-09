from util.injector import inject, inject_to, is_injectable


class TestInject:
    def test_wraps_function(self):
        def original(x):
            return x * 2

        def wrapper(orig_fn, x):
            return orig_fn(x) + 1

        injected = inject(original, wrapper)
        assert injected(5) == 11  # (5 * 2) + 1

    def test_preserves_name(self):
        def my_function(x):
            return x

        def wrapper(orig_fn, x):
            return orig_fn(x)

        injected = inject(my_function, wrapper)
        assert injected.__name__ == "my_function"

    def test_passes_args_and_kwargs(self):
        def original(a, b, key=None):
            return (a, b, key)

        def wrapper(orig_fn, a, b, key=None):
            return orig_fn(a, b, key=key)

        injected = inject(original, wrapper)
        assert injected(1, 2, key="hello") == (1, 2, "hello")


class TestInjectTo:
    def test_replaces_method_on_object(self):
        class Target:
            def greet(self, name):
                return "Hello, " + name

        target = Target()

        @inject_to(Target, "greet")
        def new_greet(original, self, name):
            return original(self, name) + "!"

        assert target.greet("World") == "Hello, World!"

    def test_returns_new_function(self):
        class Target:
            def method(self):
                pass

        @inject_to(Target, "method")
        def replacement(original, self):
            pass

        assert replacement is not None

    def test_chained_injections(self):
        class Target:
            def value(self):
                return 1

        @inject_to(Target, "value")
        def add_ten(original, self):
            return original(self) + 10

        @inject_to(Target, "value")
        def double(original, self):
            return original(self) * 2

        t = Target()
        # double(add_ten(original)) = (1 + 10) * 2 = 22
        assert t.value() == 22


class TestIsInjectable:
    def test_compatible_signatures(self):
        def target(a, b):
            pass

        def new_fn(original, a, b):
            pass

        assert is_injectable(target, new_fn)

    def test_incompatible_signatures(self):
        def target(a, b, c):
            pass

        def new_fn(original, a):
            pass

        assert not is_injectable(target, new_fn)

    def test_no_args(self):
        def target():
            pass

        def new_fn(original):
            pass

        assert is_injectable(target, new_fn)
