"""Gain Controls - build script.

Packs src/gwt_gain_controls into GhostWorldTourist_GainControls.ts4script, as
source: the game compiles it on load (zipimport), so no Python 3.7 is needed to
build it. Writes out/GhostWorldTourist_GainControls.zip for Vortex or a manual
install, and refuses to write anything naming the builder's account.

Author: GhostWorldTourist
"""
import io, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
NAME = 'GhostWorldTourist_GainControls'
OUT = os.path.join(HERE, 'out', NAME + '.zip')
FORBIDDEN = [os.path.basename(os.path.expanduser('~')).lower().encode()]


def stored(z, name, data):
    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))   # fixed time: same source, same bytes
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    z.writestr(info, data)


def main():
    script = io.BytesIO()
    with zipfile.ZipFile(script, 'w') as z:
        for dp, _, fns in sorted(os.walk(SRC)):
            for fn in sorted(fns):
                if fn.endswith('.py'):
                    p = os.path.join(dp, fn)
                    stored(z, os.path.relpath(p, SRC).replace(os.sep, '/'), open(p, 'rb').read())
    data = script.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if any(w in z.read(n).lower() for w in FORBIDDEN):
                raise SystemExit('%s names the builder account - refusing to build' % n)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, 'w') as z:
        stored(z, NAME + '.ts4script', data)
    print('wrote %s (%d bytes of script)' % (OUT, len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
