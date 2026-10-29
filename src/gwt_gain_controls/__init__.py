"""Gain Controls by GhostWorldTourist.

Sets how fast Sims gain (and lose) friendship and romance, and how fast they
gain skills, as plain multipliers: 0.5 is half speed, 2 is double, 1 is the game.

Each multiplier is applied exactly once per change. The game multiplies every
statistic change by get_statistic_multiplier_increase (or _decrease for a loss);
this wraps that one method, and only on the friendship and romance tracks and
on visible skills, so nothing else in the game pays for it.

Settings live in GhostWorldTourist_GainControls.cfg beside this script, and
change live with the cheat-free console command:

    gwt.gains                       show the current multipliers
    gwt.gains friendship 0.5        friendship gain at half speed
    gwt.gains romance_loss 2        romance falls twice as fast
    gwt.gains skill 0.25            skills at a quarter speed
    gwt.gains reset                 everything back to 1 (the game's speed)

If another mod also scales these (MCCC's difficulty settings, for one), the two
stack. Set MCCC's Friendship, Romance and Skill Difficulty Adjustment to 0 to use
this instead.
"""
import json
import os
import traceback

import services
import sims4.commands
import sims4.resources

FRIENDSHIP_TRACK = 16650      # LTR_Friendship_Main
ROMANCE_TRACK = 16651         # LTR_Romance_Main
KEYS = ('friendship', 'friendship_loss', 'romance', 'romance_loss', 'skill')
LIMIT = 100.0

# __file__ is <Mods folder>/<name>.ts4script/gwt_gain_controls/__init__.py: the
# settings go in the folder holding the .ts4script, beside it, never inside it.
_HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(_HERE, 'GhostWorldTourist_GainControls.cfg')
LOG = os.path.join(_HERE, 'GhostWorldTourist_GainControls.log')

SETTINGS = {k: 1.0 for k in KEYS}
PATCHED = []


def log(msg):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(msg.rstrip() + '\n')
    except OSError:
        pass


def load():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        save()
        return
    except (OSError, ValueError):
        log('could not read %s, using 1.0 for everything:\n%s' % (CONFIG, traceback.format_exc()))
        return
    for k in KEYS:
        try:
            v = float(data.get(k, 1.0))
        except (TypeError, ValueError):
            continue
        if 0 <= v <= LIMIT:
            SETTINGS[k] = v


def save():
    try:
        with open(CONFIG, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, indent=2)
    except OSError:
        log('could not write %s:\n%s' % (CONFIG, traceback.format_exc()))


# --- the one hook --------------------------------------------------------------

def _wrap(cls, direction, key):
    """Scale cls.get_statistic_multiplier_<direction> by SETTINGS[key], once."""
    name = 'get_statistic_multiplier_' + direction
    if getattr(getattr(cls, name), '_gwt_gain_key', None) is not None:
        return False                     # inherited from a class already wrapped
    own = cls.__dict__.get(name)
    # Resolve the parent's method at call time, not now: a mod that wraps
    # BaseStatistic after this runs must still sit beneath us, not be bypassed.
    if own is not None:
        def wrapped(self):
            return own(self) * SETTINGS[key]
    else:
        def wrapped(self):
            return getattr(super(cls, self), name)() * SETTINGS[key]
    wrapped._gwt_gain_key = key
    wrapped.__name__ = name
    setattr(cls, name, wrapped)
    return True


def targets(manager):
    """(class, gain key, loss key or None) for every statistic this mod scales."""
    out = []
    for cls in manager.types.values():
        guid = getattr(cls, 'guid64', None)
        if guid == FRIENDSHIP_TRACK:
            out.append((cls, 'friendship', 'friendship_loss'))
        elif guid == ROMANCE_TRACK:
            out.append((cls, 'romance', 'romance_loss'))
        elif getattr(cls, 'is_skill', False) and not getattr(cls, 'hidden', False):
            out.append((cls, 'skill', None))
    return out


def patch(manager):
    for cls, gain, loss in targets(manager):
        if _wrap(cls, 'increase', gain):
            PATCHED.append(cls)
        if loss:
            _wrap(cls, 'decrease', loss)
    found = {getattr(c, 'guid64', None) for c in PATCHED}
    missing = [n for i, n in ((FRIENDSHIP_TRACK, 'friendship'), (ROMANCE_TRACK, 'romance')) if i not in found]
    log('scaling %d statistics (%d skills)%s; settings %s' % (
        len(PATCHED), sum(1 for c in PATCHED if getattr(c, 'is_skill', False)),
        ('; NOT FOUND: ' + ', '.join(missing)) if missing else '', json.dumps(SETTINGS)))


def _on_statistics_loaded(manager):
    try:
        patch(manager)
    except Exception:
        log('patching failed, the game runs at its own speed:\n' + traceback.format_exc())


# --- console -------------------------------------------------------------------

def describe():
    return ', '.join('%s %g' % (k, SETTINGS[k]) for k in KEYS)


@sims4.commands.Command('gwt.gains', command_type=sims4.commands.CommandType.Live)
def gains(key: str = None, value: str = None, _connection=None):
    out = sims4.commands.CheatOutput(_connection)
    if key is None:
        out('Gain Controls: ' + describe())
        return True
    key = key.lower()
    if key == 'reset':
        for k in KEYS:
            SETTINGS[k] = 1.0
        save()
        out('Gain Controls reset: ' + describe())
        return True
    if key not in KEYS or value is None:
        out('Usage: gwt.gains [%s] <multiplier>, or gwt.gains reset' % '|'.join(KEYS))
        return False
    try:
        v = float(value)
    except ValueError:
        out('%r is not a number' % value)
        return False
    if not 0 <= v <= LIMIT:
        out('Use a multiplier from 0 to %g (1 is the game\'s own speed).' % LIMIT)
        return False
    SETTINGS[key] = v
    save()
    out('Gain Controls: ' + describe())
    return True


load()
services.get_instance_manager(sims4.resources.Types.STATISTIC).add_on_load_complete(_on_statistics_loaded)
