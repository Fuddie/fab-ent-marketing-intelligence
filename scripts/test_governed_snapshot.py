"""Readiness must fail on source, build, file or live-database drift."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import duckdb
import governed_snapshot as snapshot
import validate_wren
from validate_wren import MODELS


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for folder in ['docs/data','wren/target','data/generated']:
            (self.root/folder).mkdir(parents=True)
        self.dbpath=self.root/'data/generated/fab_ent.duckdb'
        (self.root/'wren/target/mdl.json').write_text('{}')
        (self.root/'wren/connection_info.json').write_text(json.dumps(dict(datasource='duckdb',format='duckdb',url='../data/generated')))
        models=[]
        with duckdb.connect(str(self.dbpath)) as db:
            db.execute('CREATE SCHEMA raw_marts')
            for model,(suffix,_) in MODELS.items():
                table='raw_marts.mart_marketing__'+suffix
                db.execute(f'CREATE TABLE {table} AS SELECT * FROM (VALUES (1), (1), (NULL)) t(value)')
                path=self.root/'docs/data'/f'{model}.parquet'
                db.execute(f"COPY {table} TO '{path.as_posix()}' (FORMAT PARQUET)")
                models.append(dict(model=model,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),governed_schema=[dict(name='value',type='INTEGER')]))
        self.manifest=dict(models=models,source_sha256='source',mdl_sha256=hashlib.sha256(b'{}').hexdigest())
        self.save()
        root=patch.object(snapshot,'ROOT',self.root);root.start();self.addCleanup(root.stop)
        digest=patch.object(snapshot,'source_digest',return_value='source');digest.start();self.addCleanup(digest.stop)
        models=patch.object(validate_wren,'MODELS',{model:(suffix,['value']) for model,(suffix,_) in MODELS.items()})
        models.start();self.addCleanup(models.stop)

    def save(self):
        (self.root/'docs/snapshot.json').write_text(json.dumps(self.manifest))

    def test_matching_snapshot_and_duplicate_null_parity(self):
        self.assertEqual(snapshot.check_snapshot(),'source')
        suffix=next(iter(MODELS.values()))[0]
        with duckdb.connect(str(self.dbpath)) as db:
            db.execute(f'DELETE FROM raw_marts.mart_marketing__{suffix} WHERE value IS NULL')
        with self.assertRaisesRegex(RuntimeError,'Live database differs'):
            snapshot.check_snapshot()

    def test_source_build_and_checksum_drift(self):
        with patch.object(snapshot,'source_digest',return_value='changed'):
            with self.assertRaisesRegex(RuntimeError,'Governed sources changed'):
                snapshot.check_snapshot()
        (self.root/'wren/target/mdl.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(RuntimeError,'Wren build differs'):
            snapshot.check_snapshot()
        (self.root/'wren/target/mdl.json').write_text('{}')
        path=next((self.root/'docs/data').glob('*.parquet'))
        path.write_bytes(b'broken')
        with self.assertRaisesRegex(RuntimeError,'checksum'):
            snapshot.check_snapshot()

    def test_wrong_wren_database(self):
        (self.root/'wren/connection_info.json').write_text(json.dumps(dict(datasource='duckdb',format='duckdb',url='../other')))
        with self.assertRaisesRegex(RuntimeError,'governed project'):
            snapshot.check_snapshot()


if __name__=='__main__':unittest.main()
