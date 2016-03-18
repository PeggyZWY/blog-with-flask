# -*- coding: utf-8 -*-
 
# 把创建程序实例的过程移到可显式调用的工厂函数中
# 这种方法不仅可以给脚本留出配置程序的时间,还能够创建多个程序实例,这些实例有时在测试中非常有用。

# 构造文件导入了大多数正在使用的 Flask 扩展
from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.mail import Mail
from flask.ext.moment import Moment
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.pagedown import PageDown
# 配置类在 config.py 文件中定义
from config import config

import sys
reload(sys)
sys.setdefaultencoding('utf8')


# 由于尚未初始化所需的程序实例,所以没有初始化扩展,创建扩展类时没有向构造函数传入参数
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

login_manager = LoginManager()
# LoginManager 对象的 session_protection 属性可以设为 None、'basic' 或 'strong'
# 设为 'strong' 时,Flask-Login 会记录客户端 IP 地址和浏览器的用户代理信息,如果发现异动就登出用户
login_manager.session_protection = 'strong'
# login_view 属性设置登录页面的端点。登录路由在蓝本中定义,因此要在前面加上蓝本的名字
login_manager.login_view = 'auth.login'


# create_app() 函数就是程序的工厂函数,接受一个参数,是程序使用的配置名。
def create_app(config_name):
    app = Flask(__name__)
    # 配置类在 config.py 文件中定义,其中保存的配置可以使用Flask app.config配置对象提供的from_object()方法直接导入程序
    # 至于配置对象,则可以通过名字从 config 字典中选择
    app.config.from_object(config[config_name])
    # 程序创建并配置好后,就能初始化扩展了
    config[config_name].init_app(app)

    # 在之前创建的扩展对象上调用 init_app() 可以完成初始化过程。
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)


    # 还有附加路由和自定义的错误页面，下一节讲
    """
    现在程序在运行时创建,只 有调用 create_app() 之后才能使用 app.route 修饰器,这时定义路由就太晚了
    所以 Flask 用蓝本解决.
    为了获得最大的灵活性,程序包中创建了一个子包,用于保存蓝本.
    所以到app/main/__init__.py那里去了，但实际上还是__init__.py.
    所以这里把它import进来
    """ 
    from .main import main as main_blueprint
    # 在蓝本中定义的路由处于休眠状态,直到蓝本注册到程序上后,路由才真正成为程序的一部分。
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    # 注册蓝本时使用的 url_prefix 是可选参数。如果使用了这个参数,注册后蓝本中定义的所有路由都会加上指定的前缀
    
    # 工厂函数返回创建的程序示例
    return app
