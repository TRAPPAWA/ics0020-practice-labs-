#!/usr/bin/env python3
import argparse,csv,html
from pathlib import Path

def esc(s): return html.escape(str(s), quote=True)

def main():
    ap=argparse.ArgumentParser(description='Render a simple CSV line/bar chart as SVG')
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--x',required=True); ap.add_argument('--y',required=True,help='one column or comma-separated columns')
    ap.add_argument('--title',default='Chart'); ap.add_argument('--kind',choices=['line','bar'],default='line')
    args=ap.parse_args(); ycols=[x.strip() for x in args.y.split(',') if x.strip()]
    rows=list(csv.DictReader(open(args.input,encoding='utf-8')))
    labels=[]; series={c:[] for c in ycols}
    for r in rows:
        vals=[]; ok=True
        for c in ycols:
            try: vals.append(float(r[c]))
            except (KeyError,ValueError,TypeError): ok=False; break
        if ok:
            labels.append(r[args.x])
            for c,v in zip(ycols,vals): series[c].append(v)
    if not labels: raise SystemExit('no numeric rows to plot')
    W,H=980,440; L,R,T,B=85,40,65,90; pw=W-L-R; ph=H-T-B
    all_y=[v for c in ycols for v in series[c]]; ymin=min(0,min(all_y)); ymax=max(all_y)
    if ymax==ymin: ymax=ymin+1
    def X(i): return L + (i/(max(1,len(labels)-1)))*pw
    def Y(y): return T + ph - ((y-ymin)/(ymax-ymin))*ph
    colors=['#1f77b4','#d62728','#2ca02c','#9467bd','#ff7f0e']
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{W/2}" y="28" text-anchor="middle" font-family="sans-serif" font-size="20">{esc(args.title)}</text>',
         f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" stroke="black"/>',
         f'<line x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}" stroke="black"/>']
    for j in range(5):
        v=ymin+(ymax-ymin)*j/4; yy=Y(v)
        out.append(f'<line x1="{L-5}" y1="{yy}" x2="{L+pw}" y2="{yy}" stroke="#ddd"/>')
        out.append(f'<text x="{L-10}" y="{yy+4}" text-anchor="end" font-family="sans-serif" font-size="11">{v:.3g}</text>')
    if args.kind=='bar' and len(ycols)>1:
        raise SystemExit('bar mode supports one y column')
    for si,c in enumerate(ycols):
        color=colors[si%len(colors)]; vals=series[c]
        if args.kind=='line':
            path=' '.join((('M' if i==0 else 'L')+f' {X(i):.1f} {Y(y):.1f}') for i,y in enumerate(vals))
            out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>')
            for i,y in enumerate(vals): out.append(f'<circle cx="{X(i):.1f}" cy="{Y(y):.1f}" r="2.3" fill="{color}"/>')
        else:
            bw=max(2,pw/max(1,len(vals))*0.7)
            for i,y in enumerate(vals):
                x=X(i)-bw/2; yy=Y(y); h=T+ph-yy
                out.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{color}"/>')
        lx=L+si*180; ly=48
        out.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
        out.append(f'<text x="{lx+28}" y="{ly+4}" font-family="sans-serif" font-size="12">{esc(c)}</text>')
    step=max(1,len(labels)//8)
    for i,label in enumerate(labels):
        if i%step==0 or i==len(labels)-1:
            out.append(f'<text x="{X(i):.1f}" y="{T+ph+20}" text-anchor="start" font-family="sans-serif" font-size="10" transform="rotate(35 {X(i):.1f} {T+ph+20})">{esc(label)}</text>')
    out.append('</svg>')
    Path(args.output).write_text('\n'.join(out)+'\n',encoding='utf-8')
    print(args.output)
if __name__=='__main__': main()
