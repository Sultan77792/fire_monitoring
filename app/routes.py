# routes.py (супер идеальный полный код)
import os
import jwt
import logging
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
import pyotp
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash, abort
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, extract
from sqlalchemy.sql import func as sql_func
from sklearn.linear_model import LinearRegression
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from markupsafe import escape
from minio import Minio
from minio.error import S3Error
from config import Config
from models import User, Fire, AuditLog, KGUOOPT, FireData, REGIONS, LANGUAGES, FireForce
from forms import FireForm, LoginForm, ExportForm
from database import SessionLocal, db
from utils import allowed_file, check_access
from regions import REGIONS_AND_LOCATIONS
from extensions import cache
from dashboard import create_dash_app
import pandas as pd

# Инициализация приложения
app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
socketio = SocketIO(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# MinIO клиент
minio_client = Minio(
    Config.MINIO_ENDPOINT,
    access_key=Config.MINIO_ACCESS_KEY,
    secret_key=Config.MINIO_SECRET_KEY,
    secure=Config.MINIO_SECURE
)
BUCKET_NAME = Config.MINIO_BUCKET

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dash интеграция
with app.app_context():
    create_dash_app(app)

# Регистрация маршрутов
def register_routes(app, socketio, cache, csrf):
    """Регистрирует все маршруты приложения."""

    def token_required(f):
        def decorated(*args, **kwargs):
            token = request.cookies.get('token') or request.headers.get('Authorization')
            if not token:
                return jsonify({'success': False, 'message': 'Токен отсутствует'}), 401
            if token.startswith('Bearer '):
                token = token.split()[1]
            try:
                data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
                request.user = data
            except jwt.ExpiredSignatureError:
                return jsonify({'success': False, 'message': 'Срок действия токена истек'}), 401
            except Exception as e:
                logger.error(f"Неверный токен: {str(e)}")
                return jsonify({'success': False, 'message': 'Неверный токен'}), 401
            return f(*args, **kwargs)
        decorated.__name__ = f.__name__
        return decorated

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'success': False, 'message': 'Размер файла превышает 16 МБ'}), 413

    @login_manager.user_loader
    def load_user(user_id):
        with SessionLocal() as db:
            return db.query(User).get(int(user_id))

    @app.route('/')
    def login_page():
        form = LoginForm()
        lang = request.args.get('lang', 'ru')
        return render_template('login.html', form=form, lang=LANGUAGES[lang])

    @app.route('/login', methods=['POST'])
    @csrf.exempt
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            totp_code = form.totp.data if hasattr(form, 'totp') else request.form.get('totp')
            with SessionLocal() as db:
                user = db.query(User).filter(User.username == username).first()
                if user and check_password_hash(user.password, password):
                    if user.totp_secret:
                        totp = pyotp.TOTP(user.totp_secret)
                        if not totp_code or not totp.verify(totp_code):
                            return jsonify({'success': False, 'message': 'Требуется 2FA', '2fa_required': True}), 400
                    login_user(user)
                    token = jwt.encode({
                        'user_id': user.id,
                        'role': user.role,
                        'region': user.region,
                        'exp': datetime.utcnow() + timedelta(hours=24)
                    }, Config.SECRET_KEY)
                    response = jsonify({'success': True})
                    response.set_cookie('token', token, httponly=True, secure=True, samesite='Strict', max_age=24*60*60)
                    flash('Успешный вход в систему.', 'success')
                    logger.info(f"Пользователь {username} вошел в систему")
                    if user.role == 'engineer':
                        return redirect(url_for('dashboard', region=user.region))
                    elif user.role == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('dashboard'))
            flash('Неверное имя пользователя или пароль', 'danger')
            return jsonify({'success': False, 'message': 'Неверный логин или пароль'}), 401
        return render_template('login.html', form=form, lang=LANGUAGES['ru'])

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        response = jsonify({'success': True})
        response.delete_cookie('token')
        flash('Вы вышли из системы.', 'success')
        logger.info(f"Пользователь {current_user.username} вышел из системы")
        return redirect(url_for('login_page'))

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    @token_required
    def profile():
        if request.method == 'GET':
            lang = request.args.get('lang', 'ru')
            return render_template('profile.html', regions=REGIONS, lang=LANGUAGES[lang], user={
                'username': current_user.username, 'region': current_user.region, 'role': current_user.role, 'totp_secret': current_user.totp_secret
            })
        data = request.form.to_dict()
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == request.user['user_id']).first()
            if 'password' in data and data['password']:
                user.password = generate_password_hash(data['password'])
            user.region = data.get('region') or None
            if 'totp_enable' in data and data['totp_enable'] == 'on' and not user.totp_secret:
                user.totp_secret = pyotp.random_base32()
            elif 'totp_disable' in data and data['totp_disable'] == 'on':
                user.totp_secret = None
            db.commit()
            log_event(user.username, 'UPDATE', 'users', user.id, str({k: v for k, v in data.items() if k != 'password'}))
        flash('Профиль обновлен.', 'success')
        return jsonify({'success': True, 'totp_secret': user.totp_secret if 'totp_enable' in data else None})

    @app.route('/fires')
    @login_required
    def fires_page():
        lang = request.args.get('lang', 'ru')
        with SessionLocal() as db:
            kgu_oopt_list = db.query(KGUOOPT).all()
        return render_template('fires.html', regions=REGIONS, kgu_oopt=[(k.id, k.name) for k in kgu_oopt_list], lang=LANGUAGES[lang])

    @app.route('/form', methods=['GET', 'POST'])
    @login_required
    def form_page():
        form = FireForm()
        if current_user.role == 'admin':
            form.region.choices = [(region, region) for region in REGIONS_AND_LOCATIONS.keys()]
            selected_region = request.form.get('region', form.region.data)
            form.location.choices = [(loc, loc) for loc in REGIONS_AND_LOCATIONS.get(selected_region, [])]
        else:
            user_region = current_user.region
            form.region.choices = [(user_region, user_region)]
            form.location.choices = [(loc, loc) for loc in REGIONS_AND_LOCATIONS.get(user_region, [])]

        if form.validate_on_submit():
            file = request.files.get('file')
            file_path = None
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                try:
                    minio_client.put_object(BUCKET_NAME, filename, file, file.content_length)
                    file_path = filename
                except S3Error as e:
                    flash(f"Ошибка загрузки файла в MinIO: {e}", 'danger')
                    return render_template('form.html', form=form)

            with SessionLocal() as db:
                new_fire = Fire(
                    date=form.date.data,
                    region=form.region.data,
                    location=form.location.data,
                    branch=form.branch.data,
                    forestry=form.forestry.data,
                    quarter=form.quarter.data,
                    allotment=form.allotment.data,
                    damage_area=form.damage_area.data,
                    damage_les=form.damage_les.data,
                    damage_les_lesopokryt=form.damage_les_lesopokryt.data,
                    damage_les_verh=form.damage_les_verh.data,
                    damage_not_les=form.damage_not_les.data,
                    LO_flag=form.LO_flag.data,
                    LO_people_count=form.LO_people_count.data,
                    LO_tecnic_count=form.LO_tecnic_count.data,
                    APS_flag=form.APS_flag.data,
                    APS_people_count=form.APS_people_count.data,
                    APS_tecnic_count=form.APS_tecnic_count.data,
                    APS_aircraft_count=form.APS_aircraft_count.data,
                    KPS_flag=form.KPS_flag.data,
                    KPS_people_count=form.KPS_people_count.data,
                    KPS_tecnic_count=form.KPS_tecnic_count.data,
                    KPS_aircraft_count=form.KPS_aircraft_count.data,
                    MIO_flag=form.MIO_flag.data,
                    MIO_people_count=form.MIO_people_count.data,
                    MIO_tecnic_count=form.MIO_tecnic_count.data,
                    MIO_aircraft_count=form.MIO_aircraft_count.data,
                    other_org_flag=form.other_org_flag.data,
                    other_org_people_count=form.other_org_people_count.data,
                    other_org_tecnic_count=form.other_org_tecnic_count.data,
                    other_org_aircraft_count=form.other_org_aircraft_count.data,
                    description=form.description.data,
                    damage_tenge=form.damage_tenge.data,
                    firefighting_costs=form.firefighting_costs.data,
                    KPO=form.KPO.data,
                    file_path=file_path,
                    created_by=current_user.id
                )
                db.add(new_fire)
                db.commit()
                log_event(current_user.username, 'INSERT', 'fires', new_fire.id, str(form.data))
                flash('Данные успешно добавлены!', 'success')
                socketio.emit('new_fire', {'message': f"Новый пожар в {new_fire.region}", 'region': new_fire.region})
                return redirect(url_for('dashboard'))
        return render_template('form.html', form=form, regions_and_locations=REGIONS_AND_LOCATIONS)

    @app.route('/api/fires', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def get_fires_api():
        role = request.user['role']
        region = request.user['region']
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        search = request.args.get('search', '').strip()
        with SessionLocal() as db:
            query = db.query(Fire)
            if role in ['operator', 'engineer'] and region:
                query = query.filter(Fire.region == region)
            if date_from:
                query = query.filter(Fire.date >= date_from)
            if date_to:
                query = query.filter(Fire.date <= date_to)
            if search:
                query = query.filter(
                    (Fire.region.ilike(f'%{search}%')) |
                    (Fire.description.ilike(f'%{search}%')) |
                    (Fire.file_path.ilike(f'%{search}%'))
                )
            total = query.count()
            fires = query.order_by(Fire.date.desc()).offset((page - 1) * per_page).limit(per_page).all()
            return jsonify({
                'fires': [{
                    'id': f.id,
                    'date': str(f.date),
                    'region': escape(f.region),
                    'location': escape(f.location),
                    'damage_area': float(f.damage_area or 0),
                    'description': escape(f.description),
                    'file_path': f.file_path,
                    'created_by': f.created_by
                } for f in fires],
                'total': total
            })

    @app.route('/api/fires', methods=['POST'])
    @token_required
    def add_fire_api():
        error, status = check_access(request.user['role'], ['admin', 'engineer', 'operator'])
        if error:
            return error, status
        try:
            data = FireData(**request.form.to_dict())
            file = request.files.get('file')
            file_path = None
            if file:
                if not allowed_file(file.filename):
                    return jsonify({'success': False, 'message': 'Недопустимый формат файла'}), 400
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
                minio_client.put_object(BUCKET_NAME, filename, file, file.content_length)
                file_path = filename
            with SessionLocal() as db:
                fire = Fire(
                    date=data.fire_date,
                    region=data.region,
                    kgu_oopt_id=data.kgu_oopt_id,
                    area=data.area,
                    description=data.description,
                    file_path=file_path,
                    created_by=request.user['user_id']
                )
                db.add(fire)
                db.commit()
                log_event(request.user['user_id'], 'INSERT', 'fires', fire.id, str(data.dict()))
            socketio.emit('new_fire', {'message': f"Новый пожар в {data.region}", 'region': data.region})
            return jsonify({'success': True, 'fire_id': fire.id})
        except Exception as e:
            logger.error(f"Ошибка добавления пожара: {str(e)}")
            return jsonify({'success': False, 'message': 'Ошибка сервера'}), 500

    @app.route('/edit/<int:fire_id>', methods=['GET', 'POST'])
    @login_required
    def edit_fire(fire_id):
        with SessionLocal() as db:
            fire = db.query(Fire).get_or_404(fire_id)
            form = FireForm(obj=fire)
            if current_user.role == 'admin':
                form.region.choices = [(region, region) for region in REGIONS_AND_LOCATIONS.keys()]
                form.location.choices = [(loc, loc) for loc in REGIONS_AND_LOCATIONS.get(fire.region, [])]
            elif current_user.role == 'engineer':
                if fire.region != current_user.region:
                    flash('У вас нет прав редактировать этот пожар.', 'danger')
                    return redirect(url_for('admin_dashboard'))
                form.region.choices = [(current_user.region, current_user.region)]
                form.location.choices = [(loc, loc) for loc in REGIONS_AND_LOCATIONS.get(current_user.region, [])]

            if form.validate_on_submit():
                old_data = {col.name: getattr(fire, col.name) for col in Fire.__table__.columns}
                form.populate_obj(fire)
                file = request.files.get('file')
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    minio_client.put_object(BUCKET_NAME, filename, file, file.content_length)
                    fire.file_path = filename
                db.commit()
                changes = [f"{k}: {old_data[k]} -> {getattr(fire, k)}" for k in old_data if old_data[k] != getattr(fire, k)]
                if changes:
                    log_event(current_user.username, 'UPDATE', 'fires', fire.id, '; '.join(changes))
                flash('Данные успешно обновлены!', 'success')
                return redirect(url_for('admin_dashboard'))
        return render_template('edit_fire.html', form=form, fire=fire)

    @app.route('/api/fires/<int:fire_id>', methods=['PUT'])
    @token_required
    def edit_fire_api(fire_id):
        error, status = check_access(request.user['role'], ['admin', 'engineer', 'operator'])
        if error:
            return error, status
        try:
            data = FireData(**request.form.to_dict())
            file = request.files.get('file')
            file_path = None
            if file:
                if not allowed_file(file.filename):
                    return jsonify({'success': False, 'message': 'Недопустимый формат файла'}), 400
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
                minio_client.put_object(BUCKET_NAME, filename, file, file.content_length)
                file_path = filename
            with SessionLocal() as db:
                fire = db.query(Fire).filter(Fire.id == fire_id).first()
                if not fire:
                    return jsonify({'success': False, 'message': 'Пожар не найден'}), 404
                if fire.created_by != request.user['user_id'] and request.user['role'] != 'admin':
                    return jsonify({'success': False, 'message': 'Нет прав для редактирования'}), 403
                fire.date = data.fire_date
                fire.region = data.region
                fire.kgu_oopt_id = data.kgu_oopt_id
                fire.area = data.area
                fire.description = data.description
                if file_path:
                    fire.file_path = file_path
                db.commit()
                log_event(request.user['user_id'], 'UPDATE', 'fires', fire.id, str(data.dict()))
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Ошибка редактирования пожара {fire_id}: {str(e)}")
            return jsonify({'success': False, 'message': 'Ошибка сервера'}), 500

    @app.route('/delete/<int:fire_id>', methods=['POST'])
    @login_required
    def delete_fire(fire_id):
        if current_user.role != 'admin':
            return abort(403)
        with SessionLocal() as db:
            fire = db.query(Fire).get_or_404(fire_id)
            db.delete(fire)
            db.commit()
            log_event(current_user.username, 'DELETE', 'fires', fire_id, f"Удалена запись о пожаре с ID {fire_id}")
            flash(f"Запись о пожаре с ID {fire_id} успешно удалена.", 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/api/fires/<int:fire_id>', methods=['DELETE'])
    @token_required
    def delete_fire_api(fire_id):
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        with SessionLocal() as db:
            fire = db.query(Fire).filter(Fire.id == fire_id).first()
            if not fire:
                return jsonify({'success': False, 'message': 'Пожар не найден'}), 404
            db.delete(fire)
            db.commit()
            log_event(request.user['user_id'], 'DELETE', 'fires', fire_id)
        return jsonify({'success': True})

    @app.route('/logs')
    @login_required
    def logs_page():
        if current_user.role != 'admin':
            return redirect(url_for('fires_page'))
        lang = request.args.get('lang', 'ru')
        return render_template('logs.html', lang=LANGUAGES[lang])

    @app.route('/api/logs', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def get_logs():
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        with SessionLocal() as db:
            total = db.query(AuditLog).count()
            logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            'logs': [{'time': str(l.timestamp), 'user_id': l.user_id, 'action': l.action, 'table': l.table_name,
                      'record_id': l.record_id, 'changes': escape(l.changes)} for l in logs],
            'total': total
        })

    @app.route('/api/logs/export', methods=['GET'])
    @token_required
    def export_logs():
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        with SessionLocal() as db:
            logs = db.query(AuditLog).all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Time', 'User ID', 'Action', 'Table', 'Record ID', 'Changes'])
        writer.writerows([(str(l.timestamp), l.user_id, l.action, l.table_name, l.record_id, l.changes) for l in logs])
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'logs_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/admin-dashboard')
    @login_required
    def admin_dashboard():
        with SessionLocal() as db:
            if current_user.role == 'engineer':
                fires = db.query(Fire).filter_by(region=current_user.region).order_by(Fire.date.desc()).all()
                audit_logs = []
            else:
                fires = db.query(Fire).order_by(Fire.date.desc()).all()
                audit_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
        return render_template('admin_dashboard.html', fires=fires, audit_logs=audit_logs, current_role=current_user.role)

    @app.route('/download/<filename>', methods=['GET'])
    @login_required
    def download_file(filename):
        try:
            file_obj = minio_client.get_object(BUCKET_NAME, filename)
            return send_file(file_obj, as_attachment=True, download_name=filename)
        except S3Error as e:
            logger.error(f"Ошибка скачивания файла из MinIO: {e}")
            flash('Файл не найден или произошла ошибка.', 'danger')
            return redirect(url_for('dashboard'))

    @app.route('/export', methods=['GET', 'POST'])
    @login_required
    def export():
        form = ExportForm()
        if form.validate_on_submit():
            with SessionLocal() as db:
                query = db.query(Fire)
                if form.start_date.data:
                    query = query.filter(Fire.date >= form.start_date.data)
                if form.end_date.data:
                    query = query.filter(Fire.date <= form.end_date.data)
                fires = query.all()
                fire_data = [{k: getattr(f, k) for k in Fire.__table__.columns.keys()} for f in fires]
                df = pd.DataFrame(fire_data)
                csv_file = "/tmp/fire_data_export.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                return send_file(csv_file, as_attachment=True, mimetype='text/csv')
        return render_template('export.html', form=form)

    @app.route('/api/export', methods=['GET'])
    @token_required
    def export_fires():
        error, status = check_access(request.user['role'], ['admin', 'analyst', 'engineer', 'operator'])
        if error:
            return error, status
        role = request.user['role']
        region = request.user['region']
        year = request.args.get('year')
        month = request.args.get('month')
        with SessionLocal() as db:
            query = db.query(Fire)
            if role in ['operator', 'engineer'] and region:
                query = query.filter(Fire.region == region)
            if year:
                query = query.filter(extract('year', Fire.date) == year)
            if month:
                query = query.filter(extract('month', Fire.date) == month)
            fires = query.all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Дата', 'Регион', 'КГУ/ООПТ', 'Площадь', 'Описание', 'Файл', 'Создал'])
        writer.writerows([(f.id, f.date, f.region, f.kgu_oopt_id, f.area, f.description, f.file_path, f.created_by) for f in fires])
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'fires_export_{year or "all"}_{month or "all"}.csv'
        )

    @app.route('/analytics')
    @login_required
    def analytics_page():
        error, status = check_access(current_user.role, ['admin', 'analyst', 'engineer', 'operator'])
        if error:
            return redirect(url_for('fires_page'))
        lang = request.args.get('lang', 'ru')
        with SessionLocal() as db:
            years = db.query(extract('year', Fire.date)).distinct().order_by(extract('year', Fire.date)).all()
            years = [str(int(year[0])) for year in years if year[0]]
        return render_template('analytics.html', regions=REGIONS, years=years, lang=LANGUAGES[lang])

    @app.route('/api/analytics', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def get_analytics():
        error, status = check_access(request.user['role'], ['admin', 'analyst', 'engineer', 'operator'])
        if error:
            return error, status
        role = request.user['role']
        region = request.user['region']
        year = request.args.get('year')
        month = request.args.get('month')
        region_filter = request.args.get('region_filter')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        with SessionLocal() as db:
            stats_query = db.query(
                Fire.region,
                sql_func.month(Fire.date).label('month'),
                sql_func.count(Fire.id).label('count'),
                sql_func.sum(Fire.area).label('total_area'),
                sql_func.sum(Fire.damage_tenge).label('total_damage')
            )
            map_query = db.query(Fire).filter(Fire.latitude.isnot(None), Fire.longitude.isnot(None))
            forces_query = db.query(FireForce).join(Fire, FireForce.fire_id == Fire.id)

            if role in ['operator', 'engineer'] and region:
                stats_query = stats_query.filter(Fire.region == region)
                map_query = map_query.filter(Fire.region == region)
                forces_query = forces_query.filter(Fire.region == region)
            if region_filter and role in ['admin', 'analyst']:
                stats_query = stats_query.filter(Fire.region == region_filter)
                map_query = map_query.filter(Fire.region == region_filter)
                forces_query = forces_query.filter(Fire.region == region_filter)
            if year:
                stats_query = stats_query.filter(extract('year', Fire.date) == year)
                map_query = map_query.filter(extract('year', Fire.date) == year)
                forces_query = forces_query.filter(extract('year', Fire.date) == year)
            if month:
                stats_query = stats_query.filter(extract('month', Fire.date) == month)
                map_query = map_query.filter(extract('month', Fire.date) == month)
                forces_query = forces_query.filter(extract('month', Fire.date) == month)

            stats_query = stats_query.group_by(Fire.region, sql_func.month(Fire.date))
            total = stats_query.count()
            stats_data = stats_query.offset((page - 1) * per_page).limit(per_page).all()
            map_data = map_query.all()
            forces_data = forces_query.all()

            forces_by_region_month = {}
            for force in forces_data:
                fire = db.query(Fire).filter(Fire.id == force.fire_id).first()
                key = (fire.region, fire.date.month)
                if key not in forces_by_region_month:
                    forces_by_region_month[key] = []
                forces_by_region_month[key].append({
                    'force_type': force.force_type,
                    'people_count': force.people_count
                })

        return jsonify({
            'data': [{
                'region': escape(d[0]),
                'month': d[1],
                'count': d[2],
                'total_area': float(d[3]),
                'total_damage': float(d[4]) if d[4] else 0,
                'forces': forces_by_region_month.get((d[0], d[1]), [])
            } for d in stats_data],
            'map_data': [{
                'id': f.id,
                'latitude': float(f.latitude) if f.latitude else None,
                'longitude': float(f.longitude) if f.longitude else None,
                'region': escape(f.region),
                'date': str(f.date),
                'area': float(f.area)
            } for f in map_data],
            'total': total
        })

    @app.route('/api/analytics/predict', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def predict_fires():
        error, status = check_access(request.user['role'], ['admin', 'analyst'])
        if error:
            return error, status
        days_ahead = int(request.args.get('days_ahead', 30))
        model_type = request.args.get('model', 'linear')
        with SessionLocal() as db:
            data = db.query(Fire.date, Fire.area).order_by(Fire.date).all()
            if len(data) < 2:
                return jsonify({'success': False, 'message': 'Недостаточно данных для прогноза'}), 400
            dates = [d[0] for d in data]
            areas = [d[1] for d in data]
            if model_type == 'linear':
                X = np.array([d.toordinal() for d in dates]).reshape(-1, 1)
                y = np.array(areas)
                model = LinearRegression().fit(X, y)
                future_date = (datetime.now() + timedelta(days=days_ahead)).toordinal()
                prediction = model.predict([[future_date]])
            elif model_type == 'arima':
                model = ARIMA(areas, order=(5, 1, 0)).fit()
                prediction = model.forecast(steps=days_ahead)[-1]
            else:
                return jsonify({'success': False, 'message': 'Неподдерживаемый тип модели'}), 400
        return jsonify({
            'success': True,
            'predicted_area': float(prediction[0] if model_type == 'linear' else prediction),
            'date': (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        })

    @app.route('/api/analytics/pdf', methods=['GET'])
    @token_required
    def export_analytics_pdf():
        error, status = check_access(request.user['role'], ['admin', 'analyst'])
        if error:
            return error, status
        lang = request.args.get('lang', 'ru')
        year = request.args.get('year')
        month = request.args.get('month')
        is_summary = request.args.get('summary', 'false').lower() == 'true'
        with SessionLocal() as db:
            if is_summary:
                query = db.query(
                    Fire.region,
                    sql_func.count(Fire.id).label('count'),
                    sql_func.sum(Fire.area).label('total_area'),
                    sql_func.sum(Fire.damage_tenge).label('total_damage'),
                    sql_func.count(sql_func.distinct(Fire.created_by)).label('users_count')
                )
                if year:
                    query = query.filter(extract('year', Fire.date) == year)
                if month:
                    query = query.filter(extract('month', Fire.date) == month)
                data = query.group_by(Fire.region).all()
                title = LANGUAGES[lang]['summary']
                headers = [LANGUAGES[lang]['region'], LANGUAGES[lang]['count'], LANGUAGES[lang]['total_area'], 
                           LANGUAGES[lang]['total_damage'], LANGUAGES[lang]['users_count']]
                table_data = [headers] + [
                    [escape(d[0]), d[1], f"{float(d[2]):.2f}", f"{float(d[3]):.2f}" if d[3] else '0.00', d[4]] for d in data
                ]
            else:
                query = db.query(
                    Fire.region,
                    sql_func.month(Fire.date).label('month'),
                    sql_func.count(Fire.id).label('count'),
                    sql_func.sum(Fire.area).label('total_area'),
                    sql_func.sum(Fire.damage_tenge).label('total_damage')
                )
                if year:
                    query = query.filter(extract('year', Fire.date) == year)
                if month:
                    query = query.filter(extract('month', Fire.date) == month)
                data = query.group_by(Fire.region, sql_func.month(Fire.date)).all()
                title = LANGUAGES[lang]['analytics_title']
                headers = [LANGUAGES[lang]['region'], LANGUAGES[lang]['month'], LANGUAGES[lang]['count'], 
                           LANGUAGES[lang]['total_area'], LANGUAGES[lang]['total_damage']]
                month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'] if lang == 'ru' else ['Қаң', 'Ақп', 'Нау', 'Сәу', 'Мам', 'Мау', 'Шіл', 'Там', 'Қыр', 'Қаз', 'Қар', 'Жел']
                table_data = [headers] + [
                    [escape(d[0]), month_names[d[1] - 1], d[2], f"{float(d[3]):.2f}", f"{float(d[4]):.2f}" if d[4] else '0.00'] for d in data
                ]
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = [Paragraph(title, styles['Title']), Spacer(1, 12), Table(table_data)]
        doc.build(elements)
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{'summary' if is_summary else 'analytics'}_{year or 'all'}_{month or 'all'}.pdf"
        )

    @app.route('/summary')
    @login_required
    def summary_page():
        error, status = check_access(current_user.role, ['admin', 'analyst'])
        if error:
            return redirect(url_for('fires_page'))
        lang = request.args.get('lang', 'ru')
        return render_template('summary.html', lang=LANGUAGES[lang])

    @app.route('/api/summary', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def get_summary():
        error, status = check_access(request.user['role'], ['admin', 'analyst', 'engineer', 'operator'])
        if error:
            return error, status
        role = request.user['role']
        region = request.user['region']
        year = request.args.get('year')
        month = request.args.get('month')
        with SessionLocal() as db:
            query = db.query(
                Fire.region,
                sql_func.count(Fire.id).label('count'),
                sql_func.sum(Fire.area).label('total_area'),
                sql_func.sum(Fire.damage_tenge).label('total_damage'),
                sql_func.count(sql_func.distinct(Fire.created_by)).label('users_count')
            )
            if role in ['operator', 'engineer'] and region:
                query = query.filter(Fire.region == region)
            if year:
                query = query.filter(extract('year', Fire.date) == year)
            if month:
                query = query.filter(extract('month', Fire.date) == month)
            region_data = query.group_by(Fire.region).all()
            users_query = db.query(sql_func.count(sql_func.distinct(Fire.created_by)))
            if role in ['operator', 'engineer'] and region:
                users_query = users_query.filter(Fire.region == region)
            users_count = users_query.scalar()
        return jsonify({
            'regions': [{'region': escape(d[0]), 'count': d[1], 'total_area': float(d[2]), 
                         'total_damage': float(d[3]) if d[3] else 0, 'users_count': d[4]} for d in region_data],
            'users_count': users_count
        })

    @app.route('/users')
    @login_required
    def users_page():
        if current_user.role != 'admin':
            return redirect(url_for('fires_page'))
        lang = request.args.get('lang', 'ru')
        return render_template('users.html', regions=REGIONS, lang=LANGUAGES[lang])

    @app.route('/api/users', methods=['GET'])
    @token_required
    @cache.cached(timeout=60, query_string=True)
    def get_users():
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        with SessionLocal() as db:
            total = db.query(User).count()
            users = db.query(User).offset((page - 1) * per_page).limit(per_page).all()
        return jsonify({
            'users': [{'id': u.id, 'username': escape(u.username), 'role': u.role, 'region': u.region} for u in users],
            'total': total
        })

    @app.route('/api/users', methods=['POST'])
    @token_required
    def add_user():
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        data = request.form.to_dict()
        with SessionLocal() as db:
            if db.query(User).filter(User.username == data['username']).first():
                return jsonify({'success': False, 'message': 'Пользователь с таким именем уже существует'}), 400
            user = User(
                username=data['username'],
                role=data['role'],
                region=data['region'] if data['region'] else None
            )
            user.password = generate_password_hash(data['password'])
            db.add(user)
            db.commit()
            log_event(request.user['user_id'], 'INSERT', 'users', user.id, str({k: v for k, v in data.items() if k != 'password'}))
        return jsonify({'success': True, 'user_id': user.id})

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
    @token_required
    def edit_user(user_id):
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        data = request.form.to_dict()
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404
            user.username = data['username']
            if 'password' in data and data['password']:
                user.password = generate_password_hash(data['password'])
            user.role = data['role']
            user.region = data['region'] if data['region'] else None
            db.commit()
            log_event(request.user['user_id'], 'UPDATE', 'users', user.id, str({k: v for k, v in data.items() if k != 'password'}))
        return jsonify({'success': True})

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @token_required
    def delete_user(user_id):
        error, status = check_access(request.user['role'], ['admin'])
        if error:
            return error, status
        if user_id == request.user['user_id']:
            return jsonify({'success': False, 'message': 'Нельзя удалить самого себя'}), 403
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'message': 'Пользователь не найден'}), 404
            db.delete(user)
            db.commit()
            log_event(request.user['user_id'], 'DELETE', 'users', user_id)
        return jsonify({'success': True})

    @app.route('/api/weather', methods=['GET'])
    @token_required
    @cache.cached(timeout=300, query_string=True)
    async def get_weather():
        region = request.args.get('region')
        if not region:
            return jsonify({'error': 'Укажите регион'}), 400
        url = f"http://api.openweathermap.org/data/2.5/weather?q={region},KZ&appid={Config.OPENWEATHERMAP_API_KEY}&units=metric"
        @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
        async def fetch():
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return await response.json()
        try:
            data = await fetch()
            return jsonify({
                'temp': data['main']['temp'],
                'description': escape(data['weather'][0]['description'])
            })
        except Exception as e:
            logger.error(f"Ошибка API погоды: {str(e)}")
            return jsonify({'error': 'Данные о погоде недоступны'}), 503

    @app.route('/api/firms', methods=['GET'])
    @token_required
    @cache.cached(timeout=300, query_string=True)
    async def get_firms_data():
        lat_min = request.args.get('lat_min', 40)
        lat_max = request.args.get('lat_max', 55)
        lon_min = request.args.get('lon_min', 51)
        lon_max = request.args.get('lon_max', 80)
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{Config.NASA_FIRMS_API_KEY}/VIIRS_SNPP_NRT/{lon_min},{lat_min},{lon_max},{lat_max}/1"
        @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
        async def fetch():
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return await response.text()
        try:
            text = await fetch()
            lines = text.splitlines()
            reader = csv.DictReader(lines)
            fires = [{'latitude': float(row['latitude']), 'longitude': float(row['longitude']),
                      'acq_date': row['acq_date'], 'confidence': row['confidence']} for row in reader]
            return jsonify(fires)
        except Exception as e:
            logger.error(f"Ошибка API FIRMS: {str(e)}")
            return jsonify({'error': 'Данные FIRMS недоступны'}), 503

    @app.route('/analytics/export/csv', methods=['GET'])
    @token_required
    def export_analytics_csv():
        error, status = check_access(request.user['role'], ['admin', 'analyst', 'engineer', 'operator'])
        if error:
            return error, status
        role = request.user['role']
        region = request.user['region']
        year = request.args.get('year')
        month = request.args.get('month')
        with SessionLocal() as db:
            query = db.query(Fire)
            if role in ['operator', 'engineer'] and region:
                query = query.filter(Fire.region == region)
            if year:
                query = query.filter(extract('year', Fire.date) == year)
            if month:
                query = query.filter(extract('month', Fire.date) == month)
            fires = query.all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Дата', 'Регион', 'КГУ/ООПТ', 'Площадь', 'Описание', 'Файл', 'Создал'])
        writer.writerows([(f.id, f.date, escape(f.region), f.kgu_oopt_id, f.area, escape(f.description), f.file_path, f.created_by) for f in fires])
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'fires_export_{year or "all"}_{month or "all"}.csv'
        )

    @app.route('/manifest.json')
    def manifest():
        return {
            "name": "Forest Fires Platform",
            "short_name": "Fires",
            "start_url": "/fires",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#007bff",
            "icons": [
                {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
            ]
        }

    @app.route('/service-worker.js')
    def service_worker():
        return app.send_static_file('service-worker.js')

    def log_event(username, action, table_name, record_id, changes=None):
        with SessionLocal() as db:
            log = AuditLog(
                timestamp=datetime.utcnow(),
                username=username,
                action=action,
                table_name=table_name,
                record_id=record_id,
                changes=changes
            )
            db.add(log)
            db.commit()

    def translate_changes(changes):
        if not changes:
            return "Нет изменений"
        translated_changes = []
        for change in changes.split("; "):
            if ": " in change:
                column, values = change.split(": ", 1)
                column_translations = {
                    'damage_area': 'Площадь пожара',
                    'damage_les': 'Лесная площадь',
                    'LO_people_count': 'Кол-во людей ЛО',
                    # Добавить остальные переводы
                }
                translated_column = column_translations.get(column, column)
                translated_changes.append(f"{translated_column}: {values}")
        return "; ".join(translated_changes)

    @app.context_processor
    def utility_processor():
        def translate_value(value):
            if value is None:
                return ""
            if value is True:
                return "Да"
            if value is False:
                return "Нет"
            return value
        return dict(translate_value=translate_value, translate_changes=translate_changes)

    @socketio.on('connect')
    def handle_connect():
        logger.info('Клиент подключен')

if __name__ == '__main__':
    register_routes(app, socketio, cache, csrf)
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host="0.0.0.0", port=8080)