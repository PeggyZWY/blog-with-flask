# -*- coding: utf-8 -*-

from flask import Blueprint

import sys
reload(sys)
sys.setdefaultencoding('utf8')


# 通过实例化一个 Blueprint 类对象可以创建蓝本。
# 这个构造函数有两个必须指定的参数: 蓝本的名字和蓝本所在的包或模块。
main = Blueprint('main', __name__)


"""
程序的路由和错误处理程序分别保存在包里的 app/main/views.py 和 app/main/errors.py 模块中
"""
from . import views, errors
from ..models import Permission


"""
在模板中可能也需要检查权限,所以 Permission 类为所有位定义了常量以便于获取。
为了避免每次调用 render_template() 时都多添加一个模板参数,可以使用上下文处理器。
上下文处理器能让变量在所有模板中全局可访问。
"""
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)