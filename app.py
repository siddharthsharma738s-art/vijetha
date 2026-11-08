import os, secrets
from flask import Flask, request, jsonify, render_template, session, redirect, abort
import core
from core import init_db, init_demo, csrf, is_staff, S, q
import admin_api, public

def create_app():
    app = Flask(__name__)
    kf = os.path.join(core.DATA, 'secret.key')
    if not os.path.exists(kf): open(kf, 'w').write(secrets.token_hex(32)); os.chmod(kf, 0o600)
    app.secret_key = os.environ.get('SECRET_KEY') or open(kf).read().strip()
    app.config.update(MAX_CONTENT_LENGTH=300 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('HTTPS') == '1', TEMPLATES_AUTO_RELOAD=False)
    app.register_blueprint(admin_api.bp); app.register_blueprint(public.bp)
    with app.app_context(): init_db(); init_demo()

    @app.before_request
    def csrf_check():
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            tok = request.headers.get('X-CSRF') or request.form.get('csrf') or ''
            import hmac
            if not tok or not hmac.compare_digest(tok, session.get('csrf', '')): return jsonify(error='Session expired. Reload the page.'), 400

    @app.after_request
    def headers(r):
        r.headers.setdefault('X-Content-Type-Options', 'nosniff'); r.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        r.headers.setdefault('Referrer-Policy', 'same-origin')
        r.headers.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                             "font-src https://fonts.gstatic.com; img-src 'self' data: https:; media-src 'self' https:; frame-src 'self' https://www.youtube-nocookie.com; frame-ancestors 'self'")
        if request.path.startswith('/api') or request.path.startswith('/admin'): r.headers['Cache-Control'] = 'no-store'
        return r

    @app.get('/admin')
    @app.get('/admin/')
    def admin(): return render_template('admin.html' if is_staff() else 'admin_login.html', csrf=csrf(), s=S())

    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def errs(e):
        if request.path.startswith('/api'): return jsonify(error={401: 'Login required', 403: 'You do not have permission for this action', 404: 'Not found', 405: 'Not allowed', 413: 'File too large'}.get(e.code, 'Error')), e.code
        return render_template('msg.html', title=f'Error {e.code}', text={403: 'You do not have access to this page.', 404: 'Page not found.'}.get(e.code, 'Something went wrong.')), e.code

    @app.teardown_appcontext
    def close(_):
        from flask import g
        c = g.pop('db', None)
        if c: c.close()
    return app

app = create_app()
if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 5000)), debug=False)
