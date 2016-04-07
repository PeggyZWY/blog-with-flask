# -*- coding: utf-8 -*-

import re
import unittest
from flask import url_for
from app import create_app, db
from app.models import User, Role


class FlaskClientTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        """
        实例变量 self.client 是 Flask 测试客户端对象。在这个对象上可调用方法向程序发起请求。
        如果创建测试客户端时启用了 use_cookies 选项,这个测试客户端就能像浏览器一样接收和发送 cookie,
        因此能使用依赖 cookie 的功能记住请求之间的上下文。这个选项可用来启用用户会话,让用户登录和退出。
        """
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        # 客户端向首页发起了一个请求。在测试客户端上调用 get() 方法得到的结果是一个 FlaskResponse 对象,内容是调用视图函数得到的响应。
        response = self.client.get(url_for('main.index'))
        # 响应主体可使用 response.data 获取
        # self.assertTrue(b'Stranger' in response.data)

    def test_register_and_login(self):
        # 注册新账户
        # post() 方法的 data 参数是个字典,包含表单中的各个字段,各字段的名字必须严格匹配定义表单时使用的名字。
        # 由于 CSRF 保护已经在测试配置中禁用了,因此无需和表单数据一起发送。
        response = self.client.post(url_for('auth.register'), data={
            'email': 'jerry@163.com',
            'username': 'jerry',
            'password': 'jerry',
            'password2': 'jerry'
        })
        # self.assertTrue(response.status_code == 200)

        # 用新注册的账户登录
        # 指定了参数 follow_ redirects=True,让测试客户端和浏览器一样,自动向重定向的 URL 发起 GET 请求。
        # 指定这个参数后,返回的不是 302 状态码,而是请求重定向的 URL 返回的响应。
        response = self.client.post(url_for('auth.login'), data={
            'email': 'jerry@163.com',
            'password': 'jerry'
        }, follow_redirects=True)
        # 直接搜索字符串 'Hello, john!' 并没有用,因为这个字符串由动态部分和静 态部分组成,而且两部分之间有额外的空白。
        # 为了避免测试时空白引起的问题,我们使用更为灵活的正则表达式。
        # self.assertTrue(re.search(b'Hello,\s+jerry!', response.data))
        # self.assertTrue(b'You have not confirmed your account yet' in response.data)

        # 发送确认令牌，使用确认令牌确认账户
        user = User.query.filter_by(email='jerry@163.com').first()
        # token = user.generate_confirmation_token()
        # response = self.client.get(url_for('auth.confirm', token=token), follow_redirects=Trus)
        # self.assertTrue(b'You have confirmed your account' in response.data)
        
        # 退出
        response = self.client.get(url_for('auth.logout'), follow_redirects=True)
        # self.assertTrue(b'You have been logged out' in response.data)



