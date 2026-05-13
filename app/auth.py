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
