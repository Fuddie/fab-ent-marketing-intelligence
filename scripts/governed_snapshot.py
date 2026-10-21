"""Bind browser exports, semantic builds and the local database to governed inputs."""
import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def source_digest():
    paths = [ROOT / 'METRIC_CONTRACT.md', ROOT / 'dbt_project.yml']
    for folder, pattern in [('data/raw', '*.csv'), ('data/raw', '*.yml'),
                            ('models', '*.sql'), ('models', '*.yml'), ('macros', '*.sql'),
                            ('wren/models', '*.yml'), ('wren/cubes', '*.yml'),
                            ('wren/knowledge', '*.md')]:
        paths.extend((ROOT / folder).rglob(pattern))
    paths.extend(ROOT / 'wren' / name for name in ['relationships.yml', 'wren_project.yml'])
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def check_snapshot():
    # This process is independently timed by the question service. Never hash a
    # live DuckDB file: inspect its logical contents through a read-only connection.
    from validate_wren import MODELS, compare, reference
    report = json.loads((ROOT / 'docs/snapshot.json').read_text(encoding='utf-8'))
    if report.get('source_sha256') != source_digest():
        raise RuntimeError('Governed sources changed. Rebuild, validate Wren and export the dashboard together.')
    mdl = ROOT / 'wren/target/mdl.json'
    if report.get('mdl_sha256') != hashlib.sha256(mdl.read_bytes()).hexdigest():
        raise RuntimeError('Wren build differs from the exported snapshot.')
    connection = json.loads((ROOT / 'wren/connection_info.json').read_text(encoding='utf-8-sig'))
    directory = Path(connection['url'])
    database = (directory if directory.is_absolute() else ROOT / 'wren' / directory) / 'fab_ent.duckdb'
    if (connection.get('datasource'), connection.get('format')) != ('duckdb', 'duckdb') or database.resolve() != (ROOT / 'data/generated/fab_ent.duckdb').resolve():
        raise RuntimeError('Wren must use the governed project DuckDB database.')
    inventory = {item['model']: item for item in report['models']}
    if set(inventory) != set(MODELS):
        raise RuntimeError('Snapshot model inventory differs.')
    with duckdb.connect(str(database.resolve()), read_only=True) as db:
        for model, (suffix, keys) in MODELS.items():
            path = ROOT / 'docs/data' / (model + '.parquet')
            if hashlib.sha256(path.read_bytes()).hexdigest() != inventory[model]['sha256']:
                raise RuntimeError('Snapshot checksum differs: ' + model)
            table = 'raw_marts.mart_marketing__' + suffix
            schema = [{'name': row[0], 'type': row[1]} for row in db.execute('DESCRIBE ' + table).fetchall()]
            if schema != inventory[model]['governed_schema']:
                raise RuntimeError('Live database schema differs: ' + model)
            # Wren transports floating ratios at limited precision. Use the same
            # published tolerance as export; money/counts/NULLs remain exact.
            order = ', '.join(keys)
            expected = reference(db, f'SELECT * FROM {table} ORDER BY {order}')
            escaped = str(path).replace("'", "''")
            actual = reference(db, f"SELECT * FROM read_parquet('{escaped}') ORDER BY {order}")
            try:
                compare(actual, expected, model)
            except AssertionError as error:
                raise RuntimeError('Live database differs from browser snapshot: ' + model) from error
    return source_digest()


if __name__ == '__main__':
    check_snapshot()
    print('PASS: governed sources, Wren build, database and browser snapshot agree')
