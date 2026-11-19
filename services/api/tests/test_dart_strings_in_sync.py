import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
GENERATED = ROOT / "apps/mobile/lib/l10n/bot_strings.g.dart"


def test_flutter_strings_match_the_bots():
    before = GENERATED.read_text(encoding="utf-8")
    subprocess.run([sys.executable, "tools/gen_dart_strings.py"], cwd=ROOT, check=True, capture_output=True)
    assert GENERATED.read_text(encoding="utf-8") == before, "Run python tools/gen_dart_strings.py and commit the result"
