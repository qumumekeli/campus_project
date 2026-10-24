# init_db.py（仅账号创建部分修正）
from werkzeug.security import generate_password_hash
from app import create_app
from models import db, User, Category


def init_db():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        categories = [
            {'name': '校内美食', 'description': '校内食堂、小吃、饮品等', 'icon': 'food', 'sort_order': 1},
            {'name': '周边美食/夜市', 'description': '学校周边餐厅、夜市、小吃街等', 'icon': 'night-market', 'sort_order': 2},
            {'name': '游玩打卡', 'description': '校园及周边景点、拍照打卡地', 'icon': 'camera', 'sort_order': 3},
            {'name': '安静自习', 'description': '图书馆、自习室、安静学习空间', 'icon': 'book', 'sort_order': 4},
            {'name': '休闲放松', 'description': '咖啡厅、公园、运动场所等', 'icon': 'coffee', 'sort_order': 5},
            {'name': '生活服务', 'description': '超市、快递、理发、维修等', 'icon': 'service', 'sort_order': 6},
        ]
        for c in categories:
            db.session.add(Category(**c))

        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            nickname='管理员',
            cohort='2024 级',
            role='admin',
            status=1
        )
        student = User(
            username='test',
            password_hash=generate_password_hash('test123'),
            nickname='测试学生',
            cohort='2024 级',
            role='student',
            status=1
        )
        db.session.add_all([admin, student])
        db.session.commit()

        print('Database initialized successfully!')
        print('Categories:', len(categories))
        print('Admin: admin / admin123')
        print('Student: test / test123')


if __name__ == '__main__':
    init_db()