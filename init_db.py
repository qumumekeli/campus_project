from app import app, db
from models import User, Category
from werkzeug.security import generate_password_hash

def init_db():
    # 进入 Flask 的上下文环境
    with app.app_context():
        # 删除现有的所有表（这样重新建就不会冲突）
        db.drop_all()
        # 根据最新的 models.py 重新建表
        db.create_all()

        # 初始化 6 个分类
        categories = [
            {'name': '校内美食', 'description': '校内食堂、小吃等', 'icon': 'food', 'sort_order': 1},
            {'name': '周边美食/夜市', 'description': '学校周边餐厅、夜市等', 'icon': 'night-market', 'sort_order': 2},
            {'name': '游玩打卡', 'description': '校园及周边景点', 'icon': 'camera', 'sort_order': 3},
            {'name': '安静自习', 'description': '图书馆、自习室', 'icon': 'book', 'sort_order': 4},
            {'name': '休闲放松', 'description': '咖啡厅、公园等', 'icon': 'coffee', 'sort_order': 5},
            {'name': '生活服务', 'description': '超市、快递、理发等', 'icon': 'service', 'sort_order': 6}
        ]
        for c in categories:
            db.session.add(Category(**c))

        # 初始化管理员账号
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            nickname='管理员',
            cohort='2024级',
            role='admin',
            status=1
        )
        
        # 初始化测试学生账号
        student = User(
            username='test',
            password_hash=generate_password_hash('test123'),
            nickname='测试学生',
            cohort='2024级',
            role='student',
            status=1
        )
        
        db.session.add_all([admin, student])
        db.session.commit()

        print("========================================")
        print("Database initialized successfully!")
        print("Categories: 6")
        print("Admin: admin / admin123")
        print("Student: test / test123")
        print("========================================")

if __name__ == '__main__':
    init_db()