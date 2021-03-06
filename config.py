# -*- coding: utf-8 -*-
 
import os
basedir = os.path.abspath(os.path.dirname(__file__))  # 出现在 SQLALCHEMY_DATABASE_URI 里

# 不再使用 hello.py 中简单的字典状结构配置,而使用层次结构的配置类
class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    # 每次request自动提交db.session.commit()
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = 'smtp.qq.com'
    # 163服务器端口号: http://help.163.com/10/1111/15/6L7HMASV00753VB8.html
    MAIL_PORT = 465
    MAIL_USE_SSL = True 
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')    
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    FLASKY_MAIL_SUBJECT_PREFIX = '[Blog of Wenyi Zhao]'
    FLASKY_MAIL_SENDER = 'YIYI'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
    FLASKY_POSTS_PER_PAGE = 10
    FLASKY_FOLLOWERS_PER_PAGE = 20
    FLASKY_COMMENTS_PER_PAGE = 10
    # SQLALCHEMY_RECORD_QUERIES 告诉 Flask-SQLAlchemy 启用记录查询统计数字的功能。
    # 缓慢查询的阈值设为 0.5 秒。这两个配置变量都在 Config 基类中设置,因此在所有环境中都可使用。
    SQLALCHEMY_RECORD_QUERIES = True
    FLASKY_SLOW_DB_QUERY_TIME = 0.5

    """
    配置类可以定义 init_app() 类方法,其参数是程序实例。在这个方法中,可以执行对当前环境的配置初始化。
    现在,基类 Config 中的 init_app() 方法为空。
    """
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    WTF_CSRF_ENABLED = False 


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    """
    在 tests/test_client.py 中,测试客户端还能使用 post() 方法发送包含表单数据的 POST 请求,不过提交表单时会有一 个小麻烦。
    Flask-WTF 生成的表单中包含一个隐藏字段,其内容是 CSRF 令牌,需要和表单中的数据一起提交。
    为了复现这个功能,测试必须请求包含表单的页面,然后解析响应返回的 HTML 代码并提取令牌,这样才能把令牌和表单中的数据一起发送。
    为了避免在测试中处理 CSRF 令牌这一烦琐操作,最好在测试配置中禁用 CSRF 保护功能
    """

    """
    所有配置实例都有一个 init_app() 静态方法,在 create_app() 方法中调用。
    在 ProductionConfig 类的 init_app() 方法的实现中,配置程序的日志记录器把错误写入电子 邮件日志记录器。
    电子邮件日志记录器的日志等级被设为 logging.ERROR,所以只有发生严重错误时才会发送电子邮件。
    通过添加适当的日志处理程序,可以把较轻缓等级的日志消息写入文件、系统日志或其他的支持方法。
    这些日志消息的处理方法很大程度上依赖于程序使用的托管平台。
    """
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_SSL', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.FLASKY_MAIL_SENDER,
            toaddrs=[cls.FLASKY_ADMIN],
            subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + 'Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # 输出到 stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)


# config 字典中注册了不同的配置环境
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig 
}

"""
基类 Config 中包含通用配置,子类分别定义专用的配置。

开发，测试，生产

在 3 个子类中,SQLALCHEMY_DATABASE_URI 变量都被指定了不同的值。
这样程序就可在不同的配置环境中运行,每个环境都使用不同的数据库。
"""
