import os, re, io, csv, json, uuid, zipfile, hashlib, secrets, smtplib, datetime
from email.message import EmailMessage
from flask import Blueprint, request, jsonify, session, send_file, abort, g
from core import *
from schema import RES, SETTINGS, DEFAULT_SETTINGS, DEFAULT_ROLES, MODS, ROLE_LABELS

bp = Blueprint('api', __name__, url_prefix='/api')
def err(m, c=400): return jsonify(error=m), c
LET = dict(view='v', create='c', edit='e', publish='p', delete='d')
EXT = {'jpg', 'jpeg', 'png', 'webp', 'gif', 'svg', 'mp4', 'pdf', 'zip', 'ppt', 'pptx', 'doc', 'docx'}
HIDE = ('pw', 'must_change')

def chk(res):
    if res not in RES: abort(404)
    return RES[res]
def valid_media(v): return v.startswith('/media/') or safe_url(v, True)

def coerce(f, v):
    t = f['t']
    if t == 'chk': return v in (True, 1, 'true', '1', 'on')
    if t == 'num':
        if v in ('', None): return 0
        try: x = float(v)
        except (TypeError, ValueError): raise ValueError(f"{f['l']} must be a number")
        return int(x) if x == int(x) else x
    if t == 'tags':
        L = v if isinstance(v, list) else str(v or '').split(',')
        return [str(x).strip()[:40] for x in L if str(x).strip()][:30]
    if t == 'medias': return [x for x in (v or []) if isinstance(x, str) and valid_media(x)][:50]
    v = '' if v is None else str(v).strip()
    if t == 'html': return clean_html(v)
    if t == 'area': return v[:20000]
    if t == 'url':
        if v and not safe_url(v): raise ValueError(f"{f['l']}: only http(s), mailto or site-relative links are allowed")
        return v[:500]
    if t == 'media':
        if v and not valid_media(v): raise ValueError(f"{f['l']}: invalid media path")
        return v
    if t == 'sel':
        if v not in f['opts']: raise ValueError(f"{f['l']}: invalid choice")
        return v
    if t == 'email':
        if v and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', v): raise ValueError('Enter a valid email address')
        return v[:120]
    if t == 'ref': return v[:32]
    if t == 'color':
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v): raise ValueError(f"{f['l']}: use a #RRGGBB colour")
        return v
    return v[:300]

def build(res, body, old=None):
    R = RES[res]; d = dict(old or {})
    if old is None: d.update(R.get('defaults', {}))
    for f in R['fields']:
        if f['t'] == 'pass': continue
        k = f['k']
        if k in body: v = coerce(f, body[k])
        elif old is not None: continue
        else: v = coerce(f, f.get('default', ''))
        if f.get('req') and v in ('', None, []): raise ValueError(f"{f['l']} is required")
        d[k] = v
    if R.get('slug'):
        base = slugify(d.get('slug') or d.get('title')); s_ = base; n = 2
        while any(x['slug'] == s_ and x['id'] != (old or {}).get('id') for x in rows(res)): s_ = f'{base}-{n}'; n += 1
        d['slug'] = s_
    return d

def snap(res, i, d, tag='edit'):
    q('INSERT INTO versions(id,res,rid,data,ts,author) VALUES(?,?,?,?,?,?)', uid(), res, i, json.dumps(d), now(), (me() or {}).get('username', ''), w=True)
    old = q('SELECT id FROM versions WHERE res=? AND rid=? ORDER BY ts DESC', res, i)
    for x in old[30:]: q('DELETE FROM versions WHERE id=?', x['id'], w=True)

_lab = {}
def label(res, i):
    if not i: return ''
    r = rget(res, i)
    return (r or {}).get('title') or (r or {}).get('name') or (r or {}).get('code') or ''
def out(res, d):
    d = {k: v for k, v in d.items() if k not in HIDE}
    for f in RES[res]['fields']:
        if f['t'] == 'ref': d['_' + f['k']] = label(f['ref'], d.get(f['k']))
    return d

# ------------------------------------------------------------ session
@bp.post('/login')
def login():
    b = request.get_json(silent=True) or {}
    u, m = login_user(b.get('username'), b.get('password'), True)
    return (jsonify(ok=True), 200) if u else err(m, 401)

@bp.post('/logout')
def logout():
    if me(): log('Logged out')
    session.clear(); return jsonify(ok=True)

def perms():
    u = me()
    return {m: 'vcepd' for m in MODS} if u['role'] == 'super' else {m: roles().get(u['role'], {}).get(m, '') for m in MODS}

@bp.get('/me')
def whoami():
    need_staff = is_staff()
    if not need_staff: return err('Login required', 401)
    u = me()
    return jsonify(user={k: v for k, v in u.items() if k not in ('pw',)}, perms=perms(), csrf=csrf(), role_label=ROLE_LABELS.get(u['role']))

@bp.put('/me')
def update_me():
    if not is_staff(): return err('Login required', 401)
    u = me(); b = request.get_json(silent=True) or {}
    try:
        name = coerce(dict(l='Name', t='text'), b.get('name', u['name'])); email = coerce(dict(l='Email', t='email'), b.get('email', u.get('email', '')))
        photo = coerce(dict(l='Photo', t='media'), b.get('photo', u.get('photo', '')))
    except ValueError as e: return err(str(e))
    un = str(b.get('username', u['username'])).strip()
    if not re.match(r'^[A-Za-z0-9_.@-]{1,40}$', un): return err('Username: letters, digits, . _ - @ only')
    if any(x['id'] != u['id'] and (x.get('username') or '').lower() == un.lower() for x in all_users()): return err('Username already taken')
    d = dict(u, name=name, username=un, email=email, photo=photo)
    if b.get('new_password'):
        if not check_password_hash(u['pw'], b.get('current_password', '')): return err('Current password is incorrect')
        if len(b['new_password']) < 8: return err('New password must be at least 8 characters')
        d['pw'] = hash_pw(b['new_password']); d['must_change'] = False
    rput('admins', d, u['id']); g.u = d; log('Updated own profile'); return jsonify(ok=True)

def all_users(): return [unpack(r) for r in q('SELECT * FROM records WHERE res=?', 'users')]

def send_reset(u, base):
    tok = secrets.token_urlsafe(32); kv_set('reset:' + hashlib.sha256(tok.encode()).hexdigest(), dict(uid=u['id'], exp=(datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()))
    link = f'{base}/reset/{tok}'
    host = os.environ.get('SMTP_HOST')
    if host and u.get('email'):
        m = EmailMessage(); m['Subject'] = 'Password reset'; m['From'] = os.environ.get('SMTP_FROM', 'no-reply@vijetha.in'); m['To'] = u['email']
        m.set_content(f'Use this link within 1 hour to set a new password:\n{link}\nIgnore this email if you did not ask for it.')
        with smtplib.SMTP(host, int(os.environ.get('SMTP_PORT', 587))) as s:
            s.starttls(); s.login(os.environ.get('SMTP_USER', ''), os.environ.get('SMTP_PASS', '')); s.send_message(m)
    else:  # no mail server configured: write to server log so the server owner can deliver it
        with open(os.path.join(DATA, 'recovery.log'), 'a') as f: f.write(f'{now()} {u["username"]} {link}\n')
        print('[password recovery link]', u['username'], link)

@bp.post('/forgot')
def forgot():
    b = request.get_json(silent=True) or {}; un = str(b.get('username', '')).strip().lower()[:80]
    recent = q('SELECT id FROM logins WHERE usr=? AND ts>?', 'forgot:' + ip(), (datetime.datetime.utcnow() - datetime.timedelta(minutes=10)).isoformat(timespec='seconds'))
    if len(recent) >= 3: return err('Too many requests. Try again later.', 429)
    q('INSERT INTO logins(id,ts,usr,ip,ok,ua) VALUES(?,?,?,?,?,?)', uid(), now(), 'forgot:' + ip(), ip(), 1, '', w=True)
    u = next((x for x in rows('admins') if un and un in ((x.get('username') or '').lower(), (x.get('email') or '').lower()) and x.get('status') == 'active'), None)
    if u: send_reset(u, request.host_url.rstrip('/'))
    return jsonify(ok=True, msg='If that account exists, a reset link has been sent (or written to the server recovery log if email is not configured).')

# ------------------------------------------------------------ schema / dashboard
@bp.get('/schema')
def schema():
    if not is_staff(): return err('Login required', 401)
    return jsonify(res={k: v for k, v in RES.items() if not v.get('hidden')}, settings=SETTINGS, mods=MODS, role_labels=ROLE_LABELS,
                   perms=perms(), sup=me()['role'] == 'super')

def revenue():
    paid = [o for o in rows('orders') if o.get('status') == 'paid']; by = {}
    for o in paid: by[o['_c'][:7]] = by.get(o['_c'][:7], 0) + (o.get('amount') or 0)
    return dict(total=sum(o.get('amount') or 0 for o in paid), paid=len(paid), pending=sum(1 for o in rows('orders') if o.get('status') == 'pending'),
                refunded=sum(1 for o in rows('orders') if o.get('status') == 'refunded'), by_month=[dict(m=k, amount=by[k]) for k in sorted(by)[-6:]])
def storage():
    used = sum(m.get('size', 0) for m in rows('media')); return dict(used=used, quota=int(S().get('quota_mb') or 1024) * 1048576, files=len(rows('media')))

@bp.get('/dashboard')
def dashboard():
    if not is_staff(): return err('Login required', 401)
    P = perms(); st = rows('students'); co = rows('courses'); en = rows('enrollments'); ex = rows('exams'); at = rows('attempts')
    d = dict(students=len(st), courses=len(co), posts=len(rows('posts')), storage=storage(), revenue=revenue() if P['payments'] else None,
             upcoming=[out('live', x) for x in sorted(rows('live'), key=lambda x: x.get('start', '')) if x.get('start', '') >= lnow() and x.get('status') in ('published', 'live')][:5],
             recent=[dict(name=x['name'], username=x['username'], when=x['_c']) for x in st[:6]],
             activity=q('SELECT ts,who,action FROM logs WHERE kind=? ORDER BY ts DESC LIMIT 12', 'admin') if P['activity'] else [],
             course_stats=[dict(title=c['title'], enrolled=sum(1 for e in en if e.get('course') == c['id'] and e.get('status') == 'active')) for c in co[:8]],
             exam_stats=[dict(title=e['title'], attempts=len([a for a in at if a.get('exam') == e['id']]),
                              avg=round(sum((a['score'] / a['total'] * 100) for a in at if a.get('exam') == e['id'] and a.get('total')) / max(1, len([a for a in at if a.get('exam') == e['id'] and a.get('total')])), 1)) for e in ex[:8]])
    return jsonify(d)

@bp.get('/reports/revenue')
def rev_report(): need('payments'); return jsonify(revenue())

# ------------------------------------------------------------ settings / roles / logs / backup
@bp.get('/settings')
def get_settings(): need('settings'); return jsonify(values=S(), versions=q('SELECT id,ts,author FROM versions WHERE res=? ORDER BY ts DESC LIMIT 20', 'settings'))

@bp.put('/settings')
def put_settings():
    need('settings', 'e'); b = request.get_json(silent=True) or {}; cur = dict(S()); sup = me()['role'] == 'super'
    try:
        for f in SETTINGS:
            if f['k'] in b:
                if f.get('sup') and not sup: continue
                if f['g'] in ('Maintenance',) and not sup: continue
                cur[f['k']] = coerce(f, b[f['k']]) if f['t'] != 'sel' or b[f['k']] in f['opts'] else cur[f['k']]
    except ValueError as e: return err(str(e))
    snap('settings', 'settings', kv('settings', {})); kv_set('settings', {k: v for k, v in cur.items() if k in DEFAULT_SETTINGS}); log('Updated website settings'); return jsonify(ok=True)

@bp.post('/settings/restore/<vid>')
def restore_settings(vid):
    need('settings', 'e'); r = q('SELECT data FROM versions WHERE id=? AND res=?', vid, 'settings')
    if not r: abort(404)
    snap('settings', 'settings', kv('settings', {})); kv_set('settings', json.loads(r[0]['data'])); log('Restored settings version'); return jsonify(ok=True)

@bp.get('/roles')
def get_roles(): need('roles'); return jsonify(roles=roles(), mods=MODS, labels=ROLE_LABELS)

@bp.put('/roles')
def put_roles():
    if not is_staff() or me()['role'] != 'super': return err('Only the Super Admin can change roles', 403)
    b = (request.get_json(silent=True) or {}).get('roles', {}); out_ = {}
    for r_ in DEFAULT_ROLES: out_[r_] = {m: ''.join(c for c in 'vcepd' if c in str(b.get(r_, {}).get(m, ''))) for m in MODS}
    kv_set('roles', out_); log('Updated role permissions'); return jsonify(ok=True)

@bp.get('/logs')
def get_logs():
    need('activity'); ql = '%' + request.args.get('q', '') + '%'
    return jsonify(items=q('SELECT ts,who,action FROM logs WHERE kind=? AND (action LIKE ? OR who LIKE ?) ORDER BY ts DESC LIMIT 300', 'admin', ql, ql),
                   logins=q('SELECT ts,usr,ip,ok FROM logins WHERE usr NOT LIKE ? ORDER BY ts DESC LIMIT 100', 'forgot:%'))

@bp.get('/backup')
def backup():
    if not is_staff() or me()['role'] != 'super': return err('Super Admin only', 403)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('db.json', json.dumps(dict(records=q('SELECT * FROM records'), kv=q('SELECT * FROM kv'), versions=q('SELECT * FROM versions'))))
        for f in os.listdir(UP): z.write(os.path.join(UP, f), 'uploads/' + f)
    buf.seek(0); log('Downloaded backup')
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=f'vijetha-backup-{datetime.date.today()}.zip')

@bp.post('/restore')
def restore():
    if not is_staff() or me()['role'] != 'super': return err('Super Admin only', 403)
    f = request.files.get('file')
    try:
        z = zipfile.ZipFile(f.stream); dbj = json.loads(z.read('db.json'))
        names = [n for n in z.namelist() if n.startswith('uploads/') and n != 'uploads/']
        for n in names:
            b_ = os.path.basename(n)
            if b_ != n[8:] or b_.rsplit('.', 1)[-1].lower() not in EXT or '..' in b_: return err('Backup contains unsafe files')
    except Exception: return err('Not a valid backup file')
    for t in ('records', 'kv', 'versions'): q(f'DELETE FROM {t}', w=True)
    for r in dbj['records']: q('INSERT INTO records(id,res,data,created,updated) VALUES(?,?,?,?,?)', r['id'], r['res'], r['data'], r['created'], r['updated'], w=True)
    for r in dbj['kv']: q('INSERT INTO kv(k,v) VALUES(?,?)', r['k'], r['v'], w=True)
    for r in dbj['versions']: q('INSERT INTO versions(id,res,rid,data,ts,author) VALUES(?,?,?,?,?,?)', r['id'], r['res'], r['rid'], r['data'], r['ts'], r['author'], w=True)
    for n in names: open(os.path.join(UP, os.path.basename(n)), 'wb').write(z.read(n))
    session.clear(); return jsonify(ok=True, msg='Restored. Please log in again.')

# ------------------------------------------------------------ media manager
def sniff(ext, d):
    sig = dict(jpg=[b'\xff\xd8\xff'], jpeg=[b'\xff\xd8\xff'], png=[b'\x89PNG'], gif=[b'GIF8'], pdf=[b'%PDF'], zip=[b'PK'], docx=[b'PK'], pptx=[b'PK'],
               doc=[b'\xd0\xcf\x11\xe0'], ppt=[b'\xd0\xcf\x11\xe0'])
    if ext == 'webp': return d[:4] == b'RIFF' and d[8:12] == b'WEBP'
    if ext == 'mp4': return d[4:8] == b'ftyp'
    if ext == 'svg': return svg_ok(d)
    return any(d.startswith(s) for s in sig.get(ext, []))

def check_file(fs, ext_must=None):
    name = fs.filename or ''; ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if ext not in EXT: return None, f'{name}: file type not allowed'
    if ext_must and ext != ext_must: return None, f'{name}: replacement must be a .{ext_must} file'
    d = fs.read()
    if len(d) > int(S().get('max_mb') or 50) * 1048576: return None, f'{name}: larger than {S().get("max_mb")} MB'
    if not sniff(ext, d): return None, f'{name}: content does not match a valid .{ext} file'
    return (ext, d), None

@bp.get('/media')
def media_list():
    need('media'); L = rows('media'); ql = request.args.get('q', '').lower(); fo = request.args.get('folder')
    if ql: L = [m for m in L if ql in m['name'].lower()]
    if fo is not None and fo != '*': L = [m for m in L if m.get('folder', '') == fo]
    return jsonify(items=L, folders=[f['name'] for f in rows('folders')], storage=storage())

@bp.post('/media/upload')
def media_upload():
    need('media', 'c'); ok, errs = [], []; fo = request.form.get('folder', '')[:40]
    for fs in request.files.getlist('files'):
        r, e = check_file(fs)
        if e: errs.append(e); continue
        ext, d = r
        if storage()['used'] + len(d) > storage()['quota']: errs.append(f'{fs.filename}: storage quota exceeded'); continue
        fn = uuid.uuid4().hex + '.' + ext; open(os.path.join(UP, fn), 'wb').write(d)
        nm = re.sub(r'[^\w .()-]', '_', fs.filename)[:100]
        i = rput('media', dict(name=nm, file=fn, url='/media/' + fn, size=len(d), ext=ext, folder=fo, by=me()['username'])); ok.append(i)
    if ok: log(f'Uploaded {len(ok)} file(s)')
    return jsonify(ok=ok, errors=errs)

@bp.put('/media/<i>')
def media_edit(i):
    need('media', 'e'); m = rget('media', i) or abort(404); b = request.get_json(silent=True) or {}
    if 'name' in b: m['name'] = re.sub(r'[^\w .()-]', '_', str(b['name']))[:100] or m['name']
    if 'folder' in b: m['folder'] = str(b['folder'])[:40]
    rput('media', m, i); log('Renamed/moved media ' + m['name']); return jsonify(ok=True)

@bp.post('/media/<i>/replace')
def media_replace(i):
    need('media', 'e'); m = rget('media', i) or abort(404); fs = request.files.get('file')
    if not fs: return err('No file')
    r, e = check_file(fs, m['ext'])
    if e: return err(e)
    open(os.path.join(UP, m['file']), 'wb').write(r[1]); m['size'] = len(r[1]); rput('media', m, i); log('Replaced media ' + m['name']); return jsonify(ok=True)

def usage(url): return len(q('SELECT id FROM records WHERE data LIKE ? AND res<>?', '%' + url + '%', 'media')) + (1 if url in json.dumps(kv('settings', {})) else 0)

@bp.delete('/media/<i>')
def media_del(i):
    need('media', 'd'); m = rget('media', i) or abort(404); n = usage(m['url'])
    if n and request.args.get('force') != '1': return jsonify(error=f'This file is used in {n} place(s). Delete anyway?', used=n), 409
    try: os.remove(os.path.join(UP, m['file']))
    except OSError: pass
    rdel('media', i); log('Deleted media ' + m['name']); return jsonify(ok=True)

# ------------------------------------------------------------ extras: attendance, details, export
@bp.get('/live/<i>/attendance')
def att_get(i):
    need('live'); l = rget('live', i) or abort(404)
    ids = {e['student'] for e in rows('enrollments') if e.get('course') == l.get('course') and e.get('status') == 'active'} if l.get('course') else None
    done = {a['student']: a['present'] for a in rows('attendance') if a.get('live') == i}
    return jsonify(items=[dict(id=s['id'], name=s['name'], present=done.get(s['id'], False)) for s in rows('students') if ids is None or s['id'] in ids])

@bp.post('/live/<i>/attendance')
def att_set(i):
    need('live', 'e'); rget('live', i) or abort(404); pres = set((request.get_json(silent=True) or {}).get('present', []))
    for a in rows('attendance'):
        if a.get('live') == i: rdel('attendance', a['id'])
    for s in pres: rput('attendance', dict(live=i, student=str(s)[:32], present=True))
    log(f'Saved attendance for class {i}'); return jsonify(ok=True)

@bp.get('/students/<i>/detail')
def stu_detail(i):
    need('students'); s = rget('students', i) or abort(404)
    return jsonify(student=out('students', s), enrollments=[out('enrollments', e) for e in rows('enrollments') if e.get('student') == i],
                   orders=[out('orders', o) for o in rows('orders') if o.get('student') == i], attempts=[out('attempts', a) for a in rows('attempts') if a.get('student') == i],
                   activity=q('SELECT ts,action FROM logs WHERE uid=? ORDER BY ts DESC LIMIT 30', i), logins=q('SELECT ts,ip,ok FROM logins WHERE usr=? ORDER BY ts DESC LIMIT 15', s['username'].lower()))

@bp.get('/admins/<i>/logins')
def adm_logins(i):
    need('admins'); u = rget('admins', i) or abort(404)
    return jsonify(logins=q('SELECT ts,ip,ok FROM logins WHERE usr=? ORDER BY ts DESC LIMIT 50', u['username'].lower()))

@bp.get('/export/<res>')
def export(res):
    R = chk(res); need(R['mod']); w = io.StringIO(); c = csv.writer(w); fs = [f for f in R['fields'] if f['t'] != 'pass']
    c.writerow([f['l'] for f in fs] + ['Created'])
    esc_ = lambda v: "'" + v if v[:1] in '=+-@\t\r' and v else v
    for d in rows(res):
        o = out(res, d); c.writerow([esc_(str(', '.join(o[f['k']]) if isinstance(o.get(f['k']), list) else o.get('_' + f['k'], o.get(f['k'], '')))) for f in fs] + [d['_c']])
    log('Exported ' + res)
    return send_file(io.BytesIO(('\ufeff' + w.getvalue()).encode()), mimetype='text/csv', as_attachment=True, download_name=f'{res}-{datetime.date.today()}.csv')

# ------------------------------------------------------------ generic REST for every module
CASC = dict(courses=[('lessons', 'course'), ('enrollments', 'course')], exams=[('questions', 'exam'), ('attempts', 'exam')], posts=[('comments', 'post')],
            students=[('enrollments', 'student'), ('attempts', 'student')], live=[('attendance', 'live')])

@bp.get('/<res>')
def lst(res):
    R = chk(res); need(R['mod']); L = rows(res)
    for k, v in request.args.items():
        if k not in ('q', 'limit'): L = [x for x in L if str(x.get(k, '')) == v]
    ql = request.args.get('q', '').lower()
    if ql: L = [x for x in L if ql in json.dumps({k: v for k, v in out(res, x).items() if k not in ('_c', '_u')}, ensure_ascii=False).lower()]
    if R.get('ordered'): L.sort(key=lambda x: (x.get('order') or 0, x['_c']))
    return jsonify(items=[out(res, x) for x in L])

@bp.get('/<res>/<i>')
def one(res, i):
    R = chk(res); need(R['mod']); return jsonify(out(res, rget(res, i) or abort(404)))

def guard_staff(res, old, new):
    if res == 'admins' and me()['role'] != 'super': abort(403)
    if res == 'admins' and old and old['id'] == me()['id'] and (new.get('status') == 'inactive' or new.get('role') != 'super' and old['role'] == 'super'):
        raise ValueError('You cannot deactivate or demote your own account')

@bp.post('/<res>')
def create(res):
    R = chk(res); need(R['mod'], 'c'); b = request.get_json(silent=True) or {}
    if R.get('nocreate'): abort(405)
    try:
        d = build(res, b)
        if R.get('pub') and d.get('status') in ('published', 'live') : need(R['mod'], 'p')
        if R.get('store') == 'users':
            pw = str(b.get('password', '')); mn = 8 if res == 'admins' else 6
            if len(pw) < mn: raise ValueError(f'Password must be at least {mn} characters')
            if not re.match(r'^[A-Za-z0-9_.@-]{1,40}$', d['username']): raise ValueError('Username: letters, digits, . _ - @ only')
            if any((x.get('username') or '').lower() == d['username'].lower() for x in all_users()): raise ValueError('Username already taken')
            guard_staff(res, None, d); d['pw'] = hash_pw(pw)
            if res == 'admins': d['must_change'] = True
        if res == 'coupons': d['code'] = d['code'].upper()
    except ValueError as e: return err(str(e))
    i = rput(res, d); log(f'Created {R["label"]}: {d.get("title") or d.get("name") or d.get("code") or i}'); return jsonify(id=i)

@bp.put('/<res>/<i>')
def update(res, i):
    R = chk(res); need(R['mod'], 'e'); old = rget(res, i) or abort(404); b = request.get_json(silent=True) or {}
    if R.get('noedit'): abort(405)
    try:
        d = build(res, b, old)
        if R.get('pub') and d.get('status') != old.get('status'): need(R['mod'], 'p')
        if R.get('store') == 'users':
            if not re.match(r'^[A-Za-z0-9_.@-]{1,40}$', d['username']): raise ValueError('Username: letters, digits, . _ - @ only')
            if any(x['id'] != i and (x.get('username') or '').lower() == d['username'].lower() for x in all_users()): raise ValueError('Username already taken')
            guard_staff(res, old, d)
        if res == 'coupons': d['code'] = d['code'].upper()
    except ValueError as e: return err(str(e))
    if R.get('ver'): snap(res, i, old)
    rput(res, d, i); log(f'Edited {R["label"]}: {d.get("title") or d.get("name") or d.get("code") or i}'); return jsonify(ok=True)

@bp.delete('/<res>/<i>')
def delete(res, i):
    R = chk(res); need(R['mod'], 'd'); old = rget(res, i) or abort(404)
    if res == 'admins':
        if me()['role'] != 'super': abort(403)
        if i == me()['id']: return err('You cannot delete your own account')
    for r2, k in CASC.get(res, []):
        for x in rows(r2):
            if x.get(k) == i: rdel(r2, x['id'])
    rdel(res, i); log(f'Deleted {R["label"]}: {old.get("title") or old.get("name") or old.get("code") or i}'); return jsonify(ok=True)

@bp.post('/<res>/reorder')
def reorder(res):
    R = chk(res); need(R['mod'], 'e')
    for n, i in enumerate((request.get_json(silent=True) or {}).get('ids', [])):
        d = rget(res, str(i))
        if d: d['order'] = n; rput(res, d, d['id'])
    log(f'Reordered {R["label"]}'); return jsonify(ok=True)

@bp.get('/<res>/<i>/versions')
def versions(res, i):
    R = chk(res); need(R['mod'], 'e'); return jsonify(items=q('SELECT id,ts,author FROM versions WHERE res=? AND rid=? ORDER BY ts DESC', res, i))

@bp.post('/<res>/<i>/restore/<vid>')
def restore_v(res, i, vid):
    R = chk(res); need(R['mod'], 'e'); cur = rget(res, i) or abort(404); r = q('SELECT data FROM versions WHERE id=? AND rid=?', vid, i) or abort(404)
    snap(res, i, cur); d = json.loads(r[0]['data']); d['status'] = cur.get('status', d.get('status')); rput(res, d, i)
    log(f'Restored version of {R["label"]}: {d.get("title") or i}'); return jsonify(ok=True)

def fulfill(o):
    if o.get('kind') == 'plan':
        p = rget('plans', o['item']) or {}
        rput('subscriptions', dict(student=o['student'], plan=o['item'], expires_at=(datetime.datetime.utcnow() + datetime.timedelta(days=int(p.get('days') or 30))).strftime('%Y-%m-%dT%H:%M')))
        return
    e = next((x for x in rows('enrollments') if x['student'] == o['student'] and x['course'] == o['item']), None)
    if e: e['status'] = 'active'; rput('enrollments', e, e['id'])
    else: rput('enrollments', dict(student=o['student'], course=o['item'], status='active', expires_at=''))

@bp.post('/<res>/<i>/<act>')
def action(res, i, act):
    R = chk(res); d = rget(res, i) or abort(404); b = request.get_json(silent=True) or {}; ttl = d.get('title') or d.get('name') or i
    flag = dict(pin=('pin', True), unpin=('pin', False), feature=('feat', True), unfeature=('feat', False), handled=('handled', True),
                publish_results=('results_published', True), hide_results=('results_published', False))
    st = dict(publish='published', unpublish='draft', approve='approved', spam='spam', endclass='ended', cancelclass='cancelled')
    if act in ('publish', 'unpublish', 'publish_results', 'hide_results', 'endclass', 'cancelclass') and R.get('pub') or act in ('approve', 'spam'): need(R['mod'], 'p' if R.get('pub') else 'e')
    else: need(R['mod'], 'e')
    if act in st and (R.get('pub') or res == 'comments'):
        if R.get('ver'): snap(res, i, d)
        d['status'] = st[act]
    elif act in flag and (flag[act][0] in [f['k'] for f in R['fields']] or (act in ('pin', 'unpin') and R.get('pin')) or (act in ('feature', 'unfeature') and R.get('feat'))): d[flag[act][0]] = flag[act][1]
    elif act == 'reset' and R.get('store') == 'users':
        if res == 'admins' and me()['role'] != 'super': abort(403)
        pw = str(b.get('password', '')); mn = 8 if res == 'admins' else 6
        if len(pw) < mn: return err(f'Password must be at least {mn} characters')
        d['pw'] = hash_pw(pw); d['must_change'] = res == 'admins'
    elif act == 'paid' and res == 'orders':
        d['status'] = 'paid'; d['txn'] = str(b.get('txn', d.get('txn', '')))[:80]; rput(res, d, i); fulfill(d)
    elif act == 'refund' and res == 'orders':
        if d.get('status') != 'paid': return err('Only paid orders can be refunded')
        d['status'] = 'refunded'
        if d.get('kind') == 'course':
            for e in rows('enrollments'):
                if e['student'] == d['student'] and e['course'] == d['item']: e['status'] = 'revoked'; rput('enrollments', e, e['id'])
    else: abort(400)
    rput(res, d, i); log(f'{act} → {R["label"]}: {ttl}')
    return jsonify(ok=True, msg='Refund recorded. Provider is "manual": return the money through your payment channel.' if act == 'refund' else '')
