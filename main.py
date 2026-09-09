from flask import Flask, request, redirect, session, render_template_string, send_file
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3, os, io, smtplib, ssl, threading, time
from email.message import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app=Flask(__name__); app.secret_key=os.getenv('SECRET_KEY','change-me')
DB=Path(__file__).with_name('bilyard.db')

def conn():
    c=sqlite3.connect(DB, timeout=30); c.row_factory=sqlite3.Row; return c

def init():
    c=conn(); c.executescript('''
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);
    CREATE TABLE IF NOT EXISTS tables(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,num INTEGER,price REAL DEFAULT 30000,active INTEGER DEFAULT 0,started TEXT,paused INTEGER DEFAULT 0,paused_at TEXT,paused_total INTEGER DEFAULT 0,UNIQUE(kind,num));
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,category TEXT,price REAL,cost REAL DEFAULT 0,active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,num INTEGER,product_id INTEGER,name TEXT,qty INTEGER,unit_price REAL,total REAL,cost_total REAL,created TEXT);
    CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,num INTEGER,started TEXT,ended TEXT,seconds INTEGER,table_total REAL,product_total REAL,grand_total REAL,created TEXT);
    CREATE TABLE IF NOT EXISTS receipt_items(id INTEGER PRIMARY KEY AUTOINCREMENT,receipt_id INTEGER,name TEXT,qty INTEGER,unit_price REAL,total REAL);
    ''')
    defaults={'club_name':'BILYARD CLUB','login_password':'','admin_password':'','report_email':'','smtp_host':'smtp.gmail.com','smtp_port':'587','smtp_user':'','smtp_password':'','report_time':'23:59','background_url':'','last_report':''}
    for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(k,v))
    for i in range(1,6): c.execute("INSERT OR IGNORE INTO tables(kind,num,price) VALUES('BILLIARD',?,30000)",(i,))
    for i in range(1,4): c.execute("INSERT OR IGNORE INTO tables(kind,num,price) VALUES('TENNIS',?,30000)",(i,))
    if c.execute('SELECT COUNT(*) FROM products').fetchone()[0]==0:
        c.executemany('INSERT INTO products(name,category,price,cost) VALUES(?,?,?,?)',[("Suv 0.5L",'Ichimlik',3000,0),("Suv 1L",'Ichimlik',5000,0),("Coca-Cola 0.5L",'Ichimlik',7000,0),("Chips",'Gazak',10000,4000),("Suxarik",'Gazak',8000,3000),("Shokolad",'Gazak',10000,5000),("Yong'oq",'Gazak',15000,8000),("Pullik tayoqcha",'Tayoqcha',5000,0)])
    c.commit(); c.close()
init()

def setting(k):
    c=conn(); r=c.execute('SELECT v FROM settings WHERE k=?',(k,)).fetchone(); c.close(); return r['v'] if r else ''
def set_setting(k,v):
    c=conn(); c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,str(v))); c.commit(); c.close()
def now(): return datetime.now().replace(microsecond=0)
def money(v): return f'{float(v):,.0f}'.replace(',',' ')+' so\'m'
def secs(r):
    if not r['active'] or not r['started']: return 0
    start=datetime.fromisoformat(r['started'])
    if r['paused'] and r['paused_at']: return max(0,int((datetime.fromisoformat(r['paused_at'])-start).total_seconds())-(r['paused_total'] or 0))
    return max(0,int((now()-start).total_seconds())-(r['paused_total'] or 0))
def fmt(s): return f'{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}'

def admin_ok(): return bool(setting('admin_password')) and session.get('admin') is True

STYLE='''body{margin:0;color:#eef;background:radial-gradient(circle at 15% 0,#285a73,#09141c 40%,#020609);font-family:Segoe UI,Arial}nav{position:sticky;top:0;background:#02070ddd;padding:12px;display:flex;gap:8px;z-index:9}.brand{margin-right:auto;color:#f2c653;font-weight:900}.btn{background:#17394d;color:#fff;padding:10px 14px;border-radius:12px;text-decoration:none;border:0;display:inline-block;cursor:pointer}.gold{background:#d2a637;color:#071017}.green{background:#197848}.red{background:#972f35}.blue{background:#1976a8}.wrap{max-width:1450px;margin:auto;padding:20px}.hero{text-align:center}.hero h1{font-size:42px;color:#f2c653;text-shadow:0 8px 20px #000}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.card,.panel{background:#0c1c27dd;border:1px solid #2b5367;border-radius:18px;padding:18px;box-shadow:0 14px 30px #0005}.busy{border-color:#8d4040}.paused{border-color:#8a7430}.timer{font:900 44px Consolas,monospace;margin:15px 0}.row{display:flex;gap:8px;flex-wrap:wrap}input,select{width:100%;padding:10px;background:#061119;color:#fff;border:1px solid #2d4f60;border-radius:10px;margin:4px 0 10px}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #23414d;text-align:left}th{color:#f2c653}.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:800px){.two{grid-template-columns:1fr}}'''

def page(body):
    bg=setting('background_url'); bgi=f'<style>body{{background-image:linear-gradient(#02070b99,#02070bdd),url({bg!r});background-size:cover;background-attachment:fixed}}</style>' if bg else ''
    return render_template_string(f'<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>{STYLE}</style>{bgi}<nav><div class="brand">{setting("club_name")}</div><a class="btn" href="/">🏠 Bosh</a><a class="btn" href="/history">🧾 Cheklar</a><a class="btn" href="/reports">📊 Hisobot</a><a class="btn" href="/settings">⚙ Sozlamalar</a></nav><div class="wrap">{body}</div>')

@app.before_request
def auth():
    if request.endpoint in ('login','health'): return
    if setting('login_password') and session.get('logged') is not True: return redirect('/login')
@app.get('/health')
def health(): return 'OK'
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form.get('password','')==setting('login_password'): session['logged']=True; return redirect('/')
    return '<form method=post style="max-width:400px;margin:100px auto"><h2>🔐 Kirish</h2><input name=password type=password placeholder="Kirish paroli"><button>Kirish</button></form>'
@app.get('/logout')
def logout(): session.clear(); return redirect('/')

@app.get('/')
def home():
    c=conn(); rs=c.execute('SELECT * FROM tables ORDER BY kind,num').fetchall(); c.close(); cards=[]
    for r in rs:
        s=secs(r); running=r['active'] and not r['paused']; cl='busy' if running else ('paused' if r['paused'] else '')
        status='🔴 BAND' if running else ('⏸ PAUZA' if r['paused'] else '🟢 BO\'SH')
        if not r['active']: acts=f'<a class="btn green" href="/t/{r["kind"]}/{r["num"]}/start">▶ Boshlash</a>'
        else:
            acts=(f'<a class="btn green" href="/t/{r["kind"]}/{r["num"]}/resume">▶ Davom</a>' if r['paused'] else f'<a class="btn gold" href="/t/{r["kind"]}/{r["num"]}/pause">⏸ Pauza</a>')
            acts+=f' <a class="btn blue" href="/menu/{r["kind"]}/{r["num"]}">🥤 Mahsulot</a><a class="btn red" href="/t/{r["kind"]}/{r["num"]}/finish">⏹ Tugatish</a>'
        cards.append(f'<div class="card {cl}"><b>{r["kind"]} {r["num"]}</b><span style="float:right">{status}</span><div class="timer" data-base="{s}" data-run="{int(running)}">{fmt(s)}</div><div>{money(r["price"])} / soat</div><div class="row" style="margin-top:12px">{acts}</div></div>')
    body=f'<div class="hero"><div>5 TA BILLIARD • 3 TA TENNIS</div><h1>{setting("club_name")}</h1><p>Real-time taymer • Pauza • Chek • Mahsulot • PDF • Email • Realistik 3D uslub</p></div><div class="grid">{''.join(cards)}</div><script>const L=Date.now();document.querySelectorAll(".timer").forEach(e=>{{let b=+e.dataset.base,r=e.dataset.run==="1";function f(){{let s=b+(r?Math.floor((Date.now()-L)/1000):0);e.textContent=String(Math.floor(s/3600)).padStart(2,"0")+":"+String(Math.floor(s%3600/60)).padStart(2,"0")+":"+String(s%60).padStart(2,"0");requestAnimationFrame(f)}}f()}})</script>'
    return page(body)

@app.get('/t/<kind>/<int:num>/<action>')
def action(kind,num,action):
    c=conn(); r=c.execute('SELECT * FROM tables WHERE kind=? AND num=?',(kind,num)).fetchone(); n=now()
    if action=='start' and not r['active']: c.execute('UPDATE tables SET active=1,started=?,paused=0,paused_at=NULL,paused_total=0 WHERE id=?',(n.isoformat(),r['id']))
    elif action=='pause' and r['active'] and not r['paused']: c.execute('UPDATE tables SET paused=1,paused_at=? WHERE id=?',(n.isoformat(),r['id']))
    elif action=='resume' and r['active'] and r['paused']:
        add=int((n-datetime.fromisoformat(r['paused_at'])).total_seconds()); c.execute('UPDATE tables SET paused=0,paused_at=NULL,paused_total=paused_total+? WHERE id=?',(add,r['id']))
    elif action=='finish' and r['active']:
        s=secs(r); tt=s/3600*r['price']; ended=n.isoformat(); p=c.execute('SELECT COALESCE(SUM(total),0)x FROM sales WHERE kind=? AND num=? AND created>=?',(kind,num,r['started'])).fetchone()['x'];
        c.execute('INSERT INTO receipts(kind,num,started,ended,seconds,table_total,product_total,grand_total,created) VALUES(?,?,?,?,?,?,?,?,?)',(kind,num,r['started'],ended,s,tt,p,tt+p,ended)); rid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        items=c.execute('SELECT name,qty,unit_price,total FROM sales WHERE kind=? AND num=? AND created>=?',(kind,num,r['started'])).fetchall();
        for x in items: c.execute('INSERT INTO receipt_items(receipt_id,name,qty,unit_price,total) VALUES(?,?,?,?,?)',(rid,x['name'],x['qty'],x['unit_price'],x['total']))
        c.execute('UPDATE tables SET active=0,started=NULL,paused=0,paused_at=NULL,paused_total=0 WHERE id=?',(r['id'],)); c.commit(); c.close(); return redirect(f'/receipt/{rid}')
    c.commit(); c.close(); return redirect('/')

@app.get('/menu/<kind>/<int:num>')
def menu(kind,num):
    c=conn(); ps=c.execute('SELECT * FROM products WHERE active=1 ORDER BY category,name').fetchall(); c.close(); rows=''.join(f'<tr><td>{p["name"]}</td><td>{p["category"]}</td><td>{money(p["price"])}</td><td><form method=post action="/sale/{kind}/{num}/{p["id"]}"><button class="btn blue">➕ Olish</button></form></td></tr>' for p in ps); return page(f'<div class="panel"><h2>🥤 {kind} {num}</h2><table><tr><th>Nom</th><th>Kategoriya</th><th>Narx</th><th></th></tr>{rows}</table></div>')
@app.post('/sale/<kind>/<int:num>/<int:pid>')
def sale(kind,num,pid):
    c=conn(); p=c.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone(); t=c.execute('SELECT * FROM tables WHERE kind=? AND num=?',(kind,num)).fetchone()
    if p and t['active']: c.execute('INSERT INTO sales(kind,num,product_id,name,qty,unit_price,total,cost_total,created) VALUES(?,?,?,?,?,?,?,?,?)',(kind,num,p['id'],p['name'],1,p['price'],p['price'],p['cost'],now().isoformat())); c.commit()
    c.close(); return redirect(f'/menu/{kind}/{num}')

@app.get('/receipt/<int:rid>')
def receipt(rid):
    c=conn(); r=c.execute('SELECT * FROM receipts WHERE id=?',(rid,)).fetchone(); its=c.execute('SELECT * FROM receipt_items WHERE receipt_id=?',(rid,)).fetchall(); c.close(); rows=''.join(f'<tr><td>{x["name"]}</td><td>{x["qty"]}</td><td>{money(x["unit_price"])}</td><td>{money(x["total"])}</td></tr>' for x in its); return page(f'<div class="panel"><h2 style="text-align:center">🧾 {setting("club_name")}</h2><p>{r["kind"]} {r["num"]}<br>Vaqt: {fmt(r["seconds"])}<br>Sana: {r["created"]}</p><table><tr><th>Mahsulot</th><th>Miqdor</th><th>Narx</th><th>Jami</th></tr>{rows}</table><p>Stol: <b>{money(r["table_total"])}</b><br>Mahsulot: <b>{money(r["product_total"])}</b></p><h2>JAMI: {money(r["grand_total"])}</h2><a class="btn blue" href="/receipt/{rid}/pdf">📄 PDF</a></div>')

def daily_pdf(day):
    st=datetime.combine(day,datetime.min.time()); en=st+timedelta(days=1); c=conn(); rs=c.execute('SELECT * FROM receipts WHERE created>=? AND created<? ORDER BY id',(st.isoformat(),en.isoformat())).fetchall(); ps=c.execute('SELECT name,SUM(qty)qty,SUM(total)total FROM sales WHERE created>=? AND created<? GROUP BY name ORDER BY total DESC',(st.isoformat(),en.isoformat())).fetchall(); tot=c.execute('SELECT COALESCE(SUM(grand_total),0)g FROM receipts WHERE created>=? AND created<?',(st.isoformat(),en.isoformat())).fetchone()['g']; c.close(); b=io.BytesIO(); d=SimpleDocTemplate(b,pagesize=A4); sty=getSampleStyleSheet(); story=[Paragraph(setting('club_name'),sty['Title']),Paragraph(f'Kunlik hisobot — {day}',sty['Heading2']),Paragraph(f'Jami savdo: <b>{money(tot)}</b>',sty['Normal']),Spacer(1,10)]; data=[['Mahsulot','Miqdor','Jami']]+[[x['name'],str(x['qty']),money(x['total'])] for x in ps]; t=Table(data); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])); story += [Paragraph('Mahsulotlar',sty['Heading2']),t,Spacer(1,10)]; cdata=[['Chek','Stol','Vaqt','Jami']]+[[f'#{x["id"]}',f'{x["kind"]} {x["num"]}',fmt(x['seconds']),money(x['grand_total'])] for x in rs]; ct=Table(cdata); ct.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.lightgrey)])); story += [Paragraph('Barcha cheklar',sty['Heading2']),ct]; d.build(story); b.seek(0); return b
@app.get('/receipt/<int:rid>/pdf')
def receipt_pdf(rid):
    c=conn(); r=c.execute('SELECT * FROM receipts WHERE id=?',(rid,)).fetchone(); its=c.execute('SELECT * FROM receipt_items WHERE receipt_id=?',(rid,)).fetchall(); c.close(); b=io.BytesIO(); d=SimpleDocTemplate(b,pagesize=A4); s=getSampleStyleSheet(); story=[Paragraph(setting('club_name'),s['Title']),Paragraph(f'Chek #{rid}',s['Heading2'])]; data=[['Mahsulot','Miqdor','Narx','Jami']]+[[x['name'],str(x['qty']),money(x['unit_price']),money(x['total'])] for x in its]; t=Table(data); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey)])); story += [t,Paragraph(f'Stol: {money(r["table_total"])}',s['Normal']),Paragraph(f'Mahsulot: {money(r["product_total"])}',s['Normal']),Paragraph(f'<b>JAMI: {money(r["grand_total"])}</b>',s['Heading2'])]; d.build(story); b.seek(0); return send_file(b,as_attachment=True,download_name=f'chek_{rid}.pdf',mimetype='application/pdf')
@app.get('/history')
def history():
    c=conn(); rs=c.execute('SELECT * FROM receipts ORDER BY id DESC LIMIT 500').fetchall(); c.close(); rows=''.join(f'<tr><td>#{x["id"]}</td><td>{x["kind"]} {x["num"]}</td><td>{x["created"]}</td><td>{fmt(x["seconds"])}</td><td>{money(x["grand_total"])}</td><td><a class="btn" href="/receipt/{x["id"]}">Ko‘rish</a></td></tr>' for x in rs); return page(f'<div class="panel"><h2>🧾 Barcha cheklar</h2><table><tr><th>#</th><th>Stol</th><th>Sana</th><th>Vaqt</th><th>Jami</th><th></th></tr>{rows}</table></div>')
@app.get('/reports')
def reports():
    b=daily_pdf(now().date()); return send_file(b,as_attachment=False,download_name='kunlik_hisobot.pdf',mimetype='application/pdf')

@app.route('/settings',methods=['GET','POST'])
def settings():
    if request.method=='POST':
        if not admin_ok(): return redirect('/settings')
        for k in ['club_name','login_password','admin_password','report_email','smtp_host','smtp_port','smtp_user','smtp_password','report_time','background_url']: set_setting(k,request.form.get(k,''))
        c=conn()
        for k,v in request.form.items():
            if k.startswith('tp_'):
                try:c.execute('UPDATE tables SET price=? WHERE id=?',(float(v),int(k[3:])))
                except:pass
            if k.startswith('pp_'):
                try:c.execute('UPDATE products SET price=? WHERE id=?',(float(v),int(k[3:])))
                except:pass
        c.commit(); c.close(); return redirect('/settings')
    c=conn(); tables=c.execute('SELECT * FROM tables ORDER BY kind,num').fetchall(); ps=c.execute('SELECT * FROM products WHERE active=1').fetchall(); c.close(); tr=''.join(f'<tr><td>{x["kind"]} {x["num"]}</td><td><input name="tp_{x["id"]}" value="{x["price"]}"></td></tr>' for x in tables); pr=''.join(f'<tr><td>{x["name"]}</td><td><input name="pp_{x["id"]}" value="{x["price"]}"></td></tr>' for x in ps); body=f'''<div class="two"><div class="panel"><h2>⚙ Sozlamalar</h2><form method=post><label>Klub nomi</label><input name=club_name value="{setting('club_name')}"><label>Kirish paroli</label><input name=login_password type=password placeholder="O'zingiz o'rnating"><label>Admin paroli</label><input name=admin_password type=password placeholder="O'zingiz o'rnating"><label>Email</label><input name=report_email value="{setting('report_email')}"><label>SMTP user</label><input name=smtp_user value="{setting('smtp_user')}"><label>SMTP password/App Password</label><input name=smtp_password type=password><label>Hisobot vaqti (HH:MM)</label><input name=report_time value="{setting('report_time')}"><label>Oboy rasmi URL</label><input name=background_url value="{setting('background_url')}"><button class="btn gold">💾 Saqlash</button></form></div><div class="panel"><h3>💰 Stol va mahsulot narxlari</h3><form method=post><table><tr><th>Stol</th><th>Narx</th></tr>{tr}</table><table><tr><th>Mahsulot</th><th>Narx</th></tr>{pr}</table><button class="btn gold">Narxlarni saqlash</button></form></div></div><div class="panel" style="margin-top:18px"><b>Eslatma:</b> email avtomatik yuborish uchun SMTP ma'lumotlarini kiriting. Hisobotda kunlik savdo, barcha cheklar va olingan mahsulotlar bo'ladi.</div>'''; return page(body)

def email_pdf():
    target=(now().date()-timedelta(days=1)); email=setting('report_email'); user=setting('smtp_user'); pw=setting('smtp_password')
    if not email or not user or not pw:return
    b=daily_pdf(target); m=EmailMessage(); m['Subject']=f'{setting("club_name")} — {target} hisoboti'; m['From']=user; m['To']=email; m.set_content(f'{target} kunlik hisobot.'); m.add_attachment(b.getvalue(),maintype='application',subtype='pdf',filename=f'hisobot_{target}.pdf')
    with smtplib.SMTP(setting('smtp_host') or 'smtp.gmail.com',int(setting('smtp_port') or 587),timeout=30) as s: s.starttls(context=ssl.create_default_context()); s.login(user,pw); s.send_message(m)

def scheduler():
    while True:
        try:
            rt=setting('report_time') or '23:59'; hh,mm=[int(x) for x in rt.split(':')]; n=now()
            if n.hour==hh and n.minute==mm and setting('last_report') != str(n.date()):
                try: email_pdf()
                except Exception: pass
                set_setting('last_report',str(n.date()))
        except Exception: pass
        time.sleep(20)
threading.Thread(target=scheduler,daemon=True).start()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
