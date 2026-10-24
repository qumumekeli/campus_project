from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from config import Config  # 👈 关键：引入之前的配置文件

app = Flask(__name__)
app.config.from_object(Config)  # 👈 关键：让 app 使用之前的配置，连上同一个数据库

# 初始化数据库（关联已存在的 campus.db）
db.init_app(app)


# ============ 首页 ============

# ============ 首页 ============
@app.route('/')
def index():
    return render_template('index.html')


# ============ 注册 ============
@app.route('/register', methods=['GET', 'POST'])
def register():
    # 已登录用户直接跳首页
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        nickname = request.form.get('nickname', '').strip()
        cohort = request.form.get('cohort', '').strip()

        # 基础校验
        if not username or not password or not nickname or not cohort:
            flash('所有字段均为必填项', 'danger')
            return render_template('register.html')

        # 用户名唯一性校验
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('该用户名已被注册，请更换一个', 'danger')
            return render_template('register.html')

        # 创建用户（密码加密存储）
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            nickname=nickname,
            cohort=cohort,
            role='student',   # 默认角色
            status=1          # 1 代表正常（Integer 类型）
        )
        db.session.add(new_user)
        db.session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# ============ 登录 ============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        # 用户不存在 或 密码错误
        if user is None or not check_password_hash(user.password_hash, password):
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')

        # 状态校验（status 为 Integer，1 代表正常）
        if user.status != 1:
            flash('该账号当前不可用，请联系管理员', 'warning')
            return render_template('login.html')

        # 写入 session
        session['user_id'] = user.id
        session['username'] = user.username
        session['nickname'] = user.nickname
        session['role'] = user.role

        flash(f'欢迎回来，{user.nickname}！', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


# ============ 退出登录 ============
@app.route('/logout')
def logout():
    session.clear()
    flash('你已退出登录', 'info')
    return redirect(url_for('index'))


# ============ 上下文处理器：让所有模板都能用 current_user ============
@app.context_processor
def inject_user():
    return dict(
        current_user={
            'id': session.get('user_id'),
            'username': session.get('username'),
            'nickname': session.get('nickname'),
            'role': session.get('role'),
        } if session.get('user_id') else None
    )


if __name__ == '__main__':
    app.run(debug=True)