from flask import render_template, redirect, request, url_for, flash, g
from . import auth
from .form import LoginForm, RegisterForm, ChangePasswordForm, ChangeProfileForm, \
    ResetPasswordForm, NewPasswordForm
from flask.ext.login import login_user, logout_user, login_required, current_user
from ..models import User, Post
from .. import db
from ..email import send_mail
import os


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash('login success!')
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('invalid username or password.')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged ouYou have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_mail(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
        flash('register success! You can now login.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)
    

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.before_app_request
def before_request():
    current_user.ping() # flash user's last_seen time before every request
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed')) 


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been send to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/change_passwd', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    print 'current_user = %s' % current_user
    if form.validate_on_submit():
        user = User.query.filter_by(username=current_user.username).first();
        user.password = form.new_password.data
        
        db.session.add(user)
        db.session.commit()
        
        flash('password changed succeed.')
        
        return redirect(url_for('main.index'))

    return render_template('auth/change_password.html', form=form)


@auth.route('/setting')
@login_required
def setting():
    return render_template('auth/setting.html')


@auth.route('/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = ChangeProfileForm()
    if form.validate_on_submit():
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        current_user.username = form.username.data
        db.session.add(current_user)
        db.session.commit()
        flash('Update Profile Success!')
        return redirect(url_for('main.user_profile', username=current_user.username))
    form.username.data = current_user.username
    form.about_me.data = current_user.about_me
    form.location.data = current_user.location
    return render_template('update_profile.html', form=form)

@auth.route('/post/delete/<int:id>')
@login_required
def delete(id):
    post=Post.query.get_or_404(id)
    if post is None:
        abort(404)
    db.session.delete(post)
    db.session.commit()
    flash('post deleted success!')
    return redirect(url_for('main.index'))

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is None:
                flash('Wrong Email!')
                form.email.data = ''
                return redirect(url_for('auth.reset_password'))
            else:
                token = user.generate_confirmation_token()
                send_mail(user.email, 'Confirm Your Account', 'auth/email/reset_confirm', user=user,
                          token=token)
                g.user = user     # for reset password confirm
                flash('Mail sent. Please checking your email to reset password.')
                return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/reset_confirm/<token>')
def reset_confirm(token):

    if user.confirm(token):
        return redirect(url_for('auth.new_password'))
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@auth.route('/new_password', methods=['GET', 'POST'])
def new_password():
    form = NewPasswordForm()
    user = g.user
    if form.validate_on_submit():
        user.email = form.email.data
        db.session.add(user)
        db.session.commit()
        flash('Password Reset Succeed!')
        return redirect(url_for('auth.login'))
    return render_template('new_password.html')