# -*- coding: utf-8 -*-

import unittest
from flask import current_app
from app import create_app, db

# 这个测试使用 Python 标准库中的 unittest 包编写.
# setUp() 和 tearDown() 方法分别在各测试前后运行,并且名字以 test_ 开头的函数都作为测试执行。
class BasicsTestCase(unittest.TestCase):
    """
    setUp() 方法尝试创建一个测试环境,类似于运行中的程序。
    首先,使用测试配置创建程 序,然后激活上下文。
    这一步的作用是确保能在测试中使用 current_app,像普通请求一 样。
    然后创建一个全新的数据库,以备不时之需。
    """
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()


    # 数据库和程序上下文在 tearDown() 方法 中删除。
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # 名字以 test_ 开头的函数都作为测试执行
    # 第一个测试确保程序实例存在
    def test_app_exists(self):
        self.assertFalse(current_app is None)

    # 第二个测试确保程序在测试配置中运行
    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
