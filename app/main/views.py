# -*- coding: utf-8 -*-

# 11d 准备过程中加了request & current_app, 12d 准备过程中加了make_response
from flask import render_template, redirect, url_for, abort, flash, request, current_app, make_response
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from ..models import Role, User, Permission, Post, Comment, Category, HomePage
from .. import db
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from ..decorators import admin_required, permission_required

import sys
reload(sys)
sys.setdefaultencoding('utf8')

# 为会出现分类列表的排序做准备，涉及到路由'/post/<int:id>'、'/article'和'/article/<category_name>'
def sort_category():
    if Category.query.all():
        category = Category.query.all()
        dict = {}
        for i in category:
            count = i.posts.count()
            if count == 0:
                db.session.delete(i)
                db.session.commit()
            else:
                dict[i] = count
        category = sorted(dict, key=dict.__getitem__, reverse=True)
        return category

# 报告缓慢的数据库查询
"""
这个功能使用 after_app_request 处理程序实现,它和 before_app_request 处理程序的工作方式类似,只不过在视图函数处理完请求之后执行。
Flask 把响应对象传给 after_app_ request 处理程序,以防需要修改响应。
在这里,after_app_request 处理程序没有修改响应,只是获取 Flask-SQLAlchemy 记录 的查询时间并把缓慢的查询写入日志。

"""
@main.after_app_request
def after_request(response):
    """
    get_debug_queries() 函数返回一个列表,其元素是请求中执行的查询
    遍历 get_debug_queries() 函数获取的列表,把持续时间比设定阈值长的查询写入日志。
    写入的日志被设为“警告”等级。如果换成“错误”等级,发 现缓慢的查询时还会发送电子邮件。
    """
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration, query.context))
    return response


"""
Werkzeug Web 服务器本身就有停止选项,但由于服务器运行在单独的线程中,关闭服务器的唯一方法是发送一个普通的 HTTP 请求.

只有当程序运行在测试环境中时,这个关闭服务器的路由才可用,在其他配置中调用时将不起作用。
在实际过程中,关闭服务器时要调用 Werkzeug 在环境中提供的关闭函数。调用这个函数且请求处理完成后,开发服务器就知道自己需要优雅地退出了。
"""
@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
    homepages = HomePage.query.filter_by(id=1).first()
    if not homepages:
        homepages = HomePage(view_times=1)
        db.session.add(homepages)
        db.session.commit()
    try:
        if homepages.view_times > 0:
            homepages.view_times = homepages.view_times + 1
        else:
            homepages.view_times = 1
        db.session.add(homepages)
        db.session.commit()
    except:
        pass
    return render_template('index.html')


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
        # 用户发布的博客文章列表通过 User.posts 关系获取,User.posts 返回的是查询对象,因此可在其上调用过滤器,例如 order_by()。
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('资料已更新 (｡・`ω´･)')
        return redirect(url_for('.user', username=current_user.username))
    # 为所有字段设定了初始值
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
# 用户由 id 指定
def edit_profile_admin(id):
    # 使用 Flask-SQLAlchemy 提供的 get_or_404() 函数,如果提供的 id 不正确,则会返回 404 错误。
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        #user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('资料已更新 (｡・`ω´･)')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    #form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)
    """
    我们还需要再探讨一下用于选择用户角色的 SelectField。
    设定这个字段的初始值时, role_id 被赋值给了 field.role.data,这么做的原因在于 choices 属性中设置的元组列表使用数字标识符表示各选项。
    表单提交后,id 从字段的 data 属性中提取,并且查询时会使用提取出来的 id 值加载角色对象。
    表单中声明 SelectField 时使用 coerce=int 参数, 其作用是保证这个字段的 data 属性值是整数。
    """


# 博客文章的 URL 使用插入数据库时分配的唯一 id 字段构建
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    post.body_show = True
    # 这个视图函数实例化了一个评论表单,并将其转入 post.html 模板,以便渲染。
    #input_hint = '*斜体*, **粗体**, `代码`, * a, , '
    input_hint = '''### h3标题（注意：换行是先敲两个空格再敲回车！）  
***  
+ 三个星号是分隔线。现在这个加号后面一个空格是列表。  
+ *斜体*  
+  **粗体**  
+ `代码`  
+ [完整版 Markdown 语法说明](http://wowubuntu.com/markdown/index.html)  
  
> 块引用  
  
    # Python
    print "每行前面加四个空格是代码块"  
 '''
    form = CommentForm(body=input_hint)
    # 提交表单 后,插入新评论的逻辑和处理博客文章的过程差不多
    if form.validate_on_submit():
        # 和 Post 模型一样,评论的 author 字段也不能直接设为 current_user,因为这个变量是上下文代理对象。真正的 User 对象要 使用表达式 current_user._get_current_object() 获取。
        comment = Comment(body=form.body.data, post=post, author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('评论已提交 (｡・`ω´･)')
        # 提交评论后,请求结果是一个重定 向,转回之前的 URL,但是在 url_for() 函数的参数中把 page 设为 -1,这是个特殊的页 数,用来请求评论的最后一页,所以刚提交的评论才会出现在页面中。
        return redirect(url_for('.post', id=post.id))
    # 程序从查询字符串 中获取页数,发现值为 -1 时,会计算评论的总量和总页数,得出真正要显示的页数。
    page = request.args.get('page', 1, type=int)
    if page == -1:
        # " // "来表示整数除法，返回不大于结果的一个最大的整数，而" / " 则单纯的表示浮点数除法
        page = (post.comments.count() - 1) // \
            current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    # 文章的评论列表通过 post.comments 一对多关系获取,按照时间戳顺序进行排列,再使 用与博客文章相同的技术分页显示。
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    category = sort_category()
    if post.view_times > 0:
        post.view_times = post.view_times + 1
    else:
        post.view_times = 1
    db.session.add(post)
    db.session.commit()
    # 评论列表对象和分页对象都传入了模板,以便渲染。
    return render_template('post.html', posts=[post], form=form, categories=category, comments=comments, pagination=pagination)
    # 评论的渲染过程在新模板 _comments.html 中进行,类似于 _posts.html,但使用的 CSS 类不 同。_comments.html 模板要引入 post.html 中,放在文章正文下方,后面再显示分页导航。

    """ 这是之前的最后一句：

    post.html 模板接收一个列表作为参数,这个列表就是要渲染的文章。
    这里必须要传入列表,因为只有这样,index.html 和 user.html 引用的 _posts.html 模板才能在这个页面中使用。
    
    return render_template('post.html', posts=[post])
    """


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if post.category_id:
        category = Category.query.get_or_404(post.category_id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    # 这里使用 的 PostForm 表单类和首页中使用的是同一个。
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.intro = form.intro.data
        post.body = form.body.data
        if form.category_name.data:
            category_name_exists = Category.query.filter_by(category_name=form.category_name.data).first()
            if not category_name_exists:
                category = Category(category_name=form.category_name.data)
                db.session.add(category)
                db.session.commit()
                post.category_id = category.id
            else:
                post.category_id = category_name_exists.id
        db.session.add(post)
        db.session.commit()
        flash('文章已提交 (｡・`ω´･)')
        return redirect(url_for('.post', id=post.id))
    form.title.data = post.title
    form.intro.data = post.intro
    form.body.data = post.body
    if post.category_id:
        category = Category.query.filter_by(id=post.category.id).first()
        form.category_name.data = category.category_name
    return render_template('edit_post.html', form=form)


# 用户在其他用户的资料页中点击“Follow”(关注)按钮后,执行的是/follow/<username>路由。
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('你已关注了此用户')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('你关注了 %s' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('你已取消关注了此用户')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('你已不再关注 %s' % username)
    return redirect(url_for('.user', username=username))


# 用户在其他用户的资料页中点击关注者数量后,将调用 /followers/<username> 路由。
@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('.index'))
    # 使用第 11 章中介绍的技术分页显示该用户的 followers 关系。
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    # 由于查询关注者返回的是 Follow 实例列表,为了渲染方便,将其转换成一个新列表,列表中的各元素都包含 user 和 timestamp 字段。
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    # 渲染关注者列表的模板可以写的通用一些,以便能用来渲染关注的用户列表和被关注的用户列表。模板接收的参数包括用户对象、分页链接使用的端点、分页对象和查询结果列表。
    return render_template('followers.html', user=user, title='他们关注了', 
                            endpoint='.followers', pagination=pagination, follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title='关注了他们',
                            endpoint='.followed_by', pagination=pagination, follows=follows)


"""
show_followedcookie 在两个新路由中设定
指向这两个路由的链接添加在首页模板中。点击这两个链接后会为 show_followed cookie 设定适当的值,然后重定向到首页。
"""
@main.route('/all')
@login_required
def show_all():
    # cookie 只能在响应对象中设置,因此这两个路由不能依赖 Flask,要使用 make_response() 方法创建响应对象。
    resp = make_response(redirect(url_for('.article')))
    # set_cookie() 函数的前两个参数分别是 cookie 名和值。可选的 max_age 参数设置 cookie 的过期时间,单位为秒。如果不指定参数 max_age,浏览器关闭后 cookie 就会过期。
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp 


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.article')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


# 管理评论的路由
# 这个函数很简单,它从数据库中读取一页评论,将其传入模板进行渲染。除了评论列表之外,还把分页对象和当前页数传入了模板。
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments, pagination=pagination, page=page)


"""
以下启用路由和禁用路由都是先加载评论对象,把 disabled 字段设为正确的值,再把评论对象写入数据库。
最后,重定向到评论管理页面,如果查询字符串中指定了 page 参数,会将其传入重定向操作。
_comments.html 模板中的按钮指定了 page 参数,重定向后会返回之前的页面。
"""
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1 ,type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))


@main.route('/article_new', methods=['GET', 'POST'])
@permission_required(Permission.WRITE_ARTICLES)
def article_new():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
        """
        新文章对象的 author 属性值为表达式 current_user._get_current_object()。
        变量 current_user 由 Flask-Login 提供,和所有上下文变量一样,也是通过线程内的代理对象实现。
        这个对象的表现类似用户对象,但实际上却是一个轻度包装,包含真正的用户对象。 
        数据库需要真正的用户对象,因此要调用 _get_current_object() 方法。
        """
        post = Post(title=form.title.data, intro=form.intro.data, body=form.body.data, 
            author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        if form.category_name.data:
            category = Category(category_name=form.category_name.data)
            db.session.add(category)
            db.session.commit()
            post.category_id = category.id
            # db.session.add(post)
        return redirect(url_for('.article'))       
    return render_template('article_new.html', form=form)
    # 这样修改之后,首页中的文章列表只会显示有限数量的文章。若想查看第 2 页中的文章, 要在浏览器地址栏中的 URL 后加上查询字符串 ?page=2。


@main.route('/article', methods=['GET', 'POST'])
def article():
    # form = PostForm()
    # if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
    #     """
    #     新文章对象的 author 属性值为表达式 current_user._get_current_object()。
    #     变量 current_user 由 Flask-Login 提供,和所有上下文变量一样,也是通过线程内的代理对象实现。
    #     这个对象的表现类似用户对象,但实际上却是一个轻度包装,包含真正的用户对象。 
    #     数据库需要真正的用户对象,因此要调用 _get_current_object() 方法。
    #     """
    #     post = Post(title=form.title.data, intro=form.intro.data, body=form.body.data, 
    #         author=current_user._get_current_object())
    #     db.session.add(post)
    #     if form.category_name.data:
    #         category = Category(category_name=form.category_name.data)
    #         db.session.add(category)
    #         db.session.commit()
    #         post.category_id = category.id
    #         db.session.add(post)
    #     return redirect(url_for('.article'))
    # 渲染的页数从请求的查询字符串(request.args)中获取,如果没有明确指定,则默认渲染第一页。参数 type=int 保证参数无法转换成整数时,返回默认值
    page = request.args.get('page', 1, type=int)
    # show_followed = False
    # if current_user.is_authenticated:
    #     """
    #     决定显示所有博客文章还是只显示所关注用户文章的选项存储在 cookie 的 show_followed 字段中,如果其值为非空字符串,则表示只显示所关注用户的文章。
    #     cookie 以 request. cookies 字典的形式存储在请求对象中.
    #     这个 cookie 的值会转换成布尔值,根据得到的值设定本地变量 query 的值。query 的值决定最终获取所有博客文章的查询,或是获取过滤后的博客文章查询。
    #     """
    #     show_followed = bool(request.cookies.get('show_followed', ''))
    # if show_followed:
    #     query = current_user.followed_posts
    # else:
    #     query = Post.query
    query = Post.query
    """
    为了显示某页中的记录,要把 all() 换成 Flask-SQLAlchemy 提供的 paginate() 方法。
    页数是 paginate() 方法的第一个参数,也是唯一必需的参数。
    可选参数 per_page 用来指定每页显示的记录数量;如果没有指定,则默认显示 20 个记录。
    另一个可选参数为 error_ out,当其设为 True 时(默认值),如果请求的页数超出了范围,则会返回 404 错误;如果 设为 False,页数超出范围时会返回一个空列表。
    为了能够很便利地配置每页显示的记录数量,参数 per_page 的值从程序的环境变量 FLASKY_POSTS_PER_PAGE 中读取。所以去config.py里增加了。
    """
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    posts = pagination.items
    category = sort_category()
    for post in posts:
        post.body_show = False       
    return render_template('article.html', posts=posts, categories=category, show_followed=show_followed, pagination=pagination)
    # 这样修改之后,首页中的文章列表只会显示有限数量的文章。若想查看第 2 页中的文章, 要在浏览器地址栏中的 URL 后加上查询字符串 ?page=2。


@main.route('/article/<category_name>', methods=['GET', 'POST'])
def article_category_name(category_name):
    # form = PostForm()
    # if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
    #     post = Post(title=form.title.data, intro=form.intro.data, body=form.body.data, author=current_user._get_current_object())
    #     db.session.add(post)
    #     return redirect(url_for('.article'))
    page = request.args.get('page', 1, type=int)
    if not Category.query.filter_by(category_name=category_name).all():
        abort(404)
    _category = Category.query.filter_by(category_name=category_name).first()
    pagination = Post.query.filter_by(category_id=_category.id).order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    category = sort_category()
    for post in posts:
        post.body_show = False          
    return render_template('article.html', posts=posts, categories=category, show_followed=show_followed, pagination=pagination)


@main.route('/delete-article/<int:id>')
@login_required
def delete_article(id):
    post = Post.query.get_or_404(id)
    if not current_user.can(Permission.ADMINISTER):
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('你已成功删除了文章《%s》' % post.title)
    return redirect(url_for('.article'))


@main.route('/delete-comment/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()
    flash('你已成功删除了文章《%s》的评论"%s"' % (comment.comment_of_which_post, comment.body))
    return redirect(url_for('.moderate', page=request.args.get('page', 1 ,type=int)))


@main.route('/resume')
def resume():
    return render_template('resume.html')


@main.route('/contact')
def contact():
    return render_template('contact.html')


@main.route('/lab')
def lab():
    return render_template('lab.html')


# # 保存文件到SAE Storage
# @app.route('/save')
# def save():
#     data = 'data to save'
#     filename = 'filename'
#     ret = sae_storage.save(data, filename)
#     return str(ret)


# # 删除SAE Storage中的文件
# @app.route('/delete')
# def delete():
#     filename = 'filename'
#     ret = sae_storage.delete(filename)
#     return str(ret)


# # 根据文件名获取对应的公开URL
# @app.route('/url')
# def url():
#     filename = 'filename'
#     return sae_storage.url(filename)

