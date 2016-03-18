# -*- coding: utf-8 -*-

from flask import Blueprint

import sys
reload(sys)
sys.setdefaultencoding('utf8')


"""
把创建程序的过程移入工厂函数后,可以使用蓝本在全局作用域中定义路由。
与用户认证系统相关的路由可在 auth 蓝本中定义。
对于不同的程序功能, 我们要使用不同的蓝本,这是保持代码整齐有序的好方法。
"""
# auth 蓝本保存在同名 Python 包中。蓝本的包构造文件创建蓝本对象
auth = Blueprint('auth', __name__)


# 从 views.py 模块 中引入路由
from . import views

# 别忘了现在这个auth 蓝本要在 app/__init__.py 里的create_app() 工厂函数中附加到程序上