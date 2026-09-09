"""Consistent SQLite backup. Never overwrites an existing backup."""
import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
if not args.source.is_file() or args.destination.exists():
    parser.error('Source must exist; destination must be a new file.')
args.destination.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro', uri=True) as source:
    with sqlite3.connect(args.destination) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup integrity check failed.')
print('Backup created and integrity checked.')
