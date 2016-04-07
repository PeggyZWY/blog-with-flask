# -*- coding: utf-8 -*-

# 分别用在注册用户和验证用户阶段
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app
from flask.ext.login import UserMixin, AnonymousUserMixin
from . import db, login_manager
from datetime import datetime
import hashlib

import sys
reload(sys)
sys.setdefaultencoding('utf8')


class Permission(object):
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'  # 开始忘了写表名了。表名规定用复数
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    # 只有一个角色的 default 字段要设为 True,其他都设为 False。用户注册时,其角色会被设为默认角色。
    default = db.Column(db.Boolean, default=False, index=True)
    # permissions 字段的值是一个整数,表示位标志。各操作都对应一个位位置,能执行某项操作的角色,其位会被设为 1。
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')
    # 加入了lazy = 'dynamic'参数,从而禁止自动执行查询
    # 这样配置关系之后,user_role.users 会返回一个尚未执行的查询,因此可以在其上添加过滤器
    
    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()
        """
        insert_roles() 函数并不直接创建新角色对象,而是通过角色名查找现有的角色,然后再进行更新。
        只有当数据库中没有某个角色名时才会创建新角色对象。如此一来,如果以后更新了角色列表,就可以执行更新操作了。
        要想添加新角色,或者修改角色的权限,修改 roles 数组,再运行函数即可。
        注意,“匿名”角色不需要在数据库中表示出来,这个角色的作用就是为了表示不在数据库中的用户。
        """

    def __repr__(self):
        return '<Role %r>' % self.name


"""
使用多对多关系时,往往需要存储所联两个实体之间的额外信息.这种信息只能存储在关联表中.
但关联表若是默认的完全是由 SQLAlchemy 掌控的内部表，就做不到。
为了能在关系中处理自定义的数据,我们必须提升关联表的地位,使其变成程序可访问的模型。

换句话说：因为如果是 SQLAlchemy 默认掌控的内部表，就不能自己再另外添加什么关系。
而现在我们需要timestamp这个自定义字段，所以只有舍弃关联表了，要为Follow造一个模型。
"""
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # 在这个程序中,用户使用电子邮件地址登录
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    # 由于模型中新加入了一个列用来保存账户的确认状态,因此要生成并执行一个新数据库迁移。
    # confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    # db.String 和 db.Text 的区别在于后者不需要指定最大长度
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    """
    两个时间戳的默认值都是当前时间。
    注意,datetime.utcnow 后面没有 (),因为 db.Column() 的 default 参数可以接受函数作为默认值,
    所以每次需要生成默认值时,db.Column() 都会调用指定的函数。member_since 字段只需要默认值即可。
    """
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    """
    SQLAlchemy 不能直接使用Follow这个模型,因为如果这么做程序就无法访问其中的自定义字段。
    相反地,要把这个多对多关系的左右两侧拆分成两个基本的一对多关系,而且要定义成标准的关系
    在这段代码中,followed 和 followers 关系都定义为单独的一对多关系
    """
    # 为了消除外键间的歧义,定义关系时必须使用可选参数 foreign_keys 指定的外键。
    # db.backref() 参数并不是指定这两个关系之间的引用关系,而是回引 Follow 模型。
    """
    回引中的 lazy 参数指定为 joined。这个 lazy 模式可以实现立即从联结查询中加载相关对象

    例如,如果某个用户关注了 100 个用户,调用 user.followed.all() 后会返回一个列表,
    其中包含 100 个 Follow 实例,每一个实例的 follower 和 followed 回引属性都指向相应的用户。
    设定为 lazy='joined' 模式,就可在一次数据库查询中完成这些操作。
    如果把 lazy 设为默认值 select,那么首次访问 follower 和 followed 属性时才会加载对应的用户, 
    而且每个属性都需要一个单独的查询,这就意味着获取全部被关注用户时需要增加 100 次额外的数据库查询。
    """
    # lazy 参数都在“一”这一侧设定, 返回的结果是“多”这一侧中的记录。使用dynamic则关系属性不会直接返回记录,而是返回查询对象,所以在执行查询之前还可以添加额外的过滤器。
    """
    cascade 参数配置在父对象上执行的操作对相关对象的影响。
    比如,层叠选项可设定为: 将用户添加到数据库会话后,要自动把所有关系的对象都添加到会话中。
    层叠选项的默认值能满足大多数情况的需求,但对这个多对多关系来说却不合用。
    删除对象时,默认的层叠行为是把对象联接的所有相关对象的外键设为空值。
    但在关联表中,删除记录后正确的行为应该是把指向该记录的实体也删除,因为这样能有效销毁联接。这就是层叠选项值 delete-orphan 的作用。
    
    cascade 参数的值是一组由逗号分隔的层叠选项.all 表示除了 delete-orphan 之外的所有层叠选项。
    设为 all, delete-orphan 的意思是启用所有默认层叠选项,而且还要删除孤儿记录。
    """
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    # 为了完成对数据库的修改,User 和 Post 模型还要建立与 comments 表的一对多关系
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # 添加到 User 模型中的类方法,用来生成虚拟数据
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            # 这些虚拟对象的属性由 ForgeryPy 的随机信息生成器生成,其中的名字、电子邮件地址、句子等属性看起来就像真的一样
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     # confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            # ForgeryPy 随机生成这些信息,因此有重复的风险
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # 这个异常的处理方式是,在继续操作之前回滚会话。在循环中生成重复内容时不会把用户写入数据库,因此生成的虚拟用户总数可能会比预期少

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        # User 类的构造函数首先调用基类的构造函数,如果创建基类对象后还没定义角色,则根据电子邮件地址决定将其设为管理员还是默认角色。
        super(User, self).__init__(**kwargs)
        if self.email == current_app.config['FLASKY_ADMIN']:
            self.role = Role.query.filter_by(permissions=0xff).first()
            self.role = Role(permissions=0xff)
            self.role_id = 2
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
                self.role = Role(permissions=0xff)
                self.role_id = 2
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        self.followed.append(Follow(followed=self))

    """
    Python内置的@property装饰器就是负责把一个方法变成属性调用的.

    我们在对实例属性操作的时候，就知道该属性很可能不是直接暴露的，而是通过getter和setter方法来实现的。
    还可以定义只读属性，只定义getter方法，不定义setter方法就是一个只读属性.
    反之就变成不可读了，是名为password的只写属性。也就是下面这里的用法。
    如果试图读取 password 属性的值,则会返回错误,因为生成散列值后就无法还原成原来的密码了。
    """
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    # 如果这个方法返回 True,就表明密码是正确的。
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        # dumps() 方法为指定的数据生成一个加密签名,然后再对数据和签名进行序列化,生成令牌字符串。
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            # 为了解码令牌,序列化对象提供了 loads() 方法,其唯一的参数是令牌字符串
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        #self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True   

    # can() 方法在请求和赋予角色这两种权限之间进行位与操作。如果角色中包含请求的所有权限位,则返回 True,表示允许用户执行此项操作。
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    # 检查管理员权限的功能经常用到,因此使用单独的方法 is_administrator() 实现。
    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def is_moderator(self):
        return self.can(Permission.MODERATE_COMMENTS)

    # last_seen 字段创建时的初始值也是当前时间,但用户每次访问网站后,这个值都会被刷新。所以添加此处的方法完成这个操作
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
    # 每次收到用户的请求时都要调用 ping() 方法。由于 auth 蓝本中的 before_app_request 处理程序会在每次请求前运行,所以能很轻松地实现这个需求

    def avatar(self):
        """
        生成头像时要生成 MD5 值,这是一项 CPU 密集型操作。如果要在某个页面中生成大量头像,计算量会非常大。
        由于用户电子邮件地址的 MD5 散列值是不变的,因此可以将其缓存在 User 模型中。
        若要把 MD5 散列值保存在数据库中,需要对 User 模型做些改动.
        """
        hash = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return 'http://dev.evuez.net/dev/identicons/?s=' + hash

    """
    follow() 方法手动把 Follow 实例插入关联表,从而把关注者和被关注者联接起来,并让程序有机会设定自定义字段的值。
    联接在一起的两个用户被手动传入 Follow 类的构造器,创建一个 Follow 新实例,然后像往常一样,把这个实例对象添加到数据库会话中。
    注意, 这里无需手动设定 timestamp 字段,因为定义字段时指定了默认值,即当前日期和时间。
    """
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(followed=user)
            self.followed.append(f)

    # unfollow() 方法使用 followed 关系找到联接用户和被关注用户的 Follow 实例。若要销毁这 两个用户之间的联接,只需删除这个 Follow 对象即可。
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            self.followed.remove(f)

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    # is_following() 方法和 is_followed_ by() 方法分别在左右两边的一对多关系中搜索指定用户,如果找到了就返回 True。
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # 注意,followed_posts() 方法定义为属性,因此调用时无需加 ()
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    def __repr__(self):
        return '<User %r>' % self.username


# 出于一致性考虑,我们还定义了 AnonymousUser 类,并实现了 can() 方法和 is_administrator() 方法。
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

    def is_moderator(self):
        return False

# 将 AnonymousUser 类设为用户未登录时 current_user 的值。这样程序不用先检查用户是否登录,就能自由调用 current_user.can() 和 current_user.is_administrator()。
login_manager.anonymous_user = AnonymousUser

"""
Flask-Login 要求程序实现一个回调函数,使用指定的标识符加载用户
加载用户的回调函数接收以 Unicode 字符串形式表示的用户标识符。
如果能找到用户,这个函数必须返回用户对象;否则应该返回 None.

记住Flask-Login里的user_id一直是unicode类型的，所以在我们把id传递给Flask-SQLAlchemy时，有必要把它转化成integer类型
"""
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    # title_html = db.Column(db.Text)    
    intro = db.Column(db.Text)
    # intro_html = db.Column(db.Text)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    body_show = db.Column(db.Boolean, default=True)    
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 和 User 模型之间是一对多关系
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

    @property
    def category_name(self):
        return Category.query.filter_by(id = self.category_id).first().category_name

    # 添加到 Post 模型中的类方法,用来生成虚拟数据
    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            """
            随机生成文章时要为每篇文章随机指定一个用户。
            为此,我们使用 offset() 查询过滤器。这个过滤器会跳过参数中指定的记录数量。
            通过设定一个随机的偏移值,再调用 first() 方法,就能每次都获得一个不同的随机用户。
            """
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(title=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                     intro=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                     body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    # on_changed_body 函数把 body 字段中的文本渲染成 HTML 格式,结果保存在 body_html 中,自动且高效地完成 Markdown 文本到 HTML 的转换。
    # def on_changed_title(target, value, oldvalue, initiator):
    #     allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 
    #                     'em', 'i', 'strong', 
    #                     'h1', 'h2', 'h3']
    # def on_changed_intro(target, value, oldvalue, initiator):
    #     allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 
    #                     'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
    #                     'h1', 'h2', 'h3', 'p']
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'h4', 'p', 'q', 
                        'img', 'hr', 'sub', 'sup', 'del',
                        'dl', 'dt', 'dd']
        # 加了这个终于可以显示图片了，否则哪怕有上面的也不行
        attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['src', 'alt'],
        }
        """
        真正的转换过程分三步完成。
        首先,markdown() 函数初步把 Markdown 文本转换成 HTML。 
        然后,把得到的结果和允许使用的 HTML 标签列表传给 clean() 函数。clean() 函数删除所有不在白名单中的标签。
        转换的最后一步由 linkify() 函数完成,这个函数由 Bleach 提供,把纯文本中的 URL 转换成适当的 <a> 链接。

        最后一步是很有必要的,因为 Markdown 规范没有为自动生成链接提供官方支持。
        PageDown 以扩展的形式实现了这个功能,因此在服务器上要调用 linkify() 函数。
        """
        # target.title_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'), tags=allowed_tags, strip=True))
        # target.intro_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'), tags=allowed_tags, strip=True))
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'), tags=allowed_tags, attributes=attrs, strip=True))

# on_changed_body 函数注册在 body 字段上,是 SQLAlchemy“set”事件的监听程序,这意味着只要这个类实例的 body 字段设了新值,函数就会自动被调用
# db.event.listen(Post.title, 'set', Post.on_changed_title)
# db.event.listen(Post.intro, 'set', Post.on_changed_intro)
db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # Comment 模型的属性几乎和 Post 模型一样,不过多了一个 disabled 字段。这是个布尔值字段,协管员通过这个字段查禁不当评论。
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @property
    def comment_of_which_post(self):
        post = Post.query.filter_by(id=self.post_id).first()
        if post:
            return post.title
        else:
            return "已删除文章"

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['p', 'a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong', 
                        'h3', 'h4', 'li', 'ol', 'ul', 'blockquote', 'pre', 'hr', 'img', 'sub', 'sup']
        attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['src', 'alt'],
        }       
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=attrs, strip=True))

    """
    和博客文章一样,评论也定义了一个事件,在修改 body 字段内容时触发,自动把 Markdown 文本转换成 HTML。
    转换过程和第 11 章中的 博客文章一样,不过评论相对较短,而且对 Markdown 中允许使用的 HTML 标签要求更严格,要删除与段落相关的标签,只留下格式化字符的标签。
    """
db.event.listen(Comment.body, 'set', Comment.on_changed_body)

    # 为了完成对数据库的修改,User 和 Post 模型还要建立与 comments 表的一对多关系


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(64))
    posts = db.relationship('Post', backref='category', lazy='dynamic')   


