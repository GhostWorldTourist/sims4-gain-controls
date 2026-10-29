"""Gain Controls against a stand-in for the game: one multiplier, applied once.

The bug this mod exists to avoid is a multiplier applied twice per change (MCCC
2026.5 scales both of the multipliers BaseStatistic.add_value combines). These
tests model add_value as the game does - skill-based multiplier times
get_statistic_multiplier_increase/decrease - and check the setting lands once,
only on the statistics it names, and survives a second patch pass.

    py tests/test_gain.py
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BaseStatistic:
    guid64 = 0
    is_skill = False
    hidden = False

    def __init__(self):
        self.value = 0.0

    @classmethod
    def get_skill_based_statistic_multiplier(cls, targets, amount):
        return 1.0

    def get_statistic_multiplier_increase(self):
        return 1.0

    def get_statistic_multiplier_decrease(self):
        return 1.0

    def add_value(self, amount, interaction=None):
        m = 1.0
        if interaction is not None:
            m = self.get_skill_based_statistic_multiplier((), amount)
        m *= self.get_statistic_multiplier_decrease() if amount < 0 else self.get_statistic_multiplier_increase()
        self.value += amount * m


def tuned(name, **attrs):
    return type(name, (BaseStatistic,), attrs)


class Manager:
    def __init__(self, classes):
        self.types = {i: c for i, c in enumerate(classes)}
        self.callbacks = []

    def add_on_load_complete(self, cb):
        self.callbacks.append(cb)


def load_mod(tmp, classes):
    manager = Manager(classes)
    commands = types.SimpleNamespace(
        Command=lambda *a, **k: (lambda f: f),
        CommandType=types.SimpleNamespace(Live=1),
        CheatOutput=lambda conn: (lambda msg: OUT.append(msg)))
    sys.modules['services'] = types.SimpleNamespace(get_instance_manager=lambda t: manager)
    sims4 = types.ModuleType('sims4')
    sims4.commands = commands
    sims4.resources = types.SimpleNamespace(Types=types.SimpleNamespace(STATISTIC='statistic'))
    sys.modules['sims4'] = sims4
    sys.modules['sims4.commands'] = commands
    sys.modules['sims4.resources'] = sims4.resources
    pkg = os.path.join(tmp, 'GainControls.ts4script', 'gwt_gain_controls')
    shutil.copytree(os.path.join(ROOT, 'src', 'gwt_gain_controls'), pkg)
    sys.path.insert(0, os.path.dirname(pkg))
    sys.modules.pop('gwt_gain_controls', None)
    mod = importlib.import_module('gwt_gain_controls')
    sys.path.pop(0)
    return mod, manager


OUT = []


class GainControls(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.Friend = tuned('LTR_Friendship_Main', guid64=16650)
        self.Romance = tuned('LTR_Romance_Main', guid64=16651)
        self.Cooking = tuned('statistic_Skill_AdultMajor_HomeStyleCooking', guid64=16705, is_skill=True)
        self.Hidden = tuned('statistic_Skill_Hidden', guid64=99, is_skill=True, hidden=True)
        self.Hunger = tuned('motive_Hunger', guid64=16656)
        self.mod, self.manager = load_mod(self.tmp, [self.Friend, self.Romance, self.Cooking, self.Hidden, self.Hunger])
        for cb in self.manager.callbacks:
            cb(self.manager)

    def gain(self, cls, amount=10.0, interaction=object()):
        s = cls()
        s.add_value(amount, interaction=interaction)
        return s.value

    def test_default_is_the_game(self):
        for cls in (self.Friend, self.Romance, self.Cooking, self.Hunger):
            self.assertAlmostEqual(10.0, self.gain(cls))

    def test_applied_once_with_or_without_an_interaction(self):
        self.mod.gains('friendship', '0.5')
        self.assertAlmostEqual(5.0, self.gain(self.Friend))
        self.assertAlmostEqual(5.0, self.gain(self.Friend, interaction=None))

    def test_each_setting_reaches_only_its_statistic(self):
        self.mod.gains('romance', '0.25')
        self.mod.gains('skill', '2')
        self.assertAlmostEqual(10.0, self.gain(self.Friend))
        self.assertAlmostEqual(2.5, self.gain(self.Romance))
        self.assertAlmostEqual(20.0, self.gain(self.Cooking))
        self.assertAlmostEqual(10.0, self.gain(self.Hidden))
        self.assertAlmostEqual(10.0, self.gain(self.Hunger))

    def test_losses_have_their_own_setting(self):
        self.mod.gains('friendship', '0.5')
        self.mod.gains('friendship_loss', '2')
        self.assertAlmostEqual(-20.0, self.gain(self.Friend, -10.0))
        self.assertAlmostEqual(-10.0, self.gain(self.Cooking, -10.0))   # skills: gains only

    def test_a_second_patch_pass_does_not_double(self):
        self.mod.gains('friendship', '0.5')
        self.mod.patch(self.manager)
        self.assertAlmostEqual(5.0, self.gain(self.Friend))

    def test_stacks_once_with_another_wrapper_beneath(self):
        """Another mod wrapping the base method still sees one application of ours."""
        base = BaseStatistic.get_statistic_multiplier_increase
        BaseStatistic.get_statistic_multiplier_increase = lambda self: base(self) * 0.9
        self.addCleanup(setattr, BaseStatistic, 'get_statistic_multiplier_increase', base)
        self.mod.gains('friendship', '0.5')
        self.assertAlmostEqual(4.5, self.gain(self.Friend))

    def test_settings_persist_and_bad_values_are_refused(self):
        self.mod.gains('skill', '0.3')
        self.assertFalse(self.mod.gains('skill', '-1'))
        self.assertFalse(self.mod.gains('skill', 'fast'))
        self.assertFalse(self.mod.gains('charisma', '2'))
        saved = json.load(open(self.mod.CONFIG, encoding='utf-8'))
        self.assertEqual(0.3, saved['skill'])
        self.mod.gains('reset')
        self.assertEqual(1.0, json.load(open(self.mod.CONFIG, encoding='utf-8'))['skill'])

    def test_config_sits_beside_the_script_not_inside_it(self):
        self.assertEqual(os.path.normcase(self.tmp), os.path.normcase(os.path.dirname(self.mod.CONFIG)))
        self.assertTrue(self.mod.CONFIG.endswith('GhostWorldTourist_GainControls.cfg'))
        self.assertNotIn('.ts4script' + os.sep + 'GhostWorldTourist', self.mod.CONFIG)


if __name__ == '__main__':
    unittest.main()
