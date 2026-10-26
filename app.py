from sqlalchemy import func
import os
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User, Category, Place, Like, Favorite,Comment

app = Flask(__name__)
app.config.from_object(Config)

# 上传配置
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# 工具函数
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('你没有权限访问该页面', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_user():
    return dict(current_user={
        'id': session.get('user_id'),
        'username': session.get('username'),
        'nickname': session.get('nickname'),
        'role': session.get('role'),
        'cohort': session.get('cohort')
    } if session.get('user_id') else None)

# ==================== 首页 ====================
@app.route('/')
def index():
    keyword = request.args.get('keyword', '').strip()
    category_id = request.args.get('category_id', '').strip()
    scope = request.args.get('scope', '').strip()
    sort_by = request.args.get('sort_by', 'newest')

    query = Place.query.filter_by(status='approved')

    # 搜索与过滤（保留你之前的完美逻辑）
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(db.or_(Place.name.like(like), Place.description.like(like)))

    if category_id:
        try:
            query = query.filter(Place.category_id == int(category_id))
        except ValueError:
            pass

    if scope in ('campus', 'nearby', 'city'):
        query = query.filter(Place.scope == scope)

    # 排序逻辑（新增热度）
    if sort_by == 'hot':
        query = query.order_by(Place.favorite_count.desc(), Place.like_count.desc())
    else:
        sort_by = 'newest'
        query = query.order_by(Place.id.desc())

    places = query.all()
    top_recommended = (
        db.session.query(Place.name, func.count(Place.id).label('count'))
        .filter(Place.status == 'approved')
        .group_by(Place.name)
        .order_by(func.count(Place.id).desc())
        .limit(5)
        .all()
    )
    categories = Category.query.all()

    return render_template(
        'index.html',
        places=places,
        categories=categories,
        keyword=keyword,
        selected_category_id=category_id,
        selected_scope=scope,
        sort_by=sort_by,
        top_recommended=top_recommended
    )

# ==================== 登录注册 ====================
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

        user = User(username=username, password_hash=generate_password_hash(password), nickname=nickname, cohort=cohort, role='student', status=1)
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['nickname'] = user.nickname
            session['role'] = user.role
            session['cohort'] = user.cohort
            flash('登录成功', 'success')
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

# ==================== 添加推荐 ====================
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
    reason = request.form.get('reason', '').strip()
    cost_level = request.form.get('cost_level', '').strip()
    duration_level = request.form.get('duration_level', '').strip()
    tags = request.form.get('tags', '').strip()

    if not name:
        flash('名称不能为空', 'danger')
        return redirect(url_for('add_place'))

    cover_image_url = None
    file = request.files.get('cover_image')
    if file and file.filename:
        if allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_image_url = f"/static/uploads/{filename}"

    place = Place(name=name, category_id=category_id, scope=scope, address=address, description=description, reason=reason, cover_image_url=cover_image_url, cost_level=cost_level, duration_level=duration_level, tags=tags, author_id=session['user_id'], status='pending')
    db.session.add(place)
    db.session.commit()
    flash('提交成功，等待审核', 'success')
    return redirect(url_for('index'))

# ==================== 管理员审核 ====================
@app.route('/admin/review')
@login_required
@admin_required
def admin_review():
    places = Place.query.filter_by(status='pending').order_by(Place.id.desc()).all()
    return render_template('admin_review.html', places=places)

@app.route('/admin/approve/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_approve(id):
    place = db.session.get(Place, id)
    if place:
        place.status = 'approved'
        place.published_at = datetime.utcnow()
        db.session.commit()
        flash(f'已通过: {place.name}', 'success')
    return redirect(url_for('admin_review'))

@app.route('/admin/reject/<int:id>', methods=['POST'])
@login_required
@admin_required  # 别忘了管理员校验
def admin_reject(id):
    place = db.session.get(Place, id)
    if not place: abort(404)
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('必须填写驳回理由', 'danger')
        return redirect(url_for('admin_review'))
        
    place.status = 'rejected'
    place.reject_reason = reason
    db.session.commit()
    flash(f'已驳回: {place.name}', 'info')
    return redirect(url_for('admin_review'))
# ==================== 地点详情 ====================
@app.route('/place/<int:id>')
def place_detail(id):
    place = db.session.get(Place, id)
    if not place: abort(404)
    
    is_liked = False
    is_favorited = False
    if 'user_id' in session:
        uid = session['user_id']
        is_liked = Like.query.filter_by(user_id=uid, place_id=id).first() is not None
        is_favorited = Favorite.query.filter_by(user_id=uid, place_id=id).first() is not None

    # 👇 新增这两行，查出作者和分类的真实名字
    author = db.session.get(User, place.author_id)
    category = db.session.get(Category, place.category_id)
    comments = Comment.query.filter_by(place_id=place.id, parent_id=None).order_by(Comment.created_at.desc()).all()
    # 👇 注意这里把 author 和 category 也传过去
    return render_template('detail.html', place=place, is_liked=is_liked, is_favorited=is_favorited, comments=comments, author=author, category=category)
# ==================== 点赞 ====================
@app.route('/toggle_like/<int:id>')
@login_required
def toggle_like(id):
    place = db.session.get(Place, id)
    if not place: abort(404)

    uid = session['user_id']
    existing = Like.query.filter_by(user_id=uid, place_id=id).first()

    if existing:
        db.session.delete(existing)
        place.like_count = max(0, (place.like_count or 0) - 1)
        flash('已取消点赞', 'info')
    else:
        db.session.add(Like(user_id=uid, place_id=id))
        place.like_count = (place.like_count or 0) + 1
        flash('点赞成功', 'success')
    db.session.commit()
    return redirect(request.referrer or url_for('place_detail', id=id))

# ==================== 收藏 ====================
@app.route('/toggle_favorite/<int:id>')
@login_required
def toggle_favorite(id):
    place = db.session.get(Place, id)
    if not place: abort(404)

    uid = session['user_id']
    existing = Favorite.query.filter_by(user_id=uid, place_id=id).first()

    if existing:
        db.session.delete(existing)
        place.favorite_count = max(0, (place.favorite_count or 0) - 1)
        flash('已取消收藏', 'info')
    else:
        db.session.add(Favorite(user_id=uid, place_id=id))
        place.favorite_count = (place.favorite_count or 0) + 1
        flash('收藏成功', 'success')
    db.session.commit()
    return redirect(request.referrer or url_for('place_detail', id=id))

# ==================== 我的收藏 ====================
@app.route('/my_favorites')
@login_required
def my_favorites():
    uid = session['user_id']
    # 联合查询，只找审核通过的
    places = db.session.query(Place).join(Favorite, Favorite.place_id == Place.id).filter(Favorite.user_id == uid, Place.status == 'approved').all()
    return render_template('my_favorites.html', places=places)
@app.route('/profile')
@login_required
def profile():
    # 从 session 里拿用户 id
    uid = session.get('user_id')
    places = Place.query.filter_by(author_id=uid).order_by(Place.created_at.desc()).all()
    return render_template('profile.html', places=places)

@app.route('/add_comment/<int:id>', methods=['POST'])
@login_required
def add_comment(id):
    place = Place.query.get_or_404(id)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)

    if content:
        comment = Comment(
            place_id=place.id,
            user_id=session.get('user_id'), # 改用 session 获取
            content=content,
            parent_id=parent_id if parent_id else None
        )
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('place_detail', id=place.id))
@app.route('/edit_place/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_place(id):
    place = db.session.get(Place, id)
    if not place: abort(404)
    if place.author_id != session.get('user_id'):
        flash('无权编辑该地点', 'danger')
        return redirect(url_for('profile'))

    categories = Category.query.all()

    if request.method == 'POST':
        # 把字段全部更新
        place.name = request.form.get('name', '').strip()
        place.category_id = request.form.get('category_id', type=int)
        place.scope = request.form.get('scope', '').strip()
        place.address = request.form.get('address', '').strip()
        place.description = request.form.get('description', '').strip()
        place.reason = request.form.get('reason', '').strip()
        place.cost_level = request.form.get('cost_level', '').strip()
        place.duration_level = request.form.get('duration_level', '').strip()
        place.tags = request.form.get('tags', '').strip()
        
        # 处理新图片上传（如果用户选了新图）
        file = request.files.get('cover_image')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            place.cover_image_url = f"/static/uploads/{filename}"

        place.status = 'pending'
        place.reject_reason = None
        db.session.commit()
        flash('已重新提交，等待管理员审核', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_place.html', place=place, categories=categories)

@app.route('/place/delete/<int:id>', methods=['POST'])
@login_required
def place_delete(id):
    place = db.session.get(Place, id)
    if not place: abort(404)

    # 判断权限：作者本人或管理员
    if place.author_id != session.get('user_id') and session.get('role') != 'admin':
        flash('无权操作', 'danger')
        return redirect(url_for('index'))

    reason = request.form.get('reason', '').strip() or '作者自行删除'

    place.is_deleted = 1
    place.status = 'offline'
    place.reject_reason = reason
    db.session.commit()
    
    flash('地点已删除', 'info')
    return redirect(request.referrer or url_for('index'))

@app.route('/admin/manage')
@login_required
@admin_required
def admin_manage():
    places = Place.query.filter_by(status='approved', is_deleted=0).order_by(Place.id.desc()).all()
    return render_template('admin_manage.html', places=places)

if __name__ == '__main__':
    app.run(debug=True)