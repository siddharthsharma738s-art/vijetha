import os, re, json, uuid, hmac, html, secrets, datetime, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlparse
from flask import g, session, request, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from schema import RES, DEFAULT_SETTINGS, DEFAULT_ROLES, MODS

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('VIJETHA_DATA', os.path.join(BASE, 'instance'))
UP = os.path.join(DATA, 'uploads')
URL = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(DATA, 'vijetha.db'))
KIND = 'sqlite' if URL.startswith('sqlite') else 'pg' if URL.startswith('postgres') else 'mysql'
os.makedirs(UP, exist_ok=True)

# ---------------- database (portable: SQLite / PostgreSQL / MySQL) ----------------
def conn():
    if 'db' not in g:
        if KIND == 'sqlite':
            import sqlite3
            c = sqlite3.connect(URL.replace('sqlite:///', '', 1), timeout=15); c.row_factory = sqlite3.Row
            c.execute('PRAGMA journal_mode=WAL')
        elif KIND == 'pg':
            import psycopg2; c = psycopg2.connect(URL)
        else:
            import pymysql; u = urlparse(URL)
            c = pymysql.connect(host=u.hostname, port=u.port or 3306, user=u.username, password=u.password, database=u.path[1:], charset='utf8mb4')
        g.db = c
    return g.db

def q(sql, *a, w=False):
    c = conn()
    if KIND == 'pg':
        import psycopg2.extras; k = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    elif KIND == 'mysql':
        import pymysql.cursors; k = c.cursor(pymysql.cursors.DictCursor)
    else:
        k = c.cursor()
    k.execute(sql if KIND == 'sqlite' else sql.replace('?', '%s'), a)
    if w:
        c.commit(); return None
    return [dict(r) for r in k.fetchall()]

def init_db():
    T = 'LONGTEXT' if KIND == 'mysql' else 'TEXT'
    for s in [
        f'CREATE TABLE IF NOT EXISTS records(id VARCHAR(32) PRIMARY KEY, res VARCHAR(40), data {T}, created VARCHAR(25), updated VARCHAR(25))',
        f'CREATE TABLE IF NOT EXISTS kv(k VARCHAR(100) PRIMARY KEY, v {T})',
        f'CREATE TABLE IF NOT EXISTS versions(id VARCHAR(32) PRIMARY KEY, res VARCHAR(40), rid VARCHAR(32), data {T}, ts VARCHAR(25), author VARCHAR(80))',
        'CREATE TABLE IF NOT EXISTS logs(id VARCHAR(32) PRIMARY KEY, ts VARCHAR(25), uid VARCHAR(32), who VARCHAR(80), kind VARCHAR(10), action VARCHAR(300))',
        'CREATE TABLE IF NOT EXISTS logins(id VARCHAR(32) PRIMARY KEY, ts VARCHAR(25), usr VARCHAR(80), ip VARCHAR(60), ok INTEGER, ua VARCHAR(200))']:
        q(s, w=True)
    for s in ['CREATE INDEX idx_rec_res ON records(res)', 'CREATE INDEX idx_ver ON versions(res, rid)', 'CREATE INDEX idx_login ON logins(usr, ts)']:
        try: q(s, w=True)
        except Exception: conn().rollback()

def now(): return datetime.datetime.utcnow().isoformat(timespec='seconds')
def uid(): return uuid.uuid4().hex[:12]

def unpack(r):
    d = json.loads(r['data']); d['id'] = r['id']; d['_c'] = r['created']; d['_u'] = r['updated']; return d
def store(res): return RES.get(res, {}).get('store', res)
def _match(d, w):
    if not w: return True
    k, v = next(iter(w.items()))
    return (d.get(k) != v[1:]) if v.startswith('!') else d.get(k) == v
def rows(res):
    return [d for d in (unpack(r) for r in q('SELECT * FROM records WHERE res=? ORDER BY created DESC', store(res))) if _match(d, RES.get(res, {}).get('where'))]
def rget(res, i):
    r = q('SELECT * FROM records WHERE res=? AND id=?', store(res), i)
    if not r: return None
    d = unpack(r[0])
    return d if _match(d, RES.get(res, {}).get('where')) else None
def rput(res, d, i=None):
    d = {k: v for k, v in d.items() if k not in ('id', '_c', '_u') and not k.startswith('__')}
    t = now()
    if i: q('UPDATE records SET data=?,updated=? WHERE res=? AND id=?', json.dumps(d), t, store(res), i, w=True)
    else:
        i = uid(); q('INSERT INTO records(id,res,data,created,updated) VALUES(?,?,?,?,?)', i, store(res), json.dumps(d), t, t, w=True)
    return i
def rdel(res, i): q('DELETE FROM records WHERE res=? AND id=?', store(res), i, w=True)

def kv(k, default=None):
    r = q('SELECT v FROM kv WHERE k=?', k)
    return json.loads(r[0]['v']) if r else default
def kv_set(k, v):
    s = json.dumps(v)
    if q('SELECT k FROM kv WHERE k=?', k): q('UPDATE kv SET v=? WHERE k=?', s, k, w=True)
    else: q('INSERT INTO kv(k,v) VALUES(?,?)', k, s, w=True)

def S():
    if 's' not in g: g.s = {**DEFAULT_SETTINGS, **kv('settings', {})}
    return g.s
def lnow(): return (datetime.datetime.utcnow() + datetime.timedelta(minutes=int(S().get('tz') or 0))).strftime('%Y-%m-%dT%H:%M')

# ---------------- sanitising ----------------
VOID = {'br', 'hr', 'img'}
SKIP = {'script', 'style', 'iframe', 'object', 'embed', 'svg', 'math', 'form', 'textarea', 'title'}
OKTAG = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre', 'table',
         'thead', 'tbody', 'tr', 'td', 'th', 'hr', 'span', 'div', 'figure', 'figcaption'}
OKATTR = {'a': {'href', 'title'}, 'img': {'src', 'alt'}, 'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan'}}

def safe_url(v, src=False):
    v = re.sub(r'[\x00-\x20]+', '', v or '').lower()
    if src: return v.startswith(('https://', 'http://', '/media/'))
    return v.startswith(('https://', 'http://', 'mailto:', '/', '#')) and not v.startswith('//')

class _San(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=True); s.o = []; s.skip = 0; s.st = []
    def handle_starttag(s, t, at):
        if t in SKIP: s.skip += 1; return
        if s.skip or t not in OKTAG: return
        out = ''
        for k, v in at:
            if k in OKATTR.get(t, ()) and v is not None and (k not in ('href', 'src') or safe_url(v, k == 'src')):
                out += f' {k}="{html.escape(v, True)}"'
        if t == 'a': out += ' rel="noopener nofollow"'
        s.o.append(f'<{t}{out}>')
        if t not in VOID: s.st.append(t)
    def handle_endtag(s, t):
        if t in SKIP: s.skip = max(0, s.skip - 1); return
        if s.skip or t in VOID or t not in s.st: return
        while s.st:
            x = s.st.pop(); s.o.append(f'</{x}>')
            if x == t: break
    def handle_data(s, d):
        if not s.skip: s.o.append(html.escape(d, False))
def clean_html(v):
    p = _San(); p.feed(str(v or '')); p.close()
    return ''.join(p.o) + ''.join(f'</{x}>' for x in reversed(p.st))

def svg_ok(data: bytes):
    if re.search(rb'<!(ENTITY|DOCTYPE)', data, re.I): return False
    try: root = ET.fromstring(data)
    except ET.ParseError: return False
    if not root.tag.lower().endswith('svg'): return False
    for el in root.iter():
        if el.tag.split('}')[-1].lower() in ('script', 'foreignobject', 'iframe', 'embed', 'object', 'animate', 'set', 'handler'): return False
        for k, v in el.attrib.items():
            kk = k.split('}')[-1].lower(); vv = re.sub(r'\s+', '', v).lower()
            if kk.startswith('on') or 'javascript:' in vv or 'data:text' in vv: return False
            if kk == 'href' and not (vv.startswith('#') or re.match(r'data:image/(png|jpeg|gif|webp);', vv)): return False
    return True

# ---------------- auth / permissions ----------------
def csrf():
    if 'csrf' not in session: session['csrf'] = secrets.token_urlsafe(24)
    return session['csrf']
def me():
    if 'u' in g: return g.u
    g.u = None; i = session.get('uid')
    if i:
        u = rget('students', i) or rget('admins', i)
        idle = int(S().get('session_min') or 60) * 60
        if u and u.get('status') == 'active' and datetime.datetime.utcnow().timestamp() - session.get('t', 0) < idle:
            session['t'] = datetime.datetime.utcnow().timestamp(); g.u = u
        else: session.pop('uid', None)
    return g.u
def is_staff(): u = me(); return bool(u and u.get('role') != 'student')
def roles(): return {**DEFAULT_ROLES, **kv('roles', {})}
def can(mod, act='v'):
    u = me()
    if not u or u.get('role') == 'student': return False
    if u['role'] == 'super': return True
    return act in roles().get(u['role'], {}).get(mod, '')
def need(mod, act='v'):
    if not is_staff(): abort(401)
    if not can(mod, act): abort(403)
def log(action, u=None):
    u = u or me() or {}
    q('INSERT INTO logs(id,ts,uid,who,kind,action) VALUES(?,?,?,?,?,?)', uid(), now(), u.get('id', ''), u.get('username', ''),
      'student' if u.get('role') == 'student' else 'admin', str(action)[:300], w=True)
def hash_pw(p): return generate_password_hash(p)
def ip(): return (request.remote_addr or '')[:60]

def locked(username):
    n = int(S().get('max_fail') or 5); since = (datetime.datetime.utcnow() - datetime.timedelta(minutes=int(S().get('lock_min') or 15))).isoformat(timespec='seconds')
    r = q('SELECT ok FROM logins WHERE usr=? AND ts>? ORDER BY ts DESC', username.lower(), since)
    fails = 0
    for x in r:
        if x['ok']: break
        fails += 1
    return fails >= n
def login_user(username, password, staff):
    username = (username or '').strip().lower()[:80]
    if not username or locked(username): return None, 'Too many failed attempts. Try again later.'
    cand = [u for u in rows('admins' if staff else 'students') if (u.get('username') or '').lower() == username or (u.get('email') or '').lower() == username]
    u = cand[0] if cand else None
    ok = bool(u and u.get('status') == 'active' and check_password_hash(u.get('pw', ''), password or ''))
    q('INSERT INTO logins(id,ts,usr,ip,ok,ua) VALUES(?,?,?,?,?,?)', uid(), now(), username, ip(), int(ok), request.headers.get('User-Agent', '')[:200], w=True)
    if not ok: return None, 'Invalid username or password.'
    session.clear(); session['uid'] = u['id']; session['t'] = datetime.datetime.utcnow().timestamp(); csrf()
    log('Logged in', u)
    return u, ''

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')[:70] or uuid.uuid4().hex[:6]

def init_demo():
    """First-run seed: default Super Admin + starter content (all editable/deletable in the admin)."""
    if q('SELECT id FROM records WHERE res=?', 'users'): return
    rput('admins', dict(name='Administrator', username='admin', email='admin@vijetha.in', role='super', status='active', photo='',
                        pw=hash_pw('1'), must_change=True))
    t = lambda n, s, b: rput('teachers', dict(name=n, subject=s, bio=b, photo='', order=0, status='published'))
    t1 = t('Dr. Anita Sharma', 'Physics', 'PhD in Physics with 12 years of teaching experience.')
    t2 = t('Rahul Verma', 'Mathematics', 'Makes algebra feel easy.')
    c = lambda ti, p, te, f: rput('courses', dict(title=ti, slug=slugify(ti), desc='<p>Structured live and recorded lessons.</p>', thumb='', price=p, teacher=te,
                                                     duration='1 month', feat=f, publish_at='', expires_at='', status='published'))
    c1 = c('Class 4 – Science & Maths', 500, t1, True); c('Class 5', 600, t2, True); c('Soon', 700, t1, False)
    rput('lessons', dict(course=c1, chapter='Chapter 1', title='Welcome & how this course works', kind='text', file='', url='', body='<p>Start here.</p>', preview=True, order=1))
    rput('live', dict(title='Laws of Motion', course=c1, teacher=t1, kind='youtube', url='', start=(datetime.datetime.utcnow() + datetime.timedelta(days=3)).strftime('%Y-%m-%dT16:00'),
                      minutes=60, thumb='', recording='', recording_file='', desc='', status='published'))
    rput('notices', dict(title='New JEE Foundation batch starts 15 November', body='<p>Enrol now.</p>', image='', file='', urgent=True, show_home=True,
                         publish_at='', expires_at='', status='published'))
    rput('posts', dict(title='Welcome to our new website', slug='welcome', cat='Academy News', tags=['welcome'], excerpt='Our new academy website is live.',
                       body='<p>Everything on this site is now managed from the admin panel.</p>', image='', gallery=[], ext_link='', video='', publish_at='',
                       comments_on=True, status='published', pin=True, feat=True))
    rput('testimonials', dict(name='Priya', role='Class 10', text='Doubts get solved the same day.', photo='', order=1, status='published'))
    rput('sliders', dict(title='Admissions open', subtitle='Live batches from Class 4 to competitive exams', image='', btn_text='See courses', btn_url='/courses', order=1, status='published'))
    for i, (k, ti, sub) in enumerate([('hero', 'Hero', ''), ('notices', 'Latest announcements', ''), ('courses', 'Popular courses', 'Structured batches with live and recorded lessons.'),
                                     ('live', 'Upcoming live classes', ''), ('teachers', 'Featured teachers', ''), ('posts', 'Latest news', ''),
                                     ('testimonials', 'What students say', ''), ('about', 'About the academy', ''), ('contact', 'Contact us', '')]):
        body = '<p>We started with one classroom and one belief: every student can lead.</p>' if k == 'about' else ''
        rput('sections', dict(key=k, title=ti, subtitle=sub, body=body, count=6, enabled=True, order=i))
    pg = lambda ti, body, m=True, o=0: rput('pages', dict(title=ti, slug=slugify(ti), body=body, image='', link_text='', link_url='', seo_title='', seo_desc='',
                                                          in_menu=m, order=o, status='published'))
    pg('About Us', '<p>We make quality teaching affordable and accessible online. Concept first, practice daily, test weekly.</p>', True, 1)
    pg('Contact Us', '<p>Write to us using the form below.</p>', True, 5)
    pg('FAQs', '<h3>How do I join a live class?</h3><p>Enrol in the course, then open the class link from your dashboard.</p>', False)
    pg('Privacy Policy', '<p>We store only the details needed to run your classes. We never sell student data.</p>', False)
    pg('Terms and Conditions', '<p>Accounts are personal. Recordings are for enrolled students only.</p>', False)
    pg('Refund Policy', '<p>Describe your refund policy here.</p>', False)
    for s_ in ('courses', 'teachers'): pg(s_.title(), '<p>Browse our ' + s_ + '.</p>', False)
    kv_set('settings', {}); kv_set('roles', {})
