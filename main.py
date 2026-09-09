import os, sqlite3, time, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, flash, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'billiard_club.db')
UPLOAD_DIR = os.path.join(BASE, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tables (
 id INTEGER PRIMARY KEY, typ TEXT NOT NULL, no INTEGER NOT NULL,
 price REAL NOT NULL DEFAULT 30000, active INTEGER NOT NULL DEFAULT 0,
 started REAL
);
CREATE TABLE IF NOT EXISTS sales (
 id INTEGER PRIMARY KEY AUTOINCREMENT, typ TEXT, tab_no INTEGER,
 name TEXT, price REAL, qty INTEGER, created REAL
);
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, typ TEXT, tab_no INTEGER,
 started REAL, ended REAL, seconds INTEGER, total REAL
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, cat TEXT,
 size TEXT DEFAULT '', price REAL, active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
'''

def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    defaults = {'club':'BILYARD CLUB','login':'','admin':'','bg':''}
    for k, v in defaults.items():
        c.execute('INSERT OR IGNORE INTO settings(k,v) VALUES(?,?)', (k, v))
    for i in range(1, 6):
        c.execute('INSERT OR IGNORE INTO tables(id,typ,no,price) VALUES(?,?,?,?)', (i,'BILLIARD',i,30000))
    for i in range(1, 4):
        c.execute('INSERT OR IGNORE INTO tables(id,typ,no,price) VALUES(?,?,?,?)', (100+i,'TENNIS',i,20000))
    products = [
      ('Suv','Ichimlik','0.5L',3000),('Suv','Ichimlik','1L',5000),('Suv','Ichimlik','1.5L',7000),('Suv','Ichimlik','2L',9000),
      ('Coca-Cola','Ichimlik','0.5L',7000),('Coca-Cola','Ichimlik','1L',11000),('Coca-Cola','Ichimlik','1.5L',15000),('Coca-Cola','Ichimlik','2L',19000),
      ('Fanta','Ichimlik','0.5L',7000),('Fanta','Ichimlik','1L',11000),('Fanta','Ichimlik','1.5L',15000),('Fanta','Ichimlik','2L',19000),
      ('Sprite','Ichimlik','0.5L',7000),('Sprite','Ichimlik','1L',11000),('Sprite','Ichimlik','1.5L',15000),('Sprite','Ichimlik','2L',19000),
      ('Pepsi','Ichimlik','0.5L',7000),('Pepsi','Ichimlik','1L',11000),('Pepsi','Ichimlik','1.5L',15000),('Pepsi','Ichimlik','2L',19000),
      ('Chips','Gazak','',10000),('Suxarik','Gazak','',8000),('Shokolad','Gazak','',10000),("Yong'oq",'Gazak','',15000),('Pullik tayoqcha','Tayoqcha','',5000)
    ]
    if c.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
        c.executemany('INSERT INTO products(name,cat,size,price) VALUES(?,?,?,?)', products)
    c.commit()
    return c

def setting(key):
    c = get_db(); r = c.execute('SELECT v FROM settings WHERE k=?', (key,)).fetchone(); c.close()
    return r['v'] if r else ''

def money(x): return f"{x:,.0f}".replace(',', ' ') + " so'm"

def login_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if setting('login') and not session.get('logged_in'):
            return redirect(url_for('login', next=request.path))
        return f(*a, **kw)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not session.get('admin_ok'):
            return redirect(url_for('admin_login', next=request.path))
        return f(*a, **kw)
    return wrapped

CSS = '''
:root{--bg:#071017;--card:#142531;--gold:#e5b83b;--blue:#1c7fb5;--green:#1c9b57;--red:#a83232;--white:#f7f7f7}
*{box-sizing:border-box} body{margin:0;font-family:Segoe UI,Arial,sans-serif;color:var(--white);background:#071017 url('/background') center/cover fixed no-repeat}
body:before{content:'';position:fixed;inset:0;background:rgba(4,10,15,.84);z-index:-1} header{position:sticky;top:0;z-index:5;background:#03070aee;padding:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;box-shadow:0 2px 15px #0008}.brand{font-size:22px;font-weight:900;color:var(--gold);margin-right:auto}.wrap{max-width:1450px;margin:auto;padding:22px} a,button{border:0;border-radius:10px;padding:11px 15px;font-weight:800;text-decoration:none;color:white;background:#173044;cursor:pointer}a:hover,button:hover{filter:brightness(1.12)} h1,h2{color:var(--gold)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:14px}.section{background:#071017c9;border:1px solid #294452;border-radius:18px;padding:18px;margin-bottom:18px}.card{background:#142531ed;border-radius:16px;padding:16px;border:1px solid #294551}.card.busy{border-color:#7b3333;background:#3d1e24}.big{font-size:31px;font-weight:900;font-variant-numeric:tabular-nums}.gold{color:var(--gold)}.muted{opacity:.82}.btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.green{background:var(--green)}.red{background:var(--red)}.blue{background:var(--blue)}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.stat{background:#142531e8;padding:17px;border-radius:14px}.stat b{font-size:22px;color:var(--gold)}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #28404b;text-align:left}input,select{background:#0b171f;color:white;border:1px solid #355461;border-radius:8px;padding:9px}.msg{background:#174d35;padding:10px;border-radius:10px;margin-bottom:12px}.err{background:#5c2222;padding:10px;border-radius:10px;margin-bottom:12px}.login{max-width:430px;margin:10vh auto}.small{font-size:13px}.timer{font-family:Consolas,monospace}
'''

BASE_TMPL = '''<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title><style>{{css}}</style></head><body>
<header><div class="brand">🎱 {{club}}</div><a href="/">🏠 Bosh sahifa</a><a href="/menu">🥤 Menyu</a><a href="/reports">📊 Hisobot</a><a href="/settings">⚙ Sozlamalar</a>{% if logged %}<a href="/logout">🚪 Chiqish</a>{% endif %}</header><div class="wrap">{% with msgs=get_flashed_messages() %}{% for m in msgs %}<div class="msg">{{ m[1] if m is sequence and m|length > 1 else m }}</div>{% endfor %}{% endwith %}{{body|safe}}</div></body></html>'''

def page(title, body):
    # Flask flash messages must be plain strings. Defensive conversion also
    # prevents 500 errors if legacy tuple/list values exist in the session.
    return render_template_string(BASE_TMPL, title=title, body=body, css=CSS, club=setting('club') or 'BILYARD CLUB', logged=bool(session.get('logged_in') or session.get('admin_ok')))

def timer_js():
    return """<script>
(function(){
  function pad(n){return String(n).padStart(2,'0');}
  function tick(){
    const now=Date.now()/1000;
    document.querySelectorAll('[data-start]').forEach(function(e){
      const start=Number(e.dataset.start);
      if(!Number.isFinite(start)) return;
      const sec=Math.max(0,Math.floor(now-start));
      if(e.classList.contains('timer')){
        const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),x=sec%60;
        e.textContent=pad(h)+':'+pad(m)+':'+pad(x);
      }
      const target=e.querySelector('[data-timer-total]');
      if(target && e.dataset.price){
        const amount=Math.floor(sec*Number(e.dataset.price)/3600);
        target.textContent=new Intl.NumberFormat('uz-UZ').format(amount).replaceAll(',',' ')+' so\'m';
      }
    });
    setTimeout(tick,200);
  }
  tick();
})();
</script>"""

@app.route('/background')
def background():
    bg = setting('bg')
    if bg and os.path.exists(os.path.join(UPLOAD_DIR, bg)):
        return send_from_directory(UPLOAD_DIR, bg)
    return ('', 204)

@app.route('/setup', methods=['GET','POST'])
def setup():
    if setting('admin'):
        return redirect('/login')
    if request.method=='POST':
        admin=request.form.get('admin','').strip()
        login_pw=request.form.get('login','').strip()
        club=request.form.get('club','BILYARD CLUB').strip() or 'BILYARD CLUB'
        if len(admin)<4:
            flash('Admin paroli kamida 4 ta belgidan iborat bo‘lsin.')
        else:
            c=get_db()
            c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('admin',admin))
            c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('login',login_pw))
            c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('club',club))
            c.commit(); c.close()
            session['admin_ok']=True
            flash('Birinchi sozlama saqlandi.')
            return redirect('/settings')
    body='''<div class="login section"><h1>⚙ Birinchi sozlash</h1><p class="muted">Avval admin parolini o‘zingiz yarating.</p><form method="post"><p>Klub nomi<br><input name="club" value="BILYARD CLUB" required></p><p>Kirish paroli <span class="small">(ixtiyoriy)</span><br><input type="password" name="login" placeholder="Kirish paroli"></p><p>Admin paroli<br><input type="password" name="admin" placeholder="O‘zingiz tanlang" required></p><button class="blue">Saqlash va davom etish</button></form></div>'''
    return page('Birinchi sozlash',body)

@app.route('/login', methods=['GET','POST'])
def login():
    if not setting('admin'):
        return redirect(url_for('setup'))
    nxt=request.args.get('next','/')
    if request.method=='POST':
        if request.form.get('password','') == setting('login'):
            session['logged_in']=True; return redirect(request.form.get('next') or '/')
        flash('Kirish paroli noto‘g‘ri.')
    body=f'''<div class="login section"><h1>🔐 Kirish</h1><form method="post"><input type="hidden" name="next" value="{nxt}"><p><input type="password" name="password" placeholder="Kirish paroli" required></p><button class="blue">Kirish</button></form></div>'''
    return page('Kirish',body)

@app.route('/admin-login', methods=['GET','POST'])
def admin_login():
    nxt=request.args.get('next','/settings')
    if request.method=='POST':
        if setting('admin') and request.form.get('password','') == setting('admin'):
            session['admin_ok']=True; return redirect(request.form.get('next') or '/settings')
        flash('Admin paroli noto‘g‘ri.')
    body=f'''<div class="login section"><h1>🛡 Admin kirish</h1><form method="post"><input type="hidden" name="next" value="{nxt}"><p><input type="password" name="password" placeholder="Admin paroli" required></p><button class="blue">Kirish</button></form></div>'''
    return page('Admin',body)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/')
@login_required
def home():
    c=get_db(); rows=c.execute('SELECT * FROM tables ORDER BY typ,no').fetchall(); c.close()
    groups={'BILLIARD':[],'TENNIS':[]}
    for r in rows: groups[r['typ']].append(r)
    def card(r):
        start = r['started'] if r['active'] and r['started'] else ''
        elapsed=max(0,int(time.time()-start)) if start else 0
        total=elapsed*r['price']/3600
        timer=f'<div class="big timer" data-start="{start}">{timefmt(elapsed)}</div>' if start else '<div class="big timer">00:00:00</div>'
        val=f'<span data-price="{r["price"]}" data-start="{start}"><span data-timer-total>{money(total)}</span></span>' if start else money(0)
        return f'''<div class="card {'busy' if r['active'] else ''}"><div class="gold"><b>{r['typ']} {r['no']}</b></div><div>{'🔴 BAND' if r['active'] else '🟢 BO‘SH'}</div>{timer}<div class="muted">Joriy hisob: <b class="gold">{val}</b><br>{money(r['price'])}/soat</div><div class="btnrow"><a class="blue" href="/table/{r['id']}">Kirish</a><a class="{'red' if r['active'] else 'green'}" href="/toggle/{r['id']}">{'⏹ Tugatish' if r['active'] else '▶ Band qilish'}</a></div></div>'''
    body=f'<h1>{setting("club") or "BILYARD CLUB"}</h1><div class="section"><h2>🎱 5 TA BILLIARD</h2><div class="grid">{"".join(card(r) for r in groups["BILLIARD"])}</div></div><div class="section"><h2>🏓 3 TA TENNIS</h2><div class="grid">{"".join(card(r) for r in groups["TENNIS"])}</div></div>{timer_js()}'
    return page('Bilyard Club',body)

def timefmt(s): return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

@app.route('/toggle/<int:tid>')
@login_required
def toggle(tid):
    c=get_db(); r=c.execute('SELECT * FROM tables WHERE id=?',(tid,)).fetchone()
    if not r: c.close(); return 'Not found',404
    if r['active']:
        started=float(r['started']); ended=time.time(); secs=max(0,int(ended-started)); total=secs*float(r['price'])/3600
        sales=c.execute('SELECT name,price,qty,created FROM sales WHERE typ=? AND tab_no=? AND created>=? AND created<=? ORDER BY id',(r['typ'],r['no'],started,ended)).fetchall()
        sales_total=sum(float(x['price'])*int(x['qty']) for x in sales)
        c.execute('INSERT INTO sessions(typ,tab_no,started,ended,seconds,total) VALUES(?,?,?,?,?,?)',(r['typ'],r['no'],started,ended,secs,total))
        c.execute('UPDATE tables SET active=0,started=NULL WHERE id=?',(tid,)); c.commit(); c.close()
        items=''.join(f'<tr><td>{x["name"]}</td><td>{x["qty"]} ta</td><td>{money(float(x["price"])*int(x["qty"]))}</td></tr>' for x in sales)
        body=(f'<div class="section"><h1>🧾 CHEK</h1><h2>{r["typ"]} {r["no"]}</h2>'
              f'<p>Boshlangan: {datetime.fromtimestamp(started).strftime("%Y-%m-%d %H:%M:%S")}</p>'
              f'<p>Tugagan: {datetime.fromtimestamp(ended).strftime("%Y-%m-%d %H:%M:%S")}</p>'
              f'<p>O‘ynalgan vaqt: <b class="gold">{timefmt(secs)}</b></p>'
              f'<table><tr><th>Xizmat</th><th>Miqdor</th><th>Summa</th></tr>'
              f'<tr><td>{r["typ"]} stol</td><td>{timefmt(secs)}</td><td>{money(total)}</td></tr>{items}'
              f'</table><h2>JAMI: {money(total+sales_total)}</h2>'
              f'<div class="btnrow"><button onclick="window.print()" class="blue">🖨 Chekni chiqarish</button><a href="/">🏠 Bosh sahifa</a></div></div>')
        return page('Chek',body)
    c.execute('UPDATE tables SET active=1,started=? WHERE id=?',(time.time(),tid)); c.commit(); c.close(); return redirect(url_for('home'))

@app.route('/table/<int:tid>')
@login_required
def table_view(tid):
    c=get_db(); r=c.execute('SELECT * FROM tables WHERE id=?',(tid,)).fetchone(); c.close()
    if not r:return 'Not found',404
    start=r['started'] if r['active'] else ''
    elapsed=max(0,int(time.time()-start)) if start else 0
    timer=f'<div class="big timer" data-start="{start}">{timefmt(elapsed)}</div>' if start else '<div class="big">00:00:00</div>'
    body=f'<div class="section"><h1>{r["typ"]} {r["no"]}</h1><p>{"🔴 BAND" if r["active"] else "🟢 BO‘SH"}</p>{timer}<p>Stol narxi: <b class="gold">{money(r["price"])}/soat</b></p><div class="btnrow"><a class="{"red" if r["active"] else "green"}" href="/toggle/{r["id"]}">{"⏹ Tugatish" if r["active"] else "▶ Band qilish"}</a><a class="blue" href="/menu?tid={r["id"]}">🥤 Mahsulot qo‘shish</a><a href="/">← Orqaga</a></div></div>{timer_js()}'
    return page(f'{r["typ"]} {r["no"]}',body)

@app.route('/menu')
@login_required
def menu():
    tid=request.args.get('tid',''); c=get_db(); ps=c.execute('SELECT * FROM products WHERE active=1 ORDER BY cat,name,size').fetchall(); c.close()
    cards=[]
    for p in ps:
        action = f'<a class="blue" href="/sale?tid={tid}&pid={p["id"]}">➕ Olish</a>' if tid else ''
        cards.append(f'<div class="card"><b class="gold">{p["name"]} {p["size"] or ""}</b><div class="muted">{p["cat"]}</div><h3>{money(p["price"])}</h3>{action}</div>')
    return page('Menyu',f'<h1>🥤 MENYU</h1><div class="grid">{"".join(cards)}</div>')

@app.route('/sale')
@login_required
def sale():
    tid=int(request.args.get('tid','0')); pid=int(request.args.get('pid','0')); c=get_db(); t=c.execute('SELECT * FROM tables WHERE id=?',(tid,)).fetchone(); p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if t and p:
        c.execute('INSERT INTO sales(typ,tab_no,name,price,qty,created) VALUES(?,?,?,?,?,?)',(t['typ'],t['no'],p['name'],p['price'],1,time.time())); c.commit(); flash(f'{p["name"]} qo‘shildi.')
    c.close(); return redirect(url_for('table_view',tid=tid))

@app.route('/reports')
@login_required
def reports():
    n=datetime.now(); day=n.replace(hour=0,minute=0,second=0,microsecond=0).timestamp(); week=(n-timedelta(days=n.weekday())).replace(hour=0,minute=0,second=0,microsecond=0).timestamp(); month=n.replace(day=1,hour=0,minute=0,second=0,microsecond=0).timestamp()
    c=get_db()
    def calc(s):
        a=c.execute('SELECT COALESCE(SUM(total),0)x,COUNT(*)n FROM sessions WHERE ended>=?',(s,)).fetchone(); b=c.execute('SELECT COALESCE(SUM(price*qty),0)x,COUNT(*)n FROM sales WHERE created>=?',(s,)).fetchone(); return a['x']+b['x'],a['n'],b['n']
    d,w,m=calc(day),calc(week),calc(month); c.close()
    body='<h1>📊 HISOBOT</h1><div class="stats">'+''.join(f'<div class="stat"><div>{name}</div><b>{money(v[0])}</b><div class="muted">{v[1]} ta o‘yin • {v[2]} ta savdo</div></div>' for name,v in [('BUGUN',d),('HAFTA',w),('OY',m)])+'</div>'
    return page('Hisobot',body)

@app.post('/add-product')
@login_required
@admin_required
def add_product():
    name=request.form.get('name','').strip(); cat=request.form.get('cat','Boshqa').strip() or 'Boshqa'; size=request.form.get('size','').strip()
    try: price=float(request.form.get('price','0'))
    except ValueError: price=-1
    if not name or price<0: flash('Mahsulot nomi va narxini to‘g‘ri kiriting.'); return redirect('/settings')
    c=get_db(); c.execute('INSERT INTO products(name,cat,size,price,active) VALUES(?,?,?,?,1)',(name,cat,size,price)); c.commit(); c.close(); flash('Mahsulot qo‘shildi.'); return redirect('/settings')

@app.post('/edit-product')
@login_required
@admin_required
def edit_product():
    try: pid=int(request.form.get('id','0')); price=float(request.form.get('price','0'))
    except ValueError: flash('Mahsulot ID yoki narxi noto‘g‘ri.'); return redirect('/settings')
    name=request.form.get('name','').strip(); cat=request.form.get('cat','Boshqa').strip() or 'Boshqa'; size=request.form.get('size','').strip()
    c=get_db(); c.execute('UPDATE products SET name=?,cat=?,size=?,price=? WHERE id=?',(name,cat,size,price,pid)); c.commit(); c.close(); flash('Mahsulot saqlandi.'); return redirect('/settings')

@app.post('/delete-product')
@login_required
@admin_required
def delete_product():
    try: pid=int(request.form.get('id','0'))
    except ValueError: pid=0
    c=get_db(); c.execute('UPDATE products SET active=0 WHERE id=?',(pid,)); c.commit(); c.close(); flash('Mahsulot olib tashlandi.'); return redirect('/settings')

@app.route('/settings', methods=['GET'])
@login_required
def settings_page():
    if not setting('admin'):
        return redirect('/setup')
    if not session.get('admin_ok'):
        return redirect(url_for('admin_login', next=request.path))
    c=get_db(); trs=c.execute('SELECT * FROM tables ORDER BY typ,no').fetchall(); ps=c.execute('SELECT * FROM products WHERE active=1 ORDER BY id').fetchall(); c.close()
    rows=''.join(f'<tr><td>{r["typ"]} {r["no"]}</td><td><form method="post" action="/save-price"><input type="hidden" name="id" value="{r["id"]}"><input name="price" value="{r["price"]}" size="10"><button class="blue">Saqlash</button></form></td></tr>' for r in trs)
    prows=''.join(f'<tr><td>{p["name"]} {p["size"] or ""}</td><td>{money(p["price"])}</td></tr>' for p in ps)
    bg=setting('bg')
    body=f'''<h1>⚙ SOZLAMALAR</h1><div class="section"><h2>Stol narxlari</h2><table><tr><th>Stol</th><th>Narx / soat</th></tr>{rows}</table></div>
    <div class="section"><h2>Klub nomi</h2><form method="post" action="/save-club"><input name="club" value="{setting('club')}" size="30"><button class="blue">Saqlash</button></form></div>
    <div class="section"><h2>🔐 Parollar</h2><form method="post" action="/save-password"><p>Kirish paroli<br><input type="password" name="login" placeholder="Yangi parol"></p><p>Admin paroli<br><input type="password" name="admin" placeholder="Yangi admin parol"></p><button class="blue">Parollarni saqlash</button></form><p class="small">Parol maydonini bo‘sh qoldirsangiz, o‘sha parol o‘zgarmaydi.</p></div>
    <div class="section"><h2>🖼 Oboy rasmi</h2><form method="post" action="/upload-bg" enctype="multipart/form-data"><input type="file" name="bg" accept="image/png,image/jpeg,image/webp" required><button class="blue">Oboyni saqlash</button></form>{'<p>Joriy oboy: '+bg+'</p>' if bg else '<p class="muted">Hozir oboy o‘rnatilmagan.</p>'}</div>
    <div class="section"><h2>➕ Mahsulot qo‘shish</h2><form method="post" action="/add-product"><input name="name" placeholder="Mahsulot nomi" required> <input name="cat" placeholder="Kategoriya" value="Ichimlik"> <input name="size" placeholder="Hajmi"> <input type="number" min="0" step="100" name="price" placeholder="Narxi" required> <button class="green">Qo‘shish</button></form></div>
    <div class="section"><h2>✏️ Mahsulot narxi / 🗑 O‘chirish</h2><table><tr><th>Nomi</th><th>Kategoriya</th><th>Narxi</th><th>Amal</th></tr>{''.join(f'<tr><form method="post" action="/edit-product"><td><input name="name" value="{p["name"]}"></td><td><input name="cat" value="{p["cat"]}"></td><td><input type="number" min="0" step="100" name="price" value="{p["price"]}"></td><td><input type="hidden" name="id" value="{p["id"]}"><input type="hidden" name="size" value="{p["size"]}"><button class="blue">Saqlash</button></form> <form method="post" action="/delete-product" style="display:inline"><input type="hidden" name="id" value="{p["id"]}"><button class="red">O‘chirish</button></form></td></tr>' for p in ps)}</table></div>'''
    return page('Sozlamalar',body)

@app.post('/save-price')
@login_required
@admin_required
def save_price():
    try:
        c=get_db(); c.execute('UPDATE tables SET price=? WHERE id=?',(float(request.form['price']),int(request.form['id']))); c.commit(); c.close(); flash('Stol narxi saqlandi.')
    except Exception: flash('Narx noto‘g‘ri.')
    return redirect('/settings')

@app.post('/save-club')
@login_required
@admin_required
def save_club():
    c=get_db(); c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('club',request.form.get('club','BILYARD CLUB'))); c.commit(); c.close(); flash('Klub nomi saqlandi.'); return redirect('/settings')

@app.post('/save-password')
@login_required
@admin_required
def save_password():
    c=get_db()
    for k in ('login','admin'):
        v=request.form.get(k,'')
        if v: c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',(k,v))
    c.commit(); c.close(); flash('Parollar saqlandi.'); return redirect('/settings')

@app.post('/upload-bg')
@login_required
@admin_required
def upload_bg():
    f=request.files.get('bg')
    if not f or not f.filename: flash('Rasm tanlanmadi.'); return redirect('/settings')
    ext=os.path.splitext(f.filename)[1].lower()
    if ext not in {'.png','.jpg','.jpeg','.webp'}: flash('Faqat PNG/JPG/WEBP rasm tanlang.'); return redirect('/settings')
    name='club_background'+ext; f.save(os.path.join(UPLOAD_DIR,name)); c=get_db(); c.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('bg',name)); c.commit(); c.close(); flash('Oboy rasmi saqlandi.'); return redirect('/settings')

with app.app_context(): get_db().close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8000)), debug=False)
