"""Incident Lab must not turn every later turn into a remediation project."""
import importlib.util
import json
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / '__init__.py'
    spec = importlib.util.spec_from_file_location('incidentlab_under_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _State:
    def __init__(self):
        self.d = {}

    def get(self, key, default=None):
        return self.d.get(key, default)

    def set(self, key, value):
        self.d[key] = value


class _Ctx:
    def __init__(self):
        self.state = _State()
        self.hooks = {}

    def register_hook(self, name, fn):
        self.hooks[name] = fn


def _ctx():
    ctx = _Ctx()
    _load().register(ctx)
    return ctx


def _fail(ctx, sid='s1', tool='terminal'):
    ctx.hooks['post_tool_call'](session_id=sid, tool_name=tool,
                                result=json.dumps({'exit_code': 2, 'error': 'x'}))


def test_same_incident_is_reported_once_not_every_turn():
    ctx = _ctx()
    _fail(ctx)
    first = ctx.hooks['pre_llm_call'](session_id='s1')
    assert first and 'tool:terminal:error' in first['context']
    assert ctx.hooks['pre_llm_call'](session_id='s1') is None


def test_new_occurrence_is_reported_again():
    ctx = _ctx()
    _fail(ctx)
    ctx.hooks['pre_llm_call'](session_id='s1')
    _fail(ctx)
    again = ctx.hooks['pre_llm_call'](session_id='s1')
    assert again and 'tool:terminal:error' in again['context']


def test_expected_nonzero_exit_is_not_an_incident():
    ctx = _ctx()
    ctx.hooks['post_tool_call'](session_id='s1', tool_name='terminal', result=json.dumps(
        {'exit_code': 1, 'exit_code_meaning': 'No matches found (not an error)'}))
    assert ctx.hooks['pre_llm_call'](session_id='s1') is None


def test_reminder_does_not_mandate_side_projects():
    ctx = _ctx()
    _fail(ctx)
    text = ctx.hooks['pre_llm_call'](session_id='s1')['context']
    assert 'add a reproducing check' not in text
    assert 'Then diagnose the cause' not in text


def test_other_session_unaffected():
    ctx = _ctx()
    _fail(ctx, sid='s1')
    assert ctx.hooks['pre_llm_call'](session_id='s2') is None
