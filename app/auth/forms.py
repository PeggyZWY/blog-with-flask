# -*- coding: utf-8 -*-

from flask.ext.wtf import Form
# BooleanField 类表示复选框.wtforms里是有单选框RadioField的哦
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User

import sys
reload(sys)
sys.setdefaultencoding('utf8')


class LoginForm(Form):
    email = StringField('邮箱', validators=[Required(), Length(1, 64), Email()])
    password = PasswordField('密码', validators=[Required()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登陆')


class RegistrationForm(Form):
    email = StringField('邮箱', validators=[Required(), Length(1, 64), Email()])
    """
    这个表单使用 WTForms 提供的 Regexp 验证函数,确保 username 字段只包含字母、数字、下划线和点号。
    这个验证函数中正则表达式后面的两个参数分别是正则表达式的旗标和验证失败时显示的错误消息。
    """
    username = StringField('名号', validators=[Required(), Length(1, 64)])
    # EqualTo这个验证函数要附属到两个密码字段中的一个上,另一个字段则作为参数传入。
    password = PasswordField('密码', validators=[Required(), EqualTo('password2', message='两次密码要一样噢~')])
    password2 = PasswordField('确认密码', validators=[Required()])
    submit = SubmitField('注册')

    """
    这个表单还有两个自定义的验证函数,以方法的形式实现。
    如果表单类中定义了以 validate_ 开头且后面跟着字段名的方法,这个方法就和常规的验证函数一起调用。
    """
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            # 自定义的验证函数要想表示验证失败,可以抛出 ValidationError 异常,其参数就是错误消息
            raise ValidationError('邮箱已被注册啦 ╮(￣▽￣)╭ ')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('名号已被使用啦 ╮(￣▽￣)╭')


class ChangePasswordForm(Form):
    old_password = PasswordField('当前密码', validators=[Required()])
    password = PasswordField('新密码', validators=[
        Required(), EqualTo('password2', message='两次密码要一样噢~')])
    password2 = PasswordField('确认新密码', validators=[Required()])
    submit = SubmitField('确认修改密码')


class PasswordResetRequestForm(Form):
    email = StringField('邮箱', validators=[Required(), Length(1, 64),
                                             Email()])
    submit = SubmitField('重设密码')


class PasswordResetForm(Form):
    email = StringField('邮箱', validators=[Required(), Length(1, 64),
                                             Email()])
    password = PasswordField('新密码', validators=[
        Required(), EqualTo('password2', message='两次密码要一样噢~')])
    password2 = PasswordField('确认新密码', validators=[Required()])
    submit = SubmitField('重设密码')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('无效邮箱')

