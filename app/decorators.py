# -*- coding: utf-8 -*-

# 如果你想让视图函数只对具有特定权限的用户开放,可以使用自定义的修饰器。

from functools import wraps
from flask import abort
from flask.ext.login import current_user
from .models import Permission

import sys
reload(sys)
sys.setdefaultencoding('utf8')


# 用来检查常规权限的自定义修饰器
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
                # 如果用户不具有指定权限,则返 回 403 错误码,即 HTTP“禁止”错误.所以还要添加一个 403 错误页面
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# 用来检查管理员权限的自定义修饰器
def admin_required(f):
    return permission_required(Permission.ADMINISTER)(f)