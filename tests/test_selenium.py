# -*- coding: utf-8 -*-

import re
import threading
import time
import unittest
from selenium import webdriver
from app import create_app, db
from app.models import Role, User, Post


# 使用 Selenium 运行测试的框架
# setUpClass() 和 tearDownClass() 类方法分别在这个类中的全部测试运行前、后执行。
# setUp() 方法在每个测试运行之前执行,如果 Selenium 无法利用 startUpClass() 方法启动 Web 浏览器就跳过测试。
class SeleniumTestCase(unittest.TestCase):
    client = None

    @classmethod
    def setUpClass(cls):
        # 启动 Firefox
        try:
            cls.client = webdriver.Firefox()
        except:
            pass

        # 如果无法启动浏览器,则跳过这些测试
        if cls.client:
            # 创建程序
            cls.app = create_app('testing')
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # 禁止日志,保持输出简洁
            import logging
            logger = logging.getLogger('werkzeug')
            logger.setLevel('ERROR')

            # 创建数据库,并使用一些虚拟数据填充
            db.create_all()
            Role.insert_roles()
            User.generate_fake(10)
            Post.generate_fake(10)

            # 添加管理员
            admin_role = Role.query.filter_by(permissions=0xff).first()
            admin = User(email='jerry@163.com',
                         username='jerry', password='jerry',
                         role=admin_role)
            db.session.add(admin)
            db.session.commit()

            # 在一个线程中启动 Flask 服务器
            threading.Thread(target=cls.app.run).start()

            # 给服务器 1s 时间保证已经启动
            time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # 关闭 Flask 服务器和浏览器
            cls.client.get('http://localhost:5000/shutdown')
            cls.client.close()

            # 销毁数据库
            db.drop_all()
            db.session.remove()

            # 删除程序上下文
            cls.app_context.pop()

    def setUp(self):
        if not self.client:
            self.skipTest('Web browser not available')

    def tearDown(self):
        pass

    """
    注意, 这里使用的测试方法和使用 Flask 测试客户端时不一样。
    使用 Selenium 进行测试时,测试向 Web 浏览器发出指令且从不直接和程序交互。
    发给浏览器的指令和真实用户使用鼠标或键盘执行的操作几乎一样。
    """
    def test_admin_home_page(self):
        # 进入首页
        self.client.get('http://localhost:5000/')
        # self.assertTrue(re.search('Hello, \s+Stranger!', self.client.page_source))

        # 进入登录页面
        """
        为了访问登录页面,测试使用find_element_by_link_text()方法在页面源码里查找“LOG IN / REGISTER”链接。
        在这个链接上调用 click() 方法,从而在浏览器中触发一次真正的点击。
        Selenium 提供 了很多 find_element_by...() 简便方法,可使用不同的方式搜索元素。
        """
        self.client.find_element_by_link_text('LOG IN / REGISTER').click()
        self.assertTrue('<h1>登陆</h1>' in self.client.page_source)

        # 登录
        # 使用 send_keys() 方法在各字段中填入值。
        # 表单的提交通过在提交按钮上调用 click() 方法完成。
        self.client.find_element_by_name('email').send_keys('jerry@163.com')
        self.client.find_element_by_name('password').send_keys('jerry')
        self.client.find_element_by_name('submit').click()
        # self.assertTrue(re.search('Hello, \s+john!', self.client.page_source))

        # 进入用户个人资料页面
        self.client.find_element_by_link_text('PROFILE').click()
        # self.assertTrue('<h1>jerry</h1>' in self.client.page_source)




