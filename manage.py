#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment, HomePage
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand


COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()


# /app/__init__.py里的
# 如果已经定义了环境变量 FLASK_CONFIG,则从中读取配置名;否则使用默认配置。
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
# 初始化 Flask-Script、Flask-Migrate 
manager = Manager(app)
migrate = Migrate(app, db)
 

# 初始化为 Python shell 定义的上下文
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, Permission=Permission, Post=Post)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


# 为了运行单元测试,可以在 manage.py 脚本中添加一个自定义命令。这展示了如何添加 test 命令。
# manager.command 修饰器让自定义命令变得简单。修饰函数名就是命令名,函数的文档字符串会显示在帮助消息中。
@manager.command
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
 

@manager.command
def test(coverage=False):
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


# 启动分析器,在请求分析器的监视下运行程序
@manager.command
# 使用 python manage.py profile 启动程序后,终端会显示每条请求的分析数据,其中包含运行最慢的 25 个函数。--length 选项可以修改报告中显示的函数数量
# 如果指定了--profile-dir 选项,每条请求的分析数据就会保存到指定目录下的一个文件中
def profile(length=25, profile_dir=None):
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length], profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    from flask.ext.migrate import upgrade
    from app.models import Role, User

    # 定义这些函数时考虑到了多次执行的情况,所以即使多次执行也不会产生问题。因此每次安装或升级程序时只需运行 deploy 命令就能完成所有操作。
    # 把数据库迁移到最新修订版本
    upgrade()

    # 创建用户角色
    Role.insert_roles()

    # 让所有用户都关注此用户
    User.add_self_follows()


if __name__ == '__main__':
    manager.run()