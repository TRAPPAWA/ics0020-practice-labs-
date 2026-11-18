#!/usr/bin/env python3
"""Small SQLite analytics shell for the ICS0020 statistics lab.

Loads the three CSV evidence files into an in-memory SQLite database and
registers a few statistical aggregate functions that stock SQLite lacks.
"""
import argparse, csv, math, sqlite3, sys
from pathlib import Path

DATA = Path('/data') if Path('/data').exists() else Path(__file__).resolve().parents[1] / 'data'

class StddevPop:
    def __init__(self): self.n=0; self.s=0.0; self.ss=0.0
    def step(self, x):
        if x is None: return
        x=float(x); self.n+=1; self.s+=x; self.ss+=x*x
    def finalize(self):
        if self.n == 0: return None
        var=max(0.0, self.ss/self.n - (self.s/self.n)**2)
        return math.sqrt(var)

class Median:
    def __init__(self): self.v=[]
    def step(self, x):
        if x is not None: self.v.append(float(x))
    def finalize(self):
        if not self.v: return None
        v=sorted(self.v); n=len(v); m=n//2
        return v[m] if n%2 else (v[m-1]+v[m])/2

class Percentile:
    def __init__(self): self.v=[]; self.p=None
    def step(self, x, p):
        if x is None: return
        self.v.append(float(x))
        if p is not None: self.p=float(p)
    def finalize(self):
        if not self.v or self.p is None: return None
        p=min(1.0,max(0.0,self.p)); v=sorted(self.v)
        if len(v)==1: return v[0]
        pos=(len(v)-1)*p; lo=math.floor(pos); hi=math.ceil(pos)
        if lo==hi: return v[lo]
        return v[lo] + (v[hi]-v[lo])*(pos-lo)

def infer(value):
    if value == '': return None
    try: return int(value)
    except ValueError: pass
    try: return float(value)
    except ValueError: return value

def load_table(conn, table, path):
    with open(path, newline='', encoding='utf-8') as f:
        r=csv.DictReader(f); rows=list(r); cols=r.fieldnames
    types=[]
    for c in cols:
        sample=[infer(row[c]) for row in rows[:200] if row[c] != '']
        if sample and all(isinstance(x,int) for x in sample): t='INTEGER'
        elif sample and all(isinstance(x,(int,float)) for x in sample): t='REAL'
        else: t='TEXT'
        types.append(t)
    conn.execute(f"CREATE TABLE {table} ({', '.join(f'\"{c}\" {t}' for c,t in zip(cols,types))})")
    q=f"INSERT INTO {table} VALUES ({','.join('?' for _ in cols)})"
    conn.executemany(q, [[infer(row[c]) for c in cols] for row in rows])

def db():
    c=sqlite3.connect(':memory:')
    c.create_aggregate('STDDEV_POP',1,StddevPop)
    c.create_aggregate('MEDIAN',1,Median)
    c.create_aggregate('PERCENTILE',2,Percentile)
    load_table(c,'auth',DATA/'auth_hourly.csv')
    load_table(c,'network',DATA/'network_hourly.csv')
    load_table(c,'pipeline',DATA/'pipeline_hourly.csv')
    return c

def fmt(v):
    if v is None: return 'NULL'
    if isinstance(v,float): return f'{v:.6g}'
    return str(v)

def print_table(cur):
    rows=cur.fetchall(); headers=[d[0] for d in cur.description]
    vals=[[fmt(x) for x in row] for row in rows]
    widths=[len(h) for h in headers]
    for row in vals:
        for i,x in enumerate(row): widths[i]=max(widths[i],len(x))
    print(' | '.join(h.ljust(widths[i]) for i,h in enumerate(headers)))
    print('-+-'.join('-'*w for w in widths))
    for row in vals: print(' | '.join(x.ljust(widths[i]) for i,x in enumerate(row)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('query', nargs='?')
    ap.add_argument('-f','--file')
    ap.add_argument('--csv', action='store_true')
    args=ap.parse_args()
    if args.file: sql=Path(args.file).read_text(encoding='utf-8')
    elif args.query: sql=args.query
    else: sql=sys.stdin.read()
    conn=db()
    # Execute all statements, print only result-bearing ones.
    statements=[s.strip() for s in sql.split(';') if s.strip()]
    for i,stmt in enumerate(statements):
        cur=conn.execute(stmt)
        if cur.description:
            if args.csv:
                w=csv.writer(sys.stdout); w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
            else:
                print_table(cur)
            if i != len(statements)-1: print()

if __name__=='__main__': main()
