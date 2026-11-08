import os, re, json, hashlib, datetime
from flask import Blueprint, request, render_template, redirect, abort, session, send_from_directory, Response, flash, url_for, make_response
from core import *
from admin_api import fulfill, send_reset, label

bp = Blueprint('site', __name__)
RESERVED = {'admin', 'api', 'media', 'static', 'login', 'register', 'logout', 'account', 'courses', 'course', 'teachers', 'live', 'news', 'post', 'notices',
            'exam', 'exams', 'learn', 'enroll', 'order', 'forgot', 'reset', 'contact', 'robots.txt', 'sitemap.xml'}

def preview(): return request.args.get('preview') == '1' and is_staff()
def ok(r, exp=True):
    if preview(): return True
    if r.get('status') != 'published': return False
    n = lnow()
    return not (r.get('publish_at') and r['publish_at'] > n) and not (exp and r.get('expires_at') and r['expires_at'] <= n)
def srt(L): return sorted(L, key=lambda x: (x.get('order') or 0))
def safe_next(n): return n if n and n.startswith('/') and not n.startswith('//') else '/account'
def user():
    u = me(); return u if u and u['role'] == 'student' else None

def has_access(u, c):
    if not u or not c: return False
    n = lnow()
    if c.get('expires_at') and c['expires_at'] <= n: return False
    if any(e['student'] == u['id'] and e['course'] == c['id'] and e.get('status') == 'active' and (not e.get('expires_at') or e['expires_at'] > n) for e in rows('enrollments')): return True
    return any(s['student'] == u['id'] and s['expires_at'] > n for s in rows('subscriptions'))

def render(t, **k): return render_template(t, **k)

@bp.app_context_processor
def ctx():
    pages = srt([p for p in rows('pages') if ok(p) and p.get('in_menu')])
    urgent = [n for n in rows('notices') if ok(n) and n.get('urgent')][:3] if S().get('show_notice_bar') else []
    foot = [p for p in rows('pages') if ok(p) and not p.get('in_menu') and p['slug'] not in ('courses', 'teachers')]
    return dict(foot=foot, tmap={t['id']: t['name'] for t in rows('teachers')}, s=S(), user=user(), csrf=csrf(), menu=pages, urgent=urgent, preview=preview(), is_staff=is_staff())

@bp.app_template_filter('clean')
def _clean(v): return clean_html(v)
@bp.app_template_filter('money')
def _money(v): return f"{S().get('currency') or '₹'}{float(v or 0):,.0f}" if v else 'Free'
@bp.app_template_filter('dt')
def _dt(v):
    try: return datetime.datetime.strptime(v[:16], '%Y-%m-%dT%H:%M').strftime('%d %b %Y, %I:%M %p')
    except Exception: return v or ''
@bp.app_template_filter('embed')
def _embed(u):
    m = re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|live/|embed/|shorts/))([\w-]{11})', u or '')
    return f'https://www.youtube-nocookie.com/embed/{m.group(1)}' if m else ''
@bp.app_template_filter('lines')
def _lines(v): return [x.strip() for x in str(v or '').split('\n') if x.strip()]

@bp.before_app_request
def maintenance():
    p = request.path
    if S().get('maint') and not is_staff() and not p.startswith(('/admin', '/api', '/static', '/media')):
        return Response(render_template('msg.html', title='Under maintenance', text=S().get('maint_msg')), 503)

@bp.get('/')
def home():
    secs = [x for x in srt(rows('sections')) if x.get('enabled')]; n = lnow()
    D = dict(
        sliders=srt([x for x in rows('sliders') if ok(x)]), banners=srt([x for x in rows('banners') if ok(x)]),
        testimonials=srt([x for x in rows('testimonials') if ok(x)]), teachers=srt([x for x in rows('teachers') if ok(x)]),
        notices=[x for x in rows('notices') if ok(x) and x.get('show_home')],
        courses=sorted([x for x in rows('courses') if ok(x, False)], key=lambda x: not x.get('feat')),
        posts=sorted([x for x in rows('posts') if ok(x)], key=lambda x: (not x.get('pin'), '' ), reverse=False),
        live=sorted([x for x in rows('live') if ok(x) and x.get('status') in ('published', 'live') and (x.get('start', '') >= n[:10] or x.get('status') == 'live')], key=lambda x: x.get('start', '')))
    D['posts'] = sorted(D['posts'], key=lambda x: (x.get('publish_at') or x['_c']), reverse=True); D['posts'].sort(key=lambda x: not x.get('pin'))
    return render('home.html', secs=secs, D=D, seo=dict(title=S().get('seo_title') or S().get('site_title'), desc=S().get('seo_desc') or S().get('site_desc')))

def intro(slug):
    p = next((x for x in rows('pages') if x['slug'] == slug and ok(x)), None); return p

@bp.get('/courses')
def courses():
    return render('list.html', kind='courses', items=sorted([c for c in rows('courses') if ok(c, False)], key=lambda x: not x.get('feat')), page=intro('courses'), title='Courses')
@bp.get('/teachers')
def teachers(): return render('list.html', kind='teachers', items=srt([x for x in rows('teachers') if ok(x)]), page=intro('teachers'), title='Our teachers')
@bp.get('/live')
def live_list(): return render('list.html', kind='live', items=sorted([x for x in rows('live') if ok(x) and x.get('status') != 'draft'], key=lambda x: x.get('start', ''), reverse=True), title='Live classes', page=None)
@bp.get('/news')
def news():
    L = [x for x in rows('posts') if ok(x)]; c = request.args.get('cat'); t = request.args.get('tag')
    if c: L = [x for x in L if x.get('cat') == c]
    if t: L = [x for x in L if t in x.get('tags', [])]
    L.sort(key=lambda x: (x.get('publish_at') or x['_c']), reverse=True); L.sort(key=lambda x: not x.get('pin'))
    return render('list.html', kind='news', items=L, title='News & updates', page=None, cats=sorted({x['cat'] for x in rows('posts') if ok(x) and x.get('cat')}))
@bp.get('/notices')
def notices(): return render('list.html', kind='notices', items=[x for x in rows('notices') if ok(x)], title='Notices', page=None)

@bp.get('/post/<slug>')
def post(slug):
    p = next((x for x in rows('posts') if x['slug'] == slug and ok(x)), None) or abort(404)
    cm = [c for c in rows('comments') if c.get('post') == p['id'] and c.get('status') == 'approved']
    return render('post.html', p=p, comments=cm[::-1], seo=dict(title=p['title'], desc=p.get('excerpt'), img=p.get('image')))
@bp.post('/post/<slug>/comment')
def comment(slug):
    p = next((x for x in rows('posts') if x['slug'] == slug and ok(x)), None) or abort(404)
    if p.get('comments_on') and not request.form.get('website') and request.form.get('text', '').strip():
        rput('comments', dict(post=p['id'], name=request.form.get('name', 'Guest').strip()[:60] or 'Guest', text=request.form['text'].strip()[:1500],
                              status='pending' if S().get('comments_moderate') else 'approved'))
        flash('Thanks! Your comment is awaiting approval.' if S().get('comments_moderate') else 'Comment added.')
    return redirect(f'/post/{slug}')

@bp.get('/course/<slug>')
def course(slug):
    c = next((x for x in rows('courses') if x['slug'] == slug and ok(x, False)), None) or abort(404)
    u = user()
    if S().get('login_to_view') and not u and not preview(): return redirect('/login?next=' + request.path)
    ls = srt([l for l in rows('lessons') if l.get('course') == c['id']])
    expired = bool(c.get('expires_at') and c['expires_at'] <= lnow())
    pend = next((o for o in rows('orders') if u and o['student'] == u['id'] and o.get('item') == c['id'] and o['status'] == 'pending'), None)
    return render('course.html', c=c, ls=ls, teacher=rget('teachers', c.get('teacher')) if c.get('teacher') else None, access=has_access(u, c), expired=expired, pend=pend,
                  seo=dict(title=c['title'], desc=re.sub('<[^>]+>', '', c.get('desc', ''))[:160], img=c.get('thumb')))

@bp.get('/learn/<slug>')
def learn(slug):
    c = next((x for x in rows('courses') if x['slug'] == slug and ok(x, False)), None) or abort(404); u = user()
    if not u: return redirect('/login?next=' + request.path)
    ls = srt([l for l in rows('lessons') if l.get('course') == c['id']]); acc = has_access(u, c)
    cur = next((l for l in ls if l['id'] == request.args.get('l')), ls[0] if ls else None)
    if cur and not (acc or cur.get('preview')): abort(403)
    if cur: log(f'Opened lesson {cur["title"]}', u)
    return render('learn.html', c=c, ls=ls, cur=cur, acc=acc)

@bp.get('/enroll/<cid>')
def _enroll_get(cid): return redirect('/courses')
@bp.post('/enroll/<cid>')
def enroll(cid):
    u = user()
    if not u: return redirect('/login?next=/courses')
    c = rget('courses', cid)
    if not c or not ok(c, False) or (c.get('expires_at') and c['expires_at'] <= lnow()): abort(404)
    if has_access(u, c): return redirect(f'/learn/{c["slug"]}')
    price = c.get('price') or 0; disc = 0; code = request.form.get('coupon', '').strip().upper()
    if code:
        cp = next((x for x in rows('coupons') if x['code'] == code), None)
        bad = not cp or not cp.get('active') or (cp.get('expires_at') and cp['expires_at'] <= lnow()) or (cp.get('max_uses') and cp.get('used', 0) >= cp['max_uses']) or (cp.get('course') and cp['course'] != cid)
        if bad: flash('That coupon is not valid.'); return redirect(f'/course/{c["slug"]}')
        disc = min(price, round(price * cp['value'] / 100, 2) if cp['type'] == 'percent' else cp['value']); cp['used'] = cp.get('used', 0) + 1; rput('coupons', cp, cp['id'])
    amt = max(0, price - disc)
    if price == 0 and not S().get('allow_free'): flash('Enrolment in free courses is closed.'); return redirect(f'/course/{c["slug"]}')
    o = dict(student=u['id'], kind='course', item=cid, title=c['title'], amount=amt, discount=disc, coupon=code, provider='manual', txn='', status='paid' if amt == 0 else 'pending')
    i = rput('orders', o); o['id'] = i
    if amt == 0: fulfill(o); log('Enrolled in ' + c['title'], u); return redirect(f'/learn/{c["slug"]}')
    return redirect(f'/order/{i}')

@bp.get('/order/<i>')
def order(i):
    u = user(); o = rget('orders', i)
    if not u or not o or o['student'] != u['id']: abort(404)
    return render('order.html', o=o)
@bp.post('/order/<i>')
def order_txn(i):
    u = user(); o = rget('orders', i)
    if not u or not o or o['student'] != u['id'] or o['status'] != 'pending': abort(404)
    o['txn'] = request.form.get('txn', '').strip()[:80]; rput('orders', o, i); flash('Reference saved. The academy will confirm your payment shortly.'); return redirect(f'/order/{i}')

@bp.get('/account')
def account():
    u = user()
    if not u: return redirect('/login?next=/account')
    cs = [c for c in rows('courses') if has_access(u, c)]
    ex = [e for e in rows('exams') if ok(e) and (not e.get('course') or any(c['id'] == e['course'] for c in cs))]
    at = {a['exam']: a for a in rows('attempts') if a['student'] == u['id']}
    ls = [l for l in rows('live') if ok(l) and l.get('status') in ('published', 'live') and (not l.get('course') or any(c['id'] == l['course'] for c in cs)) and l.get('start', '') >= lnow()[:10]]
    return render('account.html', courses=cs, exams=ex, at=at, orders=[o for o in rows('orders') if o['student'] == u['id']], live=sorted(ls, key=lambda x: x['start']), enr=len(cs))

@bp.post('/account')
def account_save():
    u = user() or abort(401); d = dict(u)
    d['name'] = request.form.get('name', u['name']).strip()[:60] or u['name']; d['phone'] = request.form.get('phone', '').strip()[:20]
    em = request.form.get('email', '').strip()[:120]
    if em and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', em): flash('Invalid email.'); return redirect('/account')
    d['email'] = em; np = request.form.get('new_password', '')
    if np:
        if not check_password_hash(u['pw'], request.form.get('current_password', '')): flash('Current password is incorrect.'); return redirect('/account')
        if len(np) < 6: flash('New password must be at least 6 characters.'); return redirect('/account')
        d['pw'] = hash_pw(np)
    rput('students', d, u['id']); flash('Profile updated.'); return redirect('/account')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, m = login_user(request.form.get('username'), request.form.get('password'), False)
        if u: return redirect(safe_next(request.args.get('next')))
        flash(m)
    return render('auth.html', mode='login')
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if not S().get('allow_reg'): return render('msg.html', title='Registration closed', text='Please contact the academy to open an account.')
    if request.method == 'POST':
        f = request.form; un = f.get('username', '').strip(); pw = f.get('password', ''); em = f.get('email', '').strip()
        if f.get('website'): abort(400)
        if not re.match(r'^[A-Za-z0-9_.@-]{3,40}$', un): flash('Username: 3-40 letters, digits, . _ - @')
        elif len(pw) < 6: flash('Password must be at least 6 characters.')
        elif em and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', em): flash('Invalid email.')
        elif any((x.get('username') or '').lower() == un.lower() for x in [unpack(r) for r in q('SELECT * FROM records WHERE res=?', 'users')]): flash('Username already taken.')
        else:
            i = rput('students', dict(name=f.get('name', '').strip()[:60] or un, username=un, email=em, phone=f.get('phone', '').strip()[:20], photo='', role='student', status='active', pw=hash_pw(pw)))
            login_user(un, pw, False); return redirect('/account')
    return render('auth.html', mode='register')
@bp.post('/logout')
def logout(): session.clear(); return redirect('/')
@bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        k = request.form.get('username', '').strip().lower()[:80]
        u = next((x for x in rows('students') if k and k in ((x.get('username') or '').lower(), (x.get('email') or '').lower()) and x.get('status') == 'active'), None)
        if u: send_reset(u, request.host_url.rstrip('/'))
        flash('If that account exists, a reset link has been sent. If email is not configured, ask the academy to reset your password.')
    return render('auth.html', mode='forgot')
@bp.route('/reset/<tok>', methods=['GET', 'POST'])
def reset(tok):
    key = 'reset:' + hashlib.sha256(tok.encode()).hexdigest(); r = kv(key)
    if not r or r['exp'] < datetime.datetime.utcnow().isoformat(): return render('msg.html', title='Link expired', text='This reset link is invalid or has expired.')
    u = rget('students', r['uid']) or rget('admins', r['uid']) or abort(404)
    if request.method == 'POST':
        pw = request.form.get('password', ''); mn = 6 if u['role'] == 'student' else 8
        if len(pw) < mn: flash(f'Password must be at least {mn} characters.')
        else:
            u['pw'] = hash_pw(pw); u['must_change'] = False; rput('students' if u['role'] == 'student' else 'admins', u, u['id']); q('DELETE FROM kv WHERE k=?', key, w=True)
            return render('msg.html', title='Password updated', text='You can now log in with your new password.')
    return render('auth.html', mode='reset')

@bp.post('/contact')
def contact():
    f = request.form
    if not f.get('website') and f.get('msg', '').strip():
        rput('enquiries', dict(name=f.get('name', '')[:80], contact=f.get('contact', '')[:80], msg=f['msg'][:3000], handled=False)); flash('Thank you! We will get back to you.')
    return redirect(request.referrer if request.referrer and request.host in request.referrer else '/')

# ---------------- exams ----------------
def exam_ctx(i):
    u = user() or abort(401); e = rget('exams', i)
    if not e or not ok(e): abort(404)
    if e.get('course') and not has_access(u, rget('courses', e['course'])): abort(403)
    return u, e
@bp.get('/exam/<i>')
def exam(i):
    u, e = exam_ctx(i); qs = srt([x for x in rows('questions') if x.get('exam') == i]); mine = [a for a in rows('attempts') if a['student'] == u['id'] and a['exam'] == i]
    if len(mine) >= int(e.get('max_attempts') or 1): return redirect(f'/exam/{i}/result')
    if not qs: return render('msg.html', title=e['title'], text='This exam has no questions yet.')
    session['ex_' + i] = datetime.datetime.utcnow().timestamp()
    return render('exam.html', e=e, qs=qs)
@bp.post('/exam/<i>')
def exam_submit(i):
    u, e = exam_ctx(i); t0 = session.pop('ex_' + i, None); qs = [x for x in rows('questions') if x.get('exam') == i]
    if t0 is None: return redirect(f'/exam/{i}')
    if len([a for a in rows('attempts') if a['student'] == u['id'] and a['exam'] == i]) >= int(e.get('max_attempts') or 1): return redirect(f'/exam/{i}/result')
    late = datetime.datetime.utcnow().timestamp() - t0 > int(e.get('minutes') or 30) * 60 + 45
    sc = 0.0; tot = 0; ans = {}
    for x in qs:
        tot += x.get('marks') or 1; a = request.form.get('q_' + x['id'])
        if late or a is None or not a.isdigit(): continue
        a = int(a); ans[x['id']] = a
        sc += (x.get('marks') or 1) if a == int(x.get('answer') or 0) else (-(x.get('marks') or 1) * float(e.get('neg_mark') or 0) if e.get('negative') else 0)
    rput('attempts', dict(exam=i, student=u['id'], score=round(max(sc, 0) if not e.get('negative') else sc, 2), total=tot, answers=ans, late=late)); log('Submitted exam ' + e['title'], u)
    return redirect(f'/exam/{i}/result')
@bp.get('/exam/<i>/result')
def exam_result(i):
    u, e = exam_ctx(i); a = next((x for x in rows('attempts') if x['student'] == u['id'] and x['exam'] == i), None) or abort(404)
    return render('exam_result.html', e=e, a=a, qs=srt([x for x in rows('questions') if x.get('exam') == i]))

# ---------------- files, seo, pages ----------------
@bp.get('/media/<path:p>')
def media(p):
    if '/' in p or '\\' in p or p.startswith('.'): abort(404)
    ext = p.rsplit('.', 1)[-1].lower(); r = send_from_directory(UP, p, conditional=True, as_attachment=ext in ('zip', 'doc', 'docx', 'ppt', 'pptx'))
    if ext == 'svg': r.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    r.headers['Cache-Control'] = 'public, max-age=3600'; return r
@bp.get('/robots.txt')
def robots(): return Response(('User-agent: *\nDisallow: /\n' if S().get('noindex') else 'User-agent: *\nDisallow: /admin\nDisallow: /api\nSitemap: ' + request.host_url + 'sitemap.xml\n'), mimetype='text/plain')
@bp.get('/sitemap.xml')
def sitemap():
    u = ['/', '/courses', '/teachers', '/live', '/news'] + [f'/{p["slug"]}' for p in rows('pages') if ok(p)] + [f'/course/{c["slug"]}' for c in rows('courses') if ok(c, False)] + [f'/post/{p["slug"]}' for p in rows('posts') if ok(p)]
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{request.host_url.rstrip("/")}{x}</loc></url>' for x in dict.fromkeys(u)) + '</urlset>', mimetype='application/xml')
@bp.get('/<slug>')
def page(slug):
    p = next((x for x in rows('pages') if x['slug'] == slug and ok(x)), None) or abort(404)
    return render('page.html', p=p, seo=dict(title=p.get('seo_title') or p['title'], desc=p.get('seo_desc'), img=p.get('image')), contact=slug.startswith('contact'))
