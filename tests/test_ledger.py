from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
import ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name); self.db=self.path/'a.db'
        self.c=ledger.open_db(self.db,create=True); self.addCleanup(self.c.close)

    def test_half_up_and_invalid_amounts(self):
        self.assertEqual(ledger.money('1.005'),101)
        for x in ['-1','0','0.001','NaN','Infinity','x','1000000000000']:
            with self.subTest(x=x),self.assertRaises(ValueError): ledger.money(x)

    def test_summary_budget_and_month_isolation(self):
        ledger.add(self.c,'2026-10-01','Makan','10.005')
        ledger.add(self.c,'2026-10-02','Makan','2.50')
        ledger.add(self.c,'2026-11-02','Transport','99')
        ledger.budget(self.c,'2026-10','10')
        r=ledger.summary(self.c,'2026-10')
        self.assertEqual(r['categories'], [('Makan','12.51')]); self.assertEqual(r['total'],'12.51'); self.assertEqual(r['remaining'],'-2.51')

    def test_csv_roundtrip_and_formula_protection(self):
        for cat in ['=SUM(A1)', "'example", 'Makan']:
            ledger.add(self.c,'2026-10-01',cat,'1.23')
        csvpath=self.path/'a.csv'; ledger.export_csv(self.c,csvpath)
        self.assertIn("'=SUM(A1)", csvpath.read_text())
        with closing(ledger.open_db(self.path/'b.db',create=True)) as other:
            self.assertEqual(ledger.import_csv(other,csvpath),3)
            self.assertEqual(other.execute('SELECT category,cents FROM expenses ORDER BY id').fetchall(),self.c.execute('SELECT category,cents FROM expenses ORDER BY id').fetchall())
        with self.assertRaises(FileExistsError): ledger.export_csv(self.c,csvpath)

    def test_import_invalid_rolls_back(self):
        p=self.path/'invalid.csv'; p.write_text('day,category,amount\n2026-10-01,Food,1\n2026-10-02,Bad,-5\n',encoding='utf-8')
        with self.assertRaises(ValueError): ledger.import_csv(self.c,p)
        self.assertEqual(self.c.execute('SELECT COUNT(*) FROM expenses').fetchone()[0],0)

    def test_invalid_date_and_category(self):
        for day in ['2026-02-30','2026-1-01','x']:
            with self.assertRaises(ValueError): ledger.valid_date(day)
        for cat in ['', 'a\nb', 'x'*65]:
            with self.assertRaises(ValueError): ledger.category(cat)

    def test_foreign_db_preserved(self):
        p=self.path/'foreign.db'
        with closing(sqlite3.connect(p)) as c,c: c.execute('CREATE TABLE important(x)')
        before=p.read_bytes()
        with self.assertRaises(ValueError): ledger.open_db(p,create=True)
        self.assertEqual(before,p.read_bytes())

    def test_csv_invalid_header(self):
        p=self.path/'bad.csv'; p.write_text('date,amount\n',encoding='utf-8')
        with self.assertRaises(ValueError): ledger.import_csv(self.c,p)


if __name__=='__main__': unittest.main()
