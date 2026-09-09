from flask import Flask, request, redirect, url_for, render_template_string, session, flash, send_file
from datetime import datetime, timedelta
from pathlib import Path
from email.message import EmailMessage
import sqlite3, os, smtplib, ssl, io, threading, time, html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me')
BASE = Path(__file__).resolve().parent
DB = BASE / 'billiard_club.db'


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c


def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        number INTEGER NOT NULL,
        price REAL NOT NULL DEFAULT 30000,
        active INTEGER NOT NULL DEFAULT 0,
        started_at TEXT,
        paused_at TEXT,
        paused_seconds INTEGER NOT NULL DEFAULT 0,
        UNIQUE(kind, number)
    );
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        number INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        qty INTEGER NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL,
        total REAL NOT NULL,
        cost_total REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS receipts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        number INTEGER NOT NULL,
        started_at TEXT,
        ended_at TEXT NOT NULL,
        seconds INTEGER NOT NULL,
        table_total REAL NOT NULL,
        product_total REAL NOT NULL,
        grand_total REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS receipt_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total REAL NOT NULL
    );
    ''')
    defaults = {
        'club_name':'BILYARD CLUB', 'login_password':'', 'admin_password':'',
        'smtp_user':'', 'smtp_password':'', 'report_email':'',
        'report_time':'23:59', 'last_report_date':'',
        'smtp_host':'smtp.gmail.com', 'smtp_port':'587',
        'background_url':'https://images.unsplash.com/photo-1517840901100-8179e982acb7?auto=format&fit=crop&w=1800&q=80'
    }
    for k,v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)',(k,v))
    for i in range(1,6):
        c.execute("INSERT OR IGNORE INTO tables(kind,number,price) VALUES('BILLIARD',?,30000)",(i,))
    for i in range(1,4):
        c.execute("INSERT OR IGNORE INTO tables(kind,number,price) VALUES('TENNIS',?,30000)",(i,))
    if c.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
        items = [
            ('Suv 0.5L','Ichimlik',3000,0),('Suv 1L','Ichimlik',5000,0),
            ('Suv 1.5L','Ichimlik',7000,0),('Suv 2L','Ichimlik',9000,0),
            ('Coca-Cola 0.5L','Ichimlik',7000,0),('Coca-Cola 1L','Ichimlik',11000,0),
            ('Fanta 0.5L','Ichimlik',7000,0),('Sprite 0.5L','Ichimlik',7000,0),
            ('Pepsi 0.5L','Ichimlik',7000,0),('Chips','Gazak',10000,4000),
            ('Suxarik','Gazak',8000,3000),('Shokolad','Gazak',10000,5000),
            ("Yong'oq",'Gazak',15000,8000),('Pullik tayoqcha','Tayoqcha',5000,0)
        ]
        c.executemany('INSERT INTO products(name,category,price,cost) VALUES(?,?,?,?)', items)
    c.commit(); c.close()

init_db()


def get(k):
    c=db(); r=c.execute('SELECT v FROM settings WHERE k=?',(k,)).fetchone(); c.close(); return r['v'] if r else ''


def setv(k,v):
    c=db(); c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',(k,str(v))); c.commit(); c.close()


def now(): return datetime.now().replace(microsecond=0)

def parse_dt(x): return datetime.fromisoformat(x) if x else None

def money(x): return f"{float(x):,.0f}".replace(',',' ') + " so'm"

def elapsed(r):
    if not r['active'] or not r['started_at']: return 0
    start=parse_dt(r['started_at'])
    pause=parse_dt(r['paused_at']) if r['paused_at'] else None
    ref = pause if pause else now()
    return max(0, int((ref-start).total_seconds()) - int(r['paused_seconds'] or 0))

def fmt(s):
    s=int(s); return f'{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}'


def admin_ok():
    p=get('admin_password')
    if not p: flash('Avval Sozlamalar orqali admin parolini o\'rnating.'); return False
    return session.get('admin') is True

STYLE = '''
*{box-sizing:border-box}body{margin:0;min-height:100vh;color:#edf5f8;font-family:Segoe UI,Arial;background:radial-gradient(circle at 15% 10%,#345a70 0,#0a151e 38%,#020608 100%);background-attachment:fixed}body:after{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(120deg,rgba(255,255,255,.04),transparent 35%,rgba(0,0,0,.25))}nav{position:sticky;top:0;z-index:10;display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 16px;background:rgba(3,7,10,.86);backdrop-filter:blur(14px);border-bottom:1px solid #274657}.brand{margin-right:auto;color:#f0c75e;font-weight:900;font-size:20px;text-shadow:0 4px 18px #000}.btn{display:inline-block;border:0;border-radius:12px;padding:10px 14px;background:#173446;color:#fff;text-decoration:none;cursor:pointer;box-shadow:0 8px 20px #0004}.gold{background:linear-gradient(135deg,#9b741d,#f4cf72,#9b741d);color:#111}.green{background:#16834d}.red{background:#ad3737}.blue{background:#1476ad}.container{max-width:1450px;margin:auto;padding:22px}.hero{text-align:center;padding:22px}.hero h1{font-size:42px;color:#f0c75e;margin:5px}.muted{color:#9fb7c4}.section{color:#f0c75e;font-size:21px;font-weight:900;margin:15px 0 9px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:15px}.card{padding:18px;border:1px solid #31566b;border-radius:20px;background:linear-gradient(145deg,#183141dd,#08131bdd);box-shadow:12px 18px 35px #0005}.busy{border-color:#853f45}.paused{border-color:#b18b39}.timer{font:900 44px Consolas,monospace;margin:13px 0;text-shadow:0 5px 18px #000}.row{display:flex;gap:7px;flex-wrap:wrap}.panel{padding:20px;border:1px solid #2c5062;border-radius:18px;background:#08131ddd;box-shadow:0 16px 35px #0005}input,select{width:100%;padding:11px;border-radius:10px;border:1px solid #35566a;background:#081019;color:#fff;margin:5px 0 12px}label{display:block;font-weight:700;margin-top:8px}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #203946;text-align:left}th{color:#f0c75e}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:900px){.two{grid-template-columns:1fr}}.flash{padding:11px;border-radius:10px;background:#183548;margin-bottom:12px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.kpi{padding:15px;border-radius:14px;background:#102633;border:1px solid #29495a}.kpi b{display:block;color:#9bb4c1}.kpi strong{display:block;color:#f0c75e;font-size:24px;margin-top:4px}.receipt{background:#fff;color:#111;max-width:780px;margin:auto;padding:26px;border-radius:14px}.receipt table{color:#111}.right{text-align:right}
'''

def page(title, body):
    flashes=''.join(f'<div class="flash">{html.escape(x)}</div>' for x in session.pop('_flashes',[]))
    return render_template_string(f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style></head><body><nav><div class="brand">{html.escape(get("club_name"))}</div><a class="btn" href="/">🏠 Bosh</a><a class="btn" href="/history">🧾 Cheklar</a><a class="btn" href="/reports">📊 Hisobot</a><a class="btn" href="/settings">⚙ Sozlamalar</a></nav><div class="container">{flashes}{body}</div></body></html>''')

@app.before_request
def guard():
    if request.endpoint in ('login','health'): return
    p=get('login_password')
    if p and session.get('logged') is not True: return redirect('/login')

@app.get('/health')
def health(): return 'OK'

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form.get('password')==get('login_password'):
            session['logged']=True; return redirect('/')
        flash('Kirish paroli noto\'g\'ri.')
    return render_template_string('''<style>body{font-family:Segoe UI;background:#071018;color:white}main{max-width:400px;margin:100px auto;padding:25px;background:#102633;border-radius:18px}input,button{width:100%;padding:12px;margin:7px 0}</style><main><h2>🔐 BILYARD CLUB</h2><form method="post"><input type="password" name="password" placeholder="Kirish paroli"><button>Kirish</button></form></main>''')

@app.get('/')
def home():
    c=db(); rows=c.execute('SELECT * FROM tables ORDER BY kind,number').fetchall(); c.close()
    cards=[]
    for r in rows:
        cls='busy' if r['active'] and not r['paused_at'] else ('paused' if r['active'] else '')
        if r['active'] and r['paused_at']: status='⏸ PAUZA'
        elif r['active']: status='🔴 BAND'
        else: status='🟢 BO\'SH'
        actions=''
        if not r['active']:
            actions=f'<a class="btn green" href="/table/{r["kind"]}/{r["number"]}/start">▶ Boshlash</a>'
        else:
            actions += (f'<a class="btn green" href="/table/{r["kind"]}/{r["number"]}/resume">▶ Davom</a>' if r['paused_at'] else f'<a class="btn gold" href="/table/{r["kind"]}/{r["number"]}/pause">⏸ Pauza</a>')
            actions += f'<a class="btn blue" href="/table/{r["kind"]}/{r["number"]}/menu">🥤 Mahsulot</a>'
            actions += f'<a class="btn red" href="/table/{r["kind"]}/{r["number"]}/finish">⏹ Tugatish / Chek</a>'
        cards.append(f'''<div class="card {cls}"><b>{r['kind']} {r['number']}</b><span style="float:right">{status}</span><div class="timer" data-base="{elapsed(r)}" data-run="{int(bool(r['active'] and not r['paused_at']))}">00:00:00</div><div class="muted">{money(r['price'])} / soat</div><div class="row" style="margin-top:12px">{actions}</div></div>''')
    script='''<script>const t0=Date.now();document.querySelectorAll('.timer').forEach(e=>{const base=+e.dataset.base,run=e.dataset.run==='1';function draw(){let s=base+(run?Math.floor((Date.now()-t0)/1000):0);e.textContent=String(Math.floor(s/3600)).padStart(2,'0')+':'+String(Math.floor(s%3600/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');requestAnimationFrame(draw)}draw()});</script>'''
    body=f'''<div class="hero"><div class="muted">5 TA BILLIARD + 3 TA TENNIS</div><h1>{html.escape(get('club_name'))}</h1><div class="muted">Real-time taymer • Pauza • Mahsulot • Chek • PDF • Gmail</div></div><div class="section">🎱 Stollar</div><div class="grid">{''.join(cards)}</div>{script}'''
    return page(get('club_name'),body)

@app.get('/table/<kind>/<int:number>/<action>')
def table_action(kind,number,action):
    c=db(); r=c.execute('SELECT * FROM tables WHERE kind=? AND number=?',(kind,number)).fetchone()
    if not r: c.close(); return 'Not found',404
    if action=='start' and not r['active']:
        c.execute('UPDATE tables SET active=1,started_at=?,paused_at=NULL,paused_seconds=0 WHERE id=?',(now().isoformat(),r['id']))
    elif action=='pause' and r['active'] and not r['paused_at']:
        c.execute('UPDATE tables SET paused_at=? WHERE id=?',(now().isoformat(),r['id']))
    elif action=='resume' and r['active'] and r['paused_at']:
        extra=int((now()-parse_dt(r['paused_at'])).total_seconds())
        c.execute('UPDATE tables SET paused_seconds=paused_seconds+?,paused_at=NULL WHERE id=?',(extra,r['id']))
    elif action=='finish' and r['active']:
        seconds=elapsed(r); table_total=seconds/3600*r['price']; ended=now().isoformat(); start=r['started_at']
        prod=c.execute('SELECT COALESCE(SUM(total),0)pt FROM sales WHERE kind=? AND number=? AND created_at>=?',(kind,number,start)).fetchone()['pt']
        prod=float(prod)
        c.execute('INSERT INTO receipts(kind,number,started_at,ended_at,seconds,table_total,product_total,grand_total,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(kind,number,start,ended,seconds,table_total,prod,table_total+prod,ended))
        rid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        items=c.execute('SELECT name,qty,unit_price,total FROM sales WHERE kind=? AND number=? AND created_at>=?',(kind,number,start)).fetchall()
        for i in items: c.execute('INSERT INTO receipt_items(receipt_id,name,qty,unit_price,total) VALUES(?,?,?,?,?)',(rid,i['name'],i['qty'],i['unit_price'],i['total']))
        c.execute('UPDATE tables SET active=0,started_at=NULL,paused_at=NULL,paused_seconds=0 WHERE id=?',(r['id'],)); c.commit(); c.close(); return redirect(f'/receipt/{rid}')
    c.commit(); c.close(); return redirect('/')

@app.get('/table/<kind>/<int:number>/menu')
def menu(kind,number):
    c=db(); ps=c.execute('SELECT * FROM products WHERE active=1 ORDER BY category,name').fetchall(); c.close()
    rows=''.join(f'<tr><td>{html.escape(p["name"])}</td><td>{html.escape(p["category"])}</td><td>{money(p["price"])}</td><td><form method="post" action="/sale/{kind}/{number}/{p["id"]}"><button class="btn blue">➕ Olish</button></form></td></tr>' for p in ps)
    return page('Mahsulotlar',f'<div class="panel"><h2>🥤 Mahsulotlar — {kind} {number}</h2><table><tr><th>Nom</th><th>Kategoriya</th><th>Narx</th><th></th></tr>{rows}</table></div>')

@app.post('/sale/<kind>/<int:number>/<int:pid>')
def sale(kind,number,pid):
    c=db(); p=c.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone(); t=c.execute('SELECT * FROM tables WHERE kind=? AND number=?',(kind,number)).fetchone()
    if p and t and t['active']:
        created=now().isoformat(); c.execute('INSERT INTO sales(kind,number,product_id,name,qty,unit_price,total,cost_total,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(kind,number,pid,p['name'],1,p['price'],p['price'],p['cost'],created)); c.commit()
    c.close(); return redirect(f'/table/{kind}/{number}/menu')

@app.get('/receipt/<int:rid>')
def receipt(rid):
    c=db(); r=c.execute('SELECT * FROM receipts WHERE id=?',(rid,)).fetchone(); items=c.execute('SELECT * FROM receipt_items WHERE receipt_id=?',(rid,)).fetchall(); c.close()
    if not r:return 'Not found',404
    rows=''.join(f'<tr><td>{html.escape(i["name"])}</td><td>{i["qty"]}</td><td>{money(i["unit_price"])}</td><td>{money(i["total"])}</td></tr>' for i in items)
    body=f'''<div class="receipt"><h2>{html.escape(get('club_name'))}</h2><p>Chek #{r['id']} — {r['kind']} {r['number']}<br>Vaqt: {fmt(r['seconds'])}<br>Sana: {r['created_at']}</p><table><tr><th>Mahsulot</th><th>Miqdor</th><th>Narx</th><th>Jami</th></tr>{rows}</table><p>Stol: <b>{money(r['table_total'])}</b><br>Mahsulotlar: <b>{money(r['product_total'])}</b></p><h2 class="right">JAMI: {money(r['grand_total'])}</h2><a class="btn blue" href="/receipt/{rid}/pdf">📄 PDF</a> <a class="btn" href="/">Bosh sahifa</a></div>'''
    return page('Chek',body)

@app.get('/receipt/<int:rid>/pdf')
def receipt_pdf(rid):
    c=db(); r=c.execute('SELECT * FROM receipts WHERE id=?',(rid,)).fetchone(); items=c.execute('SELECT * FROM receipt_items WHERE receipt_id=?',(rid,)).fetchall(); c.close()
    if not r:return 'Not found',404
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=28,leftMargin=28,topMargin=28,bottomMargin=28); styles=getSampleStyleSheet()
    story=[Paragraph(get('club_name'),styles['Title']),Paragraph(f'Chek #{r["id"]} — {r["kind"]} {r["number"]}',styles['Heading2']),Paragraph(f'Vaqt: {fmt(r["seconds"])}',styles['Normal']),Spacer(1,10)]
    data=[['Mahsulot','Miqdor','Narx','Jami']]+[[i['name'],str(i['qty']),money(i['unit_price']),money(i['total'])] for i in items]
    t=Table(data,colWidths=[250,60,100,100]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])); story += [t,Spacer(1,10),Paragraph(f'Stol: {money(r["table_total"])}',styles['Normal']),Paragraph(f'Mahsulotlar: {money(r["product_total"])}',styles['Normal']),Paragraph(f'<b>JAMI: {money(r["grand_total"])}</b>',styles['Heading2'])]; doc.build(story); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name=f'chek_{rid}.pdf',mimetype='application/pdf')

@app.get('/history')
def history():
    c=db(); rs=c.execute('SELECT * FROM receipts ORDER BY id DESC LIMIT 500').fetchall(); c.close()
    rows=''.join(f'<tr><td>#{r["id"]}</td><td>{r["kind"]} {r["number"]}</td><td>{r["created_at"]}</td><td>{fmt(r["seconds"])}</td><td>{money(r["grand_total"])}</td><td><a class="btn" href="/receipt/{r["id"]}">Ko‘rish</a></td></tr>' for r in rs)
    return page('Cheklar',f'<div class="panel"><h2>🧾 Barcha cheklar</h2><table><tr><th>#</th><th>Stol</th><th>Sana</th><th>Vaqt</th><th>Jami</th><th></th></tr>{rows}</table></div>')

def daily_pdf(d):
    start=datetime.combine(d,datetime.min.time()); end=start+timedelta(days=1); c=db()
    rs=c.execute('SELECT * FROM receipts WHERE created_at>=? AND created_at<? ORDER BY id',(start.isoformat(),end.isoformat())).fetchall()
    ps=c.execute('SELECT name,SUM(qty) qty,SUM(total) total FROM sales WHERE created_at>=? AND created_at<? GROUP BY name ORDER BY total DESC',(start.isoformat(),end.isoformat())).fetchall()
    tot=c.execute('SELECT COALESCE(SUM(table_total),0)t,COALESCE(SUM(product_total),0)p,COALESCE(SUM(grand_total),0)g FROM receipts WHERE created_at>=? AND created_at<?',(start.isoformat(),end.isoformat())).fetchone()
    cost=c.execute('SELECT COALESCE(SUM(cost_total),0)c FROM sales WHERE created_at>=? AND created_at<?',(start.isoformat(),end.isoformat())).fetchone()['c']; c.close()
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=24,leftMargin=24,topMargin=24,bottomMargin=24); st=getSampleStyleSheet(); story=[Paragraph(f'{get("club_name")} — KUNLIK HISOBOT',st['Title']),Paragraph(str(d),st['Heading2']),Spacer(1,8),Paragraph(f'Stol: <b>{money(tot["t"])}</b>',st['Normal']),Paragraph(f'Mahsulot: <b>{money(tot["p"])}</b>',st['Normal']),Paragraph(f'Jami: <b>{money(tot["g"])}</b>',st['Normal']),Paragraph(f'Sof foyda: <b>{money(float(tot["g"])-float(cost))}</b>',st['Normal']),Spacer(1,10)]
    data=[['Mahsulot','Miqdor','Jami']]+[[p['name'],str(p['qty']),money(p['total'])] for p in ps]; t=Table(data,colWidths=[280,70,120]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])); story += [Paragraph('Mahsulotlar',st['Heading2']),t,Spacer(1,10)]
    rd=[['Chek','Stol','Vaqt','Jami']]+[[f'#{r["id"]}',f'{r["kind"]} {r["number"]}',fmt(r['seconds']),money(r['grand_total'])] for r in rs]; rt=Table(rd,colWidths=[55,130,80,100]); rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])); story += [Paragraph('Barcha cheklar',st['Heading2']),rt]; doc.build(story); buf.seek(0); return buf

@app.get('/reports')
def reports():
    d=now().date(); start=datetime.combine(d,datetime.min.time()); end=start+timedelta(days=1); c=db();
    total=c.execute('SELECT COALESCE(SUM(grand_total),0)x FROM receipts WHERE created_at>=? AND created_at<?',(start.isoformat(),end.isoformat())).fetchone()['x']; count=c.execute('SELECT COUNT(*)x FROM receipts WHERE created_at>=? AND created_at<?',(start.isoformat(),end.isoformat())).fetchone()['x']; c.close()
    return page('Hisobot',f'<div class="hero"><h1>📊 Bugungi hisobot</h1><div class="muted">{d}</div></div><div class="kpis"><div class="kpi"><b>Jami savdo</b><strong>{money(total)}</strong></div><div class="kpi"><b>Cheklar</b><strong>{count} ta</strong></div></div><div class="panel" style="margin-top:18px"><a class="btn blue" href="/report/pdf">📄 PDF yuklash</a><a class="btn gold" href="/report/send-now">✉ Hozir emailga yuborish</a></div>')

@app.get('/report/pdf')
def report_pdf(): return send_file(daily_pdf(now().date()),as_attachment=True,download_name=f'kunlik_hisobot_{now().date()}.pdf',mimetype='application/pdf')

@app.route('/settings',methods=['GET','POST'])
def settings():
    if request.method=='POST':
        if not admin_ok(): return redirect('/settings')
        for k in ['club_name','login_password','admin_password','smtp_user','smtp_password','report_email','report_time','background_url']:
            setv(k,request.form.get(k,'').strip())
        c=db()
        for k,v in request.form.items():
            if k.startswith('tp_'):
                try:c.execute('UPDATE tables SET price=? WHERE id=?',(float(v),int(k[3:])))
                except:pass
            elif k.startswith('pp_'):
                try:c.execute('UPDATE products SET price=? WHERE id=?',(float(v),int(k[3:])))
                except:pass
        c.commit(); c.close(); flash('Sozlamalar saqlandi.'); return redirect('/settings')
    c=db(); ts=c.execute('SELECT * FROM tables ORDER BY kind,number').fetchall(); ps=c.execute('SELECT * FROM products WHERE active=1 ORDER BY category,name').fetchall(); c.close()
    tr=''.join(f'<tr><td>{t["kind"]} {t["number"]}</td><td><input name="tp_{t["id"]}" value="{t["price"]}"></td></tr>' for t in ts)
    pr=''.join(f'<tr><td>{html.escape(p["name"])}</td><td>{html.escape(p["category"])}</td><td><input name="pp_{p["id"]}" value="{p["price"]}"></td><td><form method="post" action="/product/delete" style="display:inline"><input type="hidden" name="pid" value="{p["id"]}"><button class="btn red">🗑</button></form></td></tr>' for p in ps)
    body=f'''<div class="two"><div class="panel"><h2>⚙ Sozlamalar</h2><form method="post"><label>Klub nomi</label><input name="club_name" value="{html.escape(get('club_name'))}"><label>Kirish paroli</label><input name="login_password" type="password" placeholder="O‘zingiz belgilang"><label>Admin paroli</label><input name="admin_password" type="password" placeholder="O‘zingiz belgilang"><label>Gmail manzili</label><input name="smtp_user" value="{html.escape(get('smtp_user'))}" placeholder="siz@gmail.com"><label>PDF qabul qiluvchi email</label><input name="report_email" value="{html.escape(get('report_email'))}" placeholder="bo‘sh qoldirsangiz Gmail manziliga boradi"><label>Gmail App Password</label><input type="hidden" name="smtp_user" value="{html.escape(get('smtp_user'))}"><input type="hidden" name="smtp_password" value="{html.escape(get('smtp_password'))}"><label>Hisobot vaqti (HH:MM)</label><input name="report_time" value="{html.escape(get('report_time'))}" placeholder="23:59"><label>Oboy rasmi URL</label><input name="background_url" value="{html.escape(get('background_url'))}"><button class="btn gold">💾 Saqlash</button></form><p class="muted">Gmail uchun oddiy Gmail paroli emas, Google App Password ishlating. Gmail manzilingizni va App Passwordni kiriting, keyin Saqlash va Gmail ulanishini tekshirishni bosing.</p><p><a class="btn blue" href="/gmail/test">✉ Gmail ulanishini tekshirish</a></p></div><div class="panel"><h3>🎱 Stol narxlari</h3><form method="post"><table><tr><th>Stol</th><th>Soat narxi</th></tr>{tr}</table><h3>🥤 Mahsulotlar</h3><table><tr><th>Nom</th><th>Kategoriya</th><th>Narx</th><th></th></tr>{pr}</table><button class="btn gold">💾 Narxlarni saqlash</button></form><hr><h3>➕ Mahsulot qo‘shish</h3><form method="post" action="/product/add"><input name="name" placeholder="Nom" required><input name="category" placeholder="Kategoriya" value="Ichimlik"><input name="price" type="number" placeholder="Narx" required><input name="cost" type="number" placeholder="Tannarx" value="0"><button class="btn blue">Qo‘shish</button></form></div></div>'''
    return page('Sozlamalar',body)

@app.post('/product/add')
def product_add():
    if not admin_ok(): return redirect('/settings')
    try:
        c=db(); c.execute('INSERT INTO products(name,category,price,cost,active) VALUES(?,?,?,?,1)',(request.form['name'],request.form.get('category','Ichimlik'),float(request.form['price']),float(request.form.get('cost','0')))); c.commit(); c.close(); flash('Mahsulot qo‘shildi.')
    except Exception as e: flash('Xato: '+str(e))
    return redirect('/settings')

@app.post('/product/delete')
def product_delete():
    if not admin_ok(): return redirect('/settings')
    c=db(); c.execute('UPDATE products SET active=0 WHERE id=?',(int(request.form['pid']),)); c.commit(); c.close(); flash('Mahsulot o‘chirildi.'); return redirect('/settings')

@app.get('/gmail/test')
def gmail_test():
    if not admin_ok(): return redirect('/settings')
    user=get('smtp_user'); pw=get('smtp_password'); host=get('smtp_host') or 'smtp.gmail.com'; port=int(get('smtp_port') or 587); to=get('report_email') or user
    if not user or not pw or not to: flash('Gmail user, App Password va hisobot emailini kiriting.'); return redirect('/settings')
    try:
        ctx=ssl.create_default_context()
        with smtplib.SMTP(host,port,timeout=25) as s:
            s.starttls(context=ctx); s.login(user,pw)
        flash('✅ Gmail ulanishi muvaffaqiyatli.')
    except Exception as e: flash('❌ Gmail ulanish xatosi: '+str(e))
    return redirect('/settings')

def send_report(target_date):
    user=get('smtp_user'); pw=get('smtp_password'); to=get('report_email') or user
    if not user or not pw or not to: return False
    buf=daily_pdf(target_date); msg=EmailMessage(); msg['Subject']=f'{get("club_name")} — {target_date} kunlik hisobot'; msg['From']=user; msg['To']=to; msg.set_content(f'{target_date} kunlik hisobot PDF ilova qilindi.')
    msg.add_attachment(buf.getvalue(),maintype='application',subtype='pdf',filename=f'kunlik_hisobot_{target_date}.pdf')
    ctx=ssl.create_default_context()
    with smtplib.SMTP(get('smtp_host') or 'smtp.gmail.com',int(get('smtp_port') or 587),timeout=30) as s:
        s.starttls(context=ctx); s.login(user,pw); s.send_message(msg)
    return True

@app.get('/report/send-now')
def report_send_now():
    if not admin_ok(): return redirect('/settings')
    try: flash('✅ PDF emailga yuborildi.' if send_report(now().date()) else 'Email sozlamalarini to‘ldiring.')
    except Exception as e: flash('❌ Email xatosi: '+str(e))
    return redirect('/settings')

def scheduler():
    while True:
        try:
            n=now(); target=(n.date()-timedelta(days=1)); hhmm=f'{n.hour:02d}:{n.minute:02d}'
            if hhmm==get('report_time') and get('last_report_date') != str(target):
                if send_report(target): setv('last_report_date',str(target))
        except Exception:
            pass
        time.sleep(20)
threading.Thread(target=scheduler,daemon=True).start()

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8080')))
