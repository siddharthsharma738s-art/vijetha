"""Single source of truth for every manageable module: drives the REST API, validation, permissions and the admin UI."""

def F(k, l, t='text', **kw):
    d = dict(k=k, l=l, t=t); d.update(kw); return d

# field types: text area html num sel dt chk media medias ref tags url email pass color
STATUS = F('status', 'Status', 'sel', opts=['draft', 'published'], default='draft')
ORDER = F('order', 'Order', 'num', default=0)
RES = {}

def R(name, label, group, fields, cols, mod=None, **kw):
    RES[name] = dict(name=name, label=label, group=group, mod=mod or name, fields=fields, cols=cols, **kw)

R('posts', 'Posts', 'Content', [
    F('title', 'Title', req=1), F('slug', 'URL slug', help='Auto-generated if empty'),
    F('cat', 'Category'), F('tags', 'Tags', 'tags'), F('excerpt', 'Short description', 'area'),
    F('body', 'Long-form content', 'html'), F('image', 'Cover image', 'media'),
    F('gallery', 'More images', 'medias'), F('ext_link', 'External link', 'url'), F('video', 'Video link (YouTube/MP4)', 'url'),
    F('publish_at', 'Schedule (publish at)', 'dt'), F('comments_on', 'Allow comments', 'chk', default=True), STATUS,
], ['title', 'cat', 'status', 'publish_at'], pub=1, pin=1, feat=1, ver=1, slug=1, preview='/post/{slug}',
  acts=['history'])
R('comments', 'Comments', 'Content', [
    F('post', 'Post', 'ref', ref='posts'), F('name', 'Name', req=1), F('text', 'Comment', 'area', req=1),
    F('status', 'Status', 'sel', opts=['pending', 'approved', 'spam'], default='pending')],
  ['name', 'text', 'post', 'status'], mod='comments', acts=['approve', 'spam'], nocreate=1)
R('pages', 'Pages', 'Content', [
    F('title', 'Page title', req=1), F('slug', 'URL slug'), F('body', 'Content', 'html'), F('image', 'Page image', 'media'),
    F('link_text', 'Button text'), F('link_url', 'Button link', 'url'),
    F('seo_title', 'SEO title'), F('seo_desc', 'SEO description', 'area'),
    F('in_menu', 'Show in menu', 'chk'), ORDER, STATUS],
  ['title', 'slug', 'status'], pub=1, ver=1, slug=1, ordered=1, preview='/{slug}', acts=['history'])
R('notices', 'Notices', 'Content', [
    F('title', 'Title', req=1), F('body', 'Details', 'html'), F('image', 'Image', 'media'), F('file', 'Attachment', 'media'),
    F('urgent', 'Urgent announcement', 'chk'), F('show_home', 'Show on homepage', 'chk', default=True),
    F('publish_at', 'Schedule (publish at)', 'dt'), F('expires_at', 'Hide after', 'dt'), STATUS],
  ['title', 'urgent', 'status', 'publish_at'], pub=1, ver=1, acts=['history'])
R('sliders', 'Sliders', 'Homepage', [
    F('title', 'Heading', req=1), F('subtitle', 'Subtitle'), F('image', 'Banner image', 'media'),
    F('btn_text', 'Button text'), F('btn_url', 'Button link', 'url'), ORDER, STATUS],
  ['title', 'btn_text', 'order', 'status'], pub=1, ordered=1)
R('banners', 'Promo banners', 'Homepage', [
    F('title', 'Title', req=1), F('image', 'Image', 'media'), F('url', 'Link', 'url'), ORDER, STATUS],
  ['title', 'url', 'order', 'status'], pub=1, ordered=1)
R('testimonials', 'Testimonials', 'Homepage', [
    F('name', 'Student name', req=1), F('role', 'Class / exam'), F('text', 'Testimonial', 'area', req=1),
    F('photo', 'Photo', 'media'), ORDER, STATUS],
  ['name', 'role', 'order', 'status'], pub=1, ordered=1)
R('sections', 'Homepage sections', 'Homepage', [
    F('key', 'Section type', 'sel', opts=['hero', 'notices', 'courses', 'live', 'teachers', 'posts', 'testimonials', 'banners', 'about', 'contact', 'custom'], req=1),
    F('title', 'Heading'), F('subtitle', 'Subtitle'), F('body', 'Content (about / custom / contact)', 'html'),
    F('count', 'Items to show', 'num', default=6), F('enabled', 'Visible', 'chk', default=True), ORDER],
  ['title', 'key', 'enabled', 'order'], ordered=1, drag=1)
R('courses', 'Courses', 'Courses', [
    F('title', 'Course name', req=1), F('slug', 'URL slug'), F('desc', 'Description', 'html'), F('thumb', 'Thumbnail', 'media'),
    F('price', 'Price (0 = free)', 'num', default=0), F('teacher', 'Teacher', 'ref', ref='teachers'), F('duration', 'Duration'),
    F('feat', 'Featured on homepage', 'chk'), F('publish_at', 'Schedule publishing', 'dt'), F('expires_at', 'Course expiry', 'dt'),
    F('status', 'Status', 'sel', opts=['draft', 'published', 'disabled'], default='draft')],
  ['title', 'price', 'teacher', 'status', 'expires_at'], pub=1, feat=1, ver=1, slug=1, preview='/course/{slug}',
  acts=['lessons', 'enrollments', 'history'])
R('lessons', 'Lessons', 'Courses', [
    F('course', 'Course', 'ref', ref='courses', req=1), F('chapter', 'Chapter', default='Chapter 1'), F('title', 'Lesson title', req=1),
    F('kind', 'Type', 'sel', opts=['video', 'pdf', 'zip', 'link', 'text'], default='video'),
    F('file', 'Uploaded file', 'media'), F('url', 'Or external URL (YouTube etc.)', 'url'), F('body', 'Notes', 'html'),
    F('preview', 'Free preview', 'chk'), ORDER],
  ['title', 'chapter', 'kind', 'course', 'order'], ordered=1, drag=1)
R('teachers', 'Teachers', 'Courses', [
    F('name', 'Name', req=1), F('subject', 'Subject'), F('bio', 'Bio', 'area'), F('photo', 'Photo', 'media'), ORDER, STATUS],
  ['name', 'subject', 'status'], pub=1, ordered=1)
R('enrollments', 'Enrollments', 'Courses', [
    F('student', 'Student', 'ref', ref='students', req=1), F('course', 'Course', 'ref', ref='courses', req=1),
    F('expires_at', 'Access until (optional)', 'dt'), F('status', 'Access', 'sel', opts=['active', 'revoked'], default='active')],
  ['student', 'course', 'status', 'expires_at'], mod='enrollments')
R('live', 'Live classes', 'Live', [
    F('title', 'Title', req=1), F('course', 'Course', 'ref', ref='courses'), F('teacher', 'Teacher', 'ref', ref='teachers'),
    F('kind', 'Platform', 'sel', opts=['youtube', 'google-meet', 'zoom', 'teams', 'other'], default='youtube'),
    F('url', 'Class URL', 'url'), F('start', 'Date & time', 'dt', req=1), F('minutes', 'Duration (min)', 'num', default=60),
    F('thumb', 'Thumbnail', 'media'), F('recording', 'Recording URL', 'url'), F('recording_file', 'Recording file', 'media'),
    F('desc', 'Description', 'area'),
    F('status', 'Status', 'sel', opts=['draft', 'published', 'live', 'ended', 'cancelled'], default='draft')],
  ['title', 'start', 'course', 'status'], pub=1, acts=['attendance', 'endclass', 'cancelclass'])
R('exams', 'Exams', 'Exams', [
    F('title', 'Title', req=1), F('course', 'Course (optional)', 'ref', ref='courses'),
    F('minutes', 'Duration (min)', 'num', default=30), F('negative', 'Negative marking', 'chk'),
    F('neg_mark', 'Fraction of marks deducted', 'num', default=0.25), F('max_attempts', 'Attempts allowed', 'num', default=1),
    F('results_published', 'Results published', 'chk'), STATUS],
  ['title', 'minutes', 'status', 'results_published'], pub=1, acts=['questions', 'results', 'publish_results'])
R('questions', 'Questions', 'Exams', [
    F('exam', 'Exam', 'ref', ref='exams', req=1), F('text', 'Question', 'area', req=1),
    F('options', 'Options (one per line, 2-6)', 'area', req=1), F('answer', 'Correct option number (1 = first)', 'num', req=1, default=1),
    F('marks', 'Marks', 'num', default=1), F('explanation', 'Explanation', 'area'), ORDER],
  ['text', 'exam', 'marks', 'answer'], mod='questions', ordered=1, drag=1)
R('attempts', 'Exam results', 'Exams', [
    F('exam', 'Exam', 'ref', ref='exams'), F('student', 'Student', 'ref', ref='students'),
    F('score', 'Score', 'num'), F('total', 'Total', 'num')],
  ['student', 'exam', 'score', 'total', '_c'], mod='attempts', nocreate=1, noedit=1)
R('students', 'Students', 'Users', [
    F('name', 'Display name', req=1), F('username', 'Username', req=1), F('email', 'Email', 'email'), F('phone', 'Phone'),
    F('photo', 'Profile photo', 'media'), F('password', 'Password', 'pass', create_only=1, req=1),
    F('status', 'Account', 'sel', opts=['active', 'inactive'], default='active')],
  ['name', 'username', 'email', 'status'], store='users', where={'role': 'student'}, defaults={'role': 'student'},
  acts=['detail', 'enrollments', 'reset'], export=1)
R('admins', 'Staff accounts', 'Users', [
    F('name', 'Display name', req=1), F('username', 'Username', req=1), F('email', 'Email', 'email'),
    F('role', 'Role', 'sel', opts=['super', 'admin', 'content', 'course', 'teacher', 'support'], default='admin', req=1),
    F('photo', 'Profile photo', 'media'), F('password', 'Password (min 8)', 'pass', create_only=1, req=1),
    F('status', 'Account', 'sel', opts=['active', 'inactive'], default='active')],
  ['name', 'username', 'role', 'status'], store='users', where={'role': '!student'}, acts=['reset', 'logins'])
R('coupons', 'Coupons', 'Payments', [
    F('code', 'Code', req=1), F('type', 'Type', 'sel', opts=['percent', 'flat'], default='percent'), F('value', 'Value', 'num', req=1),
    F('course', 'Only for course (optional)', 'ref', ref='courses'), F('max_uses', 'Max uses (0 = unlimited)', 'num', default=0),
    F('used', 'Times used', 'num', default=0), F('expires_at', 'Expires', 'dt'), F('active', 'Active', 'chk', default=True)],
  ['code', 'type', 'value', 'used', 'active'], mod='payments')
R('plans', 'Subscription plans', 'Payments', [
    F('name', 'Plan name', req=1), F('price', 'Price', 'num', req=1), F('days', 'Access days', 'num', default=30),
    F('desc', 'Description', 'area'), STATUS],
  ['name', 'price', 'days', 'status'], mod='payments', pub=1)
R('orders', 'Orders & payments', 'Payments', [
    F('student', 'Student', 'ref', ref='students', req=1), F('kind', 'Item type', 'sel', opts=['course', 'plan'], default='course'),
    F('item', 'Item id'), F('title', 'Item name'), F('amount', 'Amount paid', 'num'), F('discount', 'Discount', 'num'),
    F('coupon', 'Coupon'), F('provider', 'Provider', default='manual'), F('txn', 'Transaction / UTR reference'),
    F('status', 'Status', 'sel', opts=['pending', 'paid', 'failed', 'refunded'], default='pending')],
  ['student', 'title', 'amount', 'status', '_c'], mod='payments', acts=['paid', 'refund'], nocreate=1, export=1)
R('enquiries', 'Enquiries', 'Users', [
    F('name', 'Name'), F('contact', 'Contact'), F('msg', 'Message', 'area'), F('handled', 'Handled', 'chk')],
  ['name', 'contact', 'msg', 'handled'], mod='enquiries', nocreate=1, acts=['handled'])
R('folders', 'Folders', 'Media', [F('name', 'Folder name', req=1)], ['name'], mod='media', hidden=1)

# ---- website settings (stored as one JSON document, grouped into tabs) ----
S = lambda g, *a, **k: dict(F(*a, **k), g=g)
SETTINGS = [
    S('General', 'name', 'Academy name'), S('General', 'tagline', 'Tagline'), S('General', 'site_title', 'Website title'),
    S('General', 'site_desc', 'Website description', 'area'), S('General', 'email', 'Contact email', 'email'),
    S('General', 'phone', 'Phone'), S('General', 'addr', 'Address'), S('General', 'tz', 'Time zone offset (minutes from UTC)', 'num'),
    S('General', 'wa', 'WhatsApp number'), S('General', 'ig', 'Instagram URL', 'url'), S('General', 'yt', 'YouTube URL', 'url'),
    S('General', 'fb', 'Facebook URL', 'url'),
    S('Branding', 'logo', 'Website logo', 'media'), S('Branding', 'logo_m', 'Mobile logo', 'media'), S('Branding', 'favicon', 'Favicon', 'media'),
    S('Branding', 'bg_img', 'Website background image', 'media'),
    S('Branding', 'p', 'Primary color', 'color'), S('Branding', 's', 'Secondary color', 'color'), S('Branding', 'a', 'Accent color', 'color'),
    S('Branding', 'bg', 'Page background', 'color'),
    S('Branding', 'font', 'Font family', 'sel', opts=['Manrope', 'Poppins', 'Inter', 'Nunito', 'Playfair Display', 'Roboto', 'Lato']),
    S('Branding', 'btn', 'Button style', 'sel', opts=['rounded', 'pill', 'square']),
    S('Branding', 'splash', 'Show intro splash screen', 'chk'),
    S('Homepage', 'hero_h', 'Homepage heading'), S('Homepage', 'hero_sub', 'Homepage subtitle', 'area'),
    S('Homepage', 'hero_btn', 'Hero button text'), S('Homepage', 'hero_url', 'Hero button link', 'url'),
    S('Header & footer', 'header', 'Header design', 'sel', opts=['light', 'dark', 'gradient']),
    S('Header & footer', 'footer', 'Footer design', 'sel', opts=['dark', 'light', 'gradient']),
    S('Header & footer', 'footer_text', 'Footer text', 'area'), S('Header & footer', 'show_notice_bar', 'Show urgent notice bar', 'chk'),
    S('Courses', 'currency', 'Currency symbol'), S('Courses', 'login_to_view', 'Require login to view course details', 'chk'),
    S('Courses', 'courses_home', 'Courses shown on homepage', 'num'),
    S('Students', 'allow_reg', 'Allow student self-registration', 'chk'), S('Students', 'allow_free', 'Allow instant enrolment in free courses', 'chk'),
    S('Media', 'max_mb', 'Max upload size (MB)', 'num'), S('Media', 'quota_mb', 'Storage quota (MB)', 'num'),
    S('Notifications', 'notices_home', 'Notices shown on homepage', 'num'), S('Notifications', 'comments_moderate', 'Moderate comments before showing', 'chk'),
    S('Notifications', 'notify_email', 'Send enquiries to email', 'email'),
    S('SEO', 'seo_title', 'Default SEO title'), S('SEO', 'seo_desc', 'Default meta description', 'area'),
    S('SEO', 'og_image', 'Social share image', 'media'), S('SEO', 'noindex', 'Ask search engines not to index', 'chk'),
    S('Payments', 'pay_instr', 'Payment instructions shown to students (UPI / bank)', 'area'),
    S('Payments', 'pay_provider', 'Payment provider', 'sel', opts=['manual']),
    S('Security', 'session_min', 'Idle session timeout (minutes)', 'num', sup=1), S('Security', 'max_fail', 'Failed logins before lockout', 'num', sup=1),
    S('Security', 'lock_min', 'Lockout duration (minutes)', 'num', sup=1),
    S('Maintenance', 'maint', 'Maintenance mode (public site offline)', 'chk'), S('Maintenance', 'maint_msg', 'Maintenance message', 'area'),
]
DEFAULT_SETTINGS = dict(
    name='Vijetha Academy', tagline='Learn Today, Lead Tomorrow.', site_title='Vijetha Academy – Learn Today, Lead Tomorrow.',
    site_desc='Live classes, recorded lectures, online exams and course management.', email='hello@vijetha.in', phone='+91 98765 43210',
    addr='Aligarh, Uttar Pradesh', tz=330, wa='', ig='', yt='', fb='', logo='', logo_m='', favicon='', bg_img='',
    p='#6C35C9', s='#35145F', a='#B69CFF', bg='#F8F6FF', font='Manrope', btn='rounded', splash=True,
    hero_h='Learn Today, Lead Tomorrow.', hero_sub='Live classes, recorded lectures, timed exams and progress tracking in one place.',
    hero_btn='Join the academy', hero_url='/register', header='light', footer='dark', footer_text='', show_notice_bar=True,
    currency='₹', login_to_view=False, courses_home=6, allow_reg=True, allow_free=True, max_mb=50, quota_mb=1024,
    notices_home=5, comments_moderate=True, notify_email='', seo_title='', seo_desc='', og_image='', noindex=False,
    pay_instr='Pay by UPI and enter the transaction reference. Access starts once the academy confirms the payment.', pay_provider='manual',
    session_min=60, max_fail=5, lock_min=15, maint=False, maint_msg='We are updating the website. Please check back soon.')

MODS = ['posts', 'comments', 'pages', 'notices', 'sliders', 'banners', 'testimonials', 'sections', 'courses', 'lessons', 'teachers',
        'enrollments', 'live', 'exams', 'questions', 'attempts', 'students', 'admins', 'payments', 'enquiries', 'media', 'settings', 'roles', 'activity', 'backup']
ROLE_LABELS = dict(super='Super Admin', admin='Admin', content='Content Manager', course='Course Manager', teacher='Teacher', support='Support Staff')
_all = lambda *m, p='vcepd': {x: p for x in m}
DEFAULT_ROLES = {
    'admin': {**_all(*[m for m in MODS if m not in ('admins', 'roles', 'backup')]), 'admins': 'v', 'roles': 'v'},
    'content': _all('posts', 'comments', 'pages', 'notices', 'sliders', 'banners', 'testimonials', 'sections', 'media', p='vcep') | {'settings': 'v'},
    'course': _all('courses', 'lessons', 'teachers', 'enrollments', 'live', 'exams', 'questions', 'media', p='vcep') | {'attempts': 'v', 'students': 'v'},
    'teacher': {'courses': 've', 'lessons': 'vce', 'live': 'vce', 'exams': 'vce', 'questions': 'vce', 'attempts': 'v', 'media': 'vc', 'students': 'v', 'enrollments': 'v'},
    'support': {'students': 'vce', 'enrollments': 'vce', 'enquiries': 'vcep', 'payments': 've', 'comments': 'vep', 'notices': 'v', 'attempts': 'v'},
}
