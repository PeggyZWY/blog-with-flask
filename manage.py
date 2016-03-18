#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from app import create_app, db
from app.models import User, Role, Permission, Post
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand


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
 
    
if __name__ == '__main__':
    manager.run()