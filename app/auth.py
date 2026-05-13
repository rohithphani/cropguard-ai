from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from collections import Counter
from app.database import db, bcrypt
from app.models import User, History

auth = Blueprint('auth', __name__)


@auth.route('/profile')
@login_required
def profile():
    history = (History.query
               .filter_by(user_id=current_user.id)
               .order_by(History.timestamp.desc())
               .all())

    total_scans   = len(history)
    healthy_count = sum(1 for h in history if h.disease.lower() == 'healthy')
    disease_count = total_scans - healthy_count
    unique_crops  = len({h.crop for h in history})

    crop_counter  = Counter(h.crop for h in history)
    crop_counts   = crop_counter.most_common()   # list of (crop, count)

    return render_template(
        'profile.html',
        history=history,
        total_scans=total_scans,
        healthy_count=healthy_count,
        disease_count=disease_count,
        unique_crops=unique_crops,
        crop_counts=crop_counts,
    )

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('auth.register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if user.is_banned:
                flash('Your account has been suspended. Please contact the admin.', 'error')
                return redirect(url_for('auth.login'))
            login_user(user, remember=True)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check username and password.', 'error')
            
    return render_template('login.html')

@auth.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_pw  = request.form.get('current_password')
    new_pw      = request.form.get('new_password')
    confirm_pw  = request.form.get('confirm_password')

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('auth.profile'))
    if len(new_pw) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('auth.profile'))
    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('auth.profile'))

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('auth.profile'))


@auth.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')
