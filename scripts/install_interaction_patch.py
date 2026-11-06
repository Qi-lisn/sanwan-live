#!/usr/bin/env python3
"""Safely apply narrowly scoped interaction edits to DSH live/server.py.

Run from the repository root after copying live/{interaction,brain_delivery}.py.
Refuses unexpected server versions and creates .bak for rollback.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

IMPORT_HOOK = 'import interaction\nimport brain_delivery\n'
COMMENT_HOOK = '''                if os.environ.get("SANWAN_DELIVERY_CHAT") == "1":
                    game = interaction.handle_comment(nick, text, delivery)
                    if game is not None:
                        heard = bool(game.get("reply"))
                        if heard:
                            with _lock:
                                _priority.append({"text": game["reply"],
                                                  "comment": {"nick": nick, "text": text}})
                                _stats["replies"] += 1
                        payload = json.dumps({"ok": True, "replied": heard,
                                              "interaction": game.get("kind")},
                                             ensure_ascii=False).encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Content-Length", str(len(payload)))
                        self.end_headers(); self.wfile.write(payload)
                        return
'''

AMBIENT_HOOK = '''    if os.environ.get("SANWAN_DELIVERY_CHAT") == "1":
        return {"text": interaction.scene_line(delivery.snapshot()), "comment": None}
'''


def apply(code: str) -> tuple[str, list[str]]:
    edits = []
    if IMPORT_HOOK not in code:
        needle = 'import delivery\n'
        if code.count(needle) != 1:
            raise RuntimeError("cannot identify import delivery location")
        code = code.replace(needle, needle + IMPORT_HOOK, 1)
        edits.append("import interaction/brain_delivery")

    if COMMENT_HOOK not in code:
        # Place AFTER singing command handling, BEFORE existing old-persona
        # trigger/DeepSeek routing. This preserves crisis and song priority.
        needle = '                _bo = False\n                for _kw, _ans in TRIGGERS.items():\n'
        if code.count(needle) != 1:
            raise RuntimeError("cannot identify /comment fallback anchor")
        code = code.replace(needle, COMMENT_HOOK + needle, 1)
        edits.append("/comment delivery route")

    needle = '                        hit = brain.reply(nick, text)'
    replacement = '''                        if os.environ.get("SANWAN_DELIVERY_CHAT") == "1":
                            hit = brain_delivery.reply(nick, text, delivery.snapshot())
                        else:
                            hit = brain.reply(nick, text)'''
    if replacement not in code:
        if code.count(needle) != 1:
            raise RuntimeError("cannot identify existing DeepSeek reply call")
        code = code.replace(needle, replacement, 1)
        edits.append("DeepSeek scene-aware persona")

    if AMBIENT_HOOK not in code:
        needle = '    if _seg is not None:\n        if _seg_i < len(_seg["lines"]):\n'
        if code.count(needle) != 1:
            raise RuntimeError("cannot identify next_line script anchor")
        code = code.replace(needle, AMBIENT_HOOK + needle, 1)
        edits.append("delivery scene ambient dialogue")
    compile(code, '<server.py>', 'exec')
    return code, edits


def apply_delivery(code: str) -> tuple[str, list[str]]:
    """Apply queued destination preference to BOTH original and v1 delivery.py."""
    hook = '''    if not place:
        # A viewer may have chosen the NEXT destination while we were delivering.
        try:
            import interaction
            place = interaction.consume_destination()
        except ImportError:
            pass
'''
    if hook in code:
        return code, []
    import re
    needle = re.compile(r'(def new_order\(now=None, rng=None, place=None\):\n)')
    if len(needle.findall(code)) != 1:
        raise RuntimeError("cannot identify delivery.new_order signature")
    patched = needle.sub(lambda m: m.group(1) + hook, code, count=1)
    compile(patched, '<delivery.py>', 'exec')
    return patched, ["queue viewer-selected destination"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='.', help='DSH repository root')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    target = root / 'live' / 'server.py'
    for helper in ('interaction.py', 'brain_delivery.py'):
        if not (root / 'live' / helper).is_file():
            raise SystemExit(f'Missing {helper}; copy the supplied live/ files first')
    original = target.read_text(encoding='utf-8')
    patched, edits = apply(original)
    delivery_target = root / 'live' / 'delivery.py'
    delivery_original = delivery_target.read_text(encoding='utf-8')
    delivery_patched, delivery_edits = apply_delivery(delivery_original)
    if args.dry_run:
        print('Dry run; prospective edits:', ', '.join(edits + delivery_edits) or 'already applied')
        return
    if patched == original and delivery_patched == delivery_original:
        print('Already applied; nothing to change')
        return
    backup = target.with_name('server.py.before-interaction.bak')
    if backup.exists() and backup.read_text(encoding='utf-8') != original:
        raise SystemExit('Backup already exists and differs; abort to protect existing work')
    if not backup.exists():
        backup.write_text(original, encoding='utf-8')
    delivery_backup = delivery_target.with_name('delivery.py.before-interaction.bak')
    if delivery_backup.exists() and delivery_backup.read_text(encoding='utf-8') != delivery_original:
        raise SystemExit('Delivery backup differs; abort before writing')
    if delivery_patched != delivery_original and not delivery_backup.exists():
        delivery_backup.write_text(delivery_original, encoding='utf-8')
    if patched != original:
        target.write_text(patched, encoding='utf-8')
    if delivery_patched != delivery_original:
        delivery_target.write_text(delivery_patched, encoding='utf-8')
    print('Applied:', ', '.join(edits + delivery_edits)); print('Backups:', backup, delivery_backup)


if __name__ == '__main__':
    main()
