# Gain Controls

Set how fast Sims gain friendship, romance and skills, as plain multipliers:
`0.5` is half speed, `2` is double, `1` is the game's own speed.

| setting | scales |
|---|---|
| `friendship` / `friendship_loss` | friendship going up / going down |
| `romance` / `romance_loss` | romance going up / going down |
| `skill` | skill gain (every visible skill) |

Change them in game with the console (no cheats needed):

```
gwt.gains                    show the current multipliers
gwt.gains friendship 0.5     friendship at half speed
gwt.gains romance 0.3        romance at 30%
gwt.gains skill 0.25         skills at a quarter speed
gwt.gains reset              everything back to 1
```

Settings are saved to `GhostWorldTourist_GainControls.cfg` beside the script,
take effect immediately, and can also be edited there (plain JSON). Decay is not
touched: this changes what interactions add, not how fast relationships fade.

## Why it exists

MCCC's Friendship, Romance and Skill Difficulty Adjustment apply their ratio
twice to every gain (MCCC 2026.5), so -1 is 0.81x rather than 0.9x and -20 is
0.0025x rather than 0.05x. This applies each multiplier exactly once: the game
scales every statistic change by `get_statistic_multiplier_increase` (or
`_decrease` for a loss), and this wraps that one method on the friendship and
romance tracks and on visible skills only, so nothing else pays for it.

**Set MCCC's three Difficulty Adjustment settings to 0 when using this**, or the
two stack.

## Install

`py build.py` writes `out/GhostWorldTourist_GainControls.zip`. Install it with
Vortex, or put the `.ts4script` directly in `Mods` (no deeper than one folder).
Script mods must be enabled in the game options.

`py tests/test_gain.py` runs the tests against a stand-in for the game's
statistics, including that a setting lands once and stacks correctly with
another mod's wrapper.

By GhostWorldTourist.
