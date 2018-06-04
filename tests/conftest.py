import asyncio
import contextlib
import gc
import sys

import pytest


try:
    import uvloop
except ImportError:  # pragma: no cover
    uvloop = None


try:
    import tokio
except ImportError:  # pragma: no cover
    tokio = None


def pytest_addoption(parser):
    parser.addoption(
        '--fast', action='store_true', default=False,
        help='run tests faster by disabling extra checks')
    parser.addoption(
        '--loop', action='store', default='pyloop',
        help='run tests with specific loop: pyloop, uvloop, or all')
    parser.addoption(
        '--enable-loop-debug', action='store_true', default=False,
        help='enable event loop debug mode')


@contextlib.contextmanager
def loop_context(loop_factory=asyncio.new_event_loop, fast=False):
    """A contextmanager that creates an event_loop, for test purposes.

    Handles the creation and cleanup of a test loop.
    """
    loop = setup_test_loop(loop_factory)
    yield loop
    teardown_test_loop(loop, fast=fast)


def setup_test_loop(loop_factory=asyncio.new_event_loop):
    """Create and return an asyncio.BaseEventLoop instance.

    The caller should also call teardown_test_loop, once they are done
    with the loop.
    """
    loop = loop_factory()
    try:
        module = loop.__class__.__module
        skip_watcher = 'uvloop' in module
    except AttributeError:
        # Just in case
        skip_watcher = True
    asyncio.set_event_loop(loop)
    if sys.platform != 'win32' and not skip_watcher:
        policy = asyncio.get_event_loop_policy()
        watcher = asyncio.SafeChildWatcher()
        watcher.attach_loop(loop)
        with contextlib.suppress(NotImplementedError):
            policy.set_child_watcher(watcher)
    return loop


def teardown_test_loop(loop, fast=False):
    """Teardown and cleanup an event_loop created by setup_test_loop."""
    closed = loop.is_closed()
    if not closed:
        loop.call_soon(loop.stop)
        loop.run_forever()
        loop.close()

    if not fast:
        gc.collect()

    asyncio.set_event_loop(None)


def pytest_generate_tests(metafunc):
    if 'loop_factory' not in metafunc.fixturenames:
        return

    loops = metafunc.config.getoption('--loop')
    avail_factories = {'pyloop': asyncio.DefaultEventLoopPolicy}

    if uvloop is not None:  # pragma: no cover
        avail_factories['uvloop'] = uvloop.EventLoopPolicy

    if tokio is not None:  # pragma: no cover
        avail_factories['tokio'] = tokio.EventLoopPolicy

    if loops == 'all':
        loops = 'pyloop,uvloop?,tokio?'

    factories = {}
    for name in loops.split(','):
        required = not name.endswith('?')
        name = name.strip(' ?')
        if name in avail_factories:
            factories[name] = avail_factories[name]
        elif required:
            raise ValueError(
                'Unknown loop "%s", available loops: %s' % (
                    name, list(avail_factories.keys())))

    metafunc.parametrize('loop_factory',
                         list(factories.values()),
                         ids=list(factories.keys()))


def pytest_pycollect_makeitem(collector, name, obj):
    """Fix pytest collecting for coroutines."""
    if collector.funcnamefilter(name) and asyncio.iscoroutinefunction(obj):
        return list(collector._genfunctions(name, obj))


def pytest_pyfunc_call(pyfuncitem):
    """Run coroutines in an event loop instead of a normal function call."""
    if asyncio.iscoroutinefunction(pyfuncitem.function):
        testargs = {arg: pyfuncitem.funcargs[arg]
                    for arg in pyfuncitem._fixtureinfo.argnames}

        _loop = pyfuncitem.funcargs.get('loop', None)
        task = _loop.create_task(pyfuncitem.obj(**testargs))
        _loop.run_until_complete(task)

        return True


@pytest.fixture
def loop(loop_factory, request):
    """Return an instance of the event loop."""
    fast = request.config.getoption('--fast')
    debug = request.config.getoption('--enable-loop-debug')

    policy = loop_factory()
    asyncio.set_event_loop_policy(policy)
    with loop_context(fast=fast) as _loop:
        if debug:
            _loop.set_debug(True)  # pragma: no cover
        asyncio.set_event_loop(_loop)
        yield _loop
