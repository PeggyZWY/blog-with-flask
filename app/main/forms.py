# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask.ext.pagedown.fields import PageDownField
from ..models import Role, User

import sys
reload(sys)
sys.setdefaultencoding('utf8')


class NameForm(Form):
    name = StringField('你的名字是什么？', validators=[Required()])
    submit = SubmitField('提交')


# 这个表单中的所有字段都是可选的,因此长度验证函数允许长度为零
class EditProfileForm(Form):
    name = StringField('真实姓名', validators=[Length(0,64)])
    location = StringField('地点', validators=[Length(0,64)])
    about_me = TextAreaField('关于我')
    submit = SubmitField('提交')


class EditProfileAdminForm(Form):
    email = StringField('邮箱', validators=[Required(), Length(1, 64), Email()])
    username = StringField('名号', validators=[Required(), Length(1, 64)])
    # confirmed = BooleanField('Confirmed')
    # WTForms 对 HTML 表单控件 <select> 进行 SelectField 包装,从而实现下拉列表
    role = SelectField('角色', coerce=int)
    name = StringField('真实姓名', validators=[Length(0,64)])
    location = StringField('地点', validators=[Length(0, 64)])
    about_me = TextAreaField('关于我')
    submit = SubmitField('提交')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        """
        SelectField 实例必须在其 choices 属性中设置各选项。
        选项必须是一个由元组组成的列表,各元组都包含两个元素:选项的标识符和显示在控件中的文本字符串。
        choices 列表在表单的构造函数中设定,其值从 Role 模型中获取,使用一个查询按照角色名的字母顺序排列所有角色。
        元组中的标识符是角色的 id,因为这是个整数,所以在 SelectField 构造函数中添加 coerce=int 参数,从而把字段的值转换为整数, 而不使用默认的字符串。
        """
        self.role.choices = [(role.id, role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user

    # 表单构造函数接收用户对象作为参数,并将其保存在成员变量中,随后自定义的验证方法要使用这个用户对象。
    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已被注册啦 ╮(￣▽￣)╭ ')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('名号已被使用啦 ╮(￣▽￣)╭')


class PostForm(Form):
    # 若想把首页中的多行文本控件转换成 Markdown 富文本编辑器,PostForm 表单中的 body 字段要进行修改
    title = TextAreaField("编辑文章_标题", validators=[Required()])
    intro = TextAreaField("编辑文章_简介")
    body = PageDownField("编辑文章_正文", validators=[Required()])
    category_name = StringField("分类", validators=[Length(0,64)])
    submit = SubmitField('提交')


class CommentForm(Form):
    body = PageDownField('评论支持部分 Markdown 语法( <a href="http://wowubuntu.com/markdown/basic.html" target="_blank">Markdown 语法快速入门</a> )', \
        validators=[Required()])
    submit = SubmitField('提交')

