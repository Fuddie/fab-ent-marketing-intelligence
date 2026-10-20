"""Internal subprocess: read-only physical-mart parity with a hard parent deadline."""
import json
from pathlib import Path
import sys
from decimal import Decimal
from datetime import date, datetime
import duckdb
from validate_wren import reference

if __name__ == '__main__':
    with duckdb.connect(str(Path(__file__).resolve().parents[1]/'data/generated/fab_ent.duckdb'),read_only=True) as db:
        def encode(value):
            if isinstance(value,Decimal): return {'__decimal__':str(value)}
            if isinstance(value,(date,datetime)): return {'__date__':value.isoformat()}
            raise TypeError(type(value).__name__)
        print(json.dumps(reference(db,sys.stdin.read()),default=encode))
