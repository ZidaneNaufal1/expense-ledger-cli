"""Pencatatan pengeluaran lokal dalam satu mata uang."""
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import sqlite3
import sys

APP_ID = 1163416647
MAX_AMOUNT = 999999999999


def money(text):
    try:
        amount = Decimal(text)
        if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
            raise ValueError
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise ValueError
        return int(amount * 100)
    except (InvalidOperation, ValueError, TypeError, OverflowError):
        raise ValueError('Jumlah harus positif, maksimal 999999999999 dan dapat dibulatkan ke dua desimal.') from None


def valid_date(text):
    try:
        if len(text) != 10 or date.fromisoformat(text).isoformat() != text:
            raise ValueError
        return text
    except (ValueError, TypeError):
        raise ValueError('Tanggal harus YYYY-MM-DD yang valid.') from None


def valid_month(text):
    valid_date(text + '-01')
    return text


def category(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 64 or any(ord(x) < 32 or ord(x) == 127 for x in text):
        raise ValueError('Kategori harus 1–64 karakter tanpa karakter kontrol.')
    return text.strip()


def open_db(path, create=False):
    path = Path(path).absolute()
    for p in (path, *path.parents):
        if p.is_symlink() or (p.exists() and getattr(p.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Path symlink/reparse tidak didukung.')
    new = not path.exists()
    if new and not create:
        raise ValueError('Database belum ada.')
    if new:
        with path.open('xb'):
            pass
    c = sqlite3.connect(path)
    try:
        if new:
            c.execute('CREATE TABLE expenses (id INTEGER PRIMARY KEY, day TEXT NOT NULL, category TEXT NOT NULL, cents INTEGER NOT NULL CHECK(cents > 0))')
            c.execute('CREATE TABLE budgets (month TEXT PRIMARY KEY, cents INTEGER NOT NULL CHECK(cents > 0))')
            c.execute(f'PRAGMA application_id={APP_ID}')
            c.execute('PRAGMA user_version=1')
            c.commit()
        if c.execute('PRAGMA application_id').fetchone()[0] != APP_ID or c.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('Database asing atau versi schema tidak didukung.')
        for table, expected in [('expenses', ['id','day','category','cents']), ('budgets', ['month','cents'])]:
            if [r[1] for r in c.execute(f'PRAGMA table_info({table})')] != expected:
                raise ValueError('Schema database tidak sesuai.')
        return c
    except BaseException:
        c.close()
        raise


def format_money(cents):
    return f'{cents // 100}.{cents % 100:02d}'


def add(c, day, cat, amount):
    values = (valid_date(day), category(cat), money(amount))
    with c:
        return c.execute('INSERT INTO expenses(day,category,cents) VALUES(?,?,?)', values).lastrowid


def budget(c, month, amount):
    values = (valid_month(month), money(amount))
    with c:
        c.execute('INSERT INTO budgets(month,cents) VALUES(?,?) ON CONFLICT(month) DO UPDATE SET cents=excluded.cents', values)


def summary(c, month):
    month = valid_month(month)
    rows = c.execute('SELECT category,SUM(cents) FROM expenses WHERE substr(day,1,7)=? GROUP BY category ORDER BY category', (month,)).fetchall()
    b = c.execute('SELECT cents FROM budgets WHERE month=?', (month,)).fetchone()
    total = sum(x[1] for x in rows)
    return {'month': month, 'categories': [(cat, format_money(n)) for cat,n in rows], 'total': format_money(total), 'budget': format_money(b[0]) if b else None, 'remaining': format_money(b[0]-total) if b and b[0]>=total else ('-' + format_money(total-b[0]) if b else None)}


def export_csv(c, path):
    path = Path(path)
    with path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['day','category','amount'])
        for day, cat, cents in c.execute('SELECT day,category,cents FROM expenses ORDER BY id'):
            # Spreadsheet-safe categories; prefix is removed only by our import.
            encoded = "'" + cat if cat.startswith(('=', '+', '-', '@', "'")) else cat
            writer.writerow([day, encoded, format_money(cents)])


def import_csv(c, path):
    pending = []
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, strict=True)
        if reader.fieldnames != ['day','category','amount']:
            raise ValueError('Header CSV harus day,category,amount.')
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Baris CSV tidak sesuai header.')
            cat = row['category']
            if cat.startswith("'"):
                cat = cat[1:]
            pending.append((valid_date(row['day']), category(cat), money(row['amount'])))
            if len(pending) > 10000:
                raise ValueError('Maksimal 10000 baris per impor.')
    with c:
        c.executemany('INSERT INTO expenses(day,category,cents) VALUES(?,?,?)', pending)
    return len(pending)


def main(argv=None):
    p=argparse.ArgumentParser(description='Catatan pengeluaran lokal, satu mata uang.')
    p.add_argument('--db', type=Path, required=True)
    sub=p.add_subparsers(dest='command', required=True)
    a=sub.add_parser('add'); a.add_argument('--date',required=True); a.add_argument('--category',required=True); a.add_argument('--amount',required=True)
    b=sub.add_parser('budget'); b.add_argument('--month',required=True); b.add_argument('--amount',required=True)
    s=sub.add_parser('summary'); s.add_argument('--month',required=True)
    e=sub.add_parser('export'); e.add_argument('file',type=Path)
    i=sub.add_parser('import'); i.add_argument('file',type=Path)
    args=p.parse_args(argv)
    try:
        if args.command in ('import','export') and args.file.resolve() == args.db.resolve():
            raise ValueError('CSV dan database harus berbeda.')
        c=open_db(args.db, create=args.command in ('add','budget','import'))
        try:
            if args.command=='add': print('Pengeluaran disimpan:', add(c,args.date,args.category,args.amount))
            elif args.command=='budget': budget(c,args.month,args.amount); print('Anggaran disimpan.')
            elif args.command=='summary':
                result=summary(c,args.month)
                print('Bulan:', result['month'])
                for cat,amount in result['categories']: print(f'{cat}: {amount}')
                print('Total:',result['total']); print('Anggaran:',result['budget'] or '-'); print('Sisa:',result['remaining'] if result['remaining'] is not None else '-')
            elif args.command=='export': export_csv(c,args.file); print('CSV disimpan.')
            else: print('Baris diimpor:',import_csv(c,args.file))
        finally: c.close()
        return 0
    except (ValueError, OSError, sqlite3.Error, csv.Error) as exc:
        print('Gagal:',str(exc),file=sys.stderr); return 2


if __name__=='__main__':
    raise SystemExit(main())
