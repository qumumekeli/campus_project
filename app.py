import os
import uuid
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User, Category, Place

app = Flask(__name__)
app.config.from_object(Config)

# 上传配置
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# 工具函数
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapped

# 首页
@app.route('/')
def index():
    places = Place.query.filter_by(status='approved').all()
    return render_template('index.html', places=places)

# 注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        nickname = request.form.get('nickname', '').strip()
        cohort = request.form.get('cohort', '').strip()

        if not username or not password or not nickname or not cohort:
            flash('所有字段均为必填项', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return redirect(url_for('register'))

        # 修正 1：使用正确的字段名和加密方式
        user = User(
            username=username, 
            password_hash=generate_password_hash(password),
            nickname=nickname,
            cohort=cohort,
            role='student',
            status=1
        )
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        # 修正 2：使用正确的密码校验方式
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['nickname'] = user.nickname
            session['role'] = user.role
            flash('登录成功', 'success')
            return redirect(url_for('index'))

        flash('用户名或密码错误', 'danger')

    return render_template('login.html')

# 退出登录
@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

# 添加地点推荐
@app.route('/add_place', methods=['GET', 'POST'])
@login_required
def add_place():
    if request.method == 'GET':
        categories = Category.query.all()
        return render_template('add_place.html', categories=categories)

    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id', type=int)
    scope = request.form.get('scope', '').strip()
    address = request.form.get('address', '').strip()
    description = request.form.get('description', '').strip()
    reason = request.form.get('reason', '').strip()  # 修正 3
    cost_level = request.form.get('cost_level', '').strip()
    duration_level = request.form.get('duration_level', '').strip() # 修正 4
    tags = request.form.get('tags', '').strip()

    if not name:
        flash('名称不能为空', 'danger')
        return redirect(url_for('add_place'))

    cover_image_url = None
    file = request.files.get('cover_image')
    if file and file.filename:
        if not allowed_file(file.filename):
            flash('图片格式仅支持 jpg / jpeg / png / webp', 'danger')
            return redirect(url_for('add_place'))

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        
        # 数据库里存相对路径
        cover_image_url = f"/static/uploads/{filename}" # 修正 5

    place = Place(
        name=name,
        category_id=category_id,
        scope=scope,
        address=address,
        description=description,
        reason=reason, # 修正 6
        cost_level=cost_level,
        duration_level=duration_level, # 修正 7
        tags=tags,
        cover_image_url=cover_image_url, # 修正 8
        author_id=session['user_id'],
        status='pending',
    )
    db.session.add(place)
    db.session.commit()

    flash('提交成功，等待审核', 'success')
    return redirect(url_for('index'))

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('图片大小不能超过 5MB', 'danger')
    return redirect(url_for('add_place'))

if __name__ == '__main__':
    app.run(debug=True)