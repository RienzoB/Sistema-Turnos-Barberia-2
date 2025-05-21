from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from config import Config
from models import db, Appointment, Product, Order, User
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
from flask import jsonify, request
from datetime import datetime, time
from forms import ChangePasswordForm

import stripe

app = Flask(__name__)
app.config.from_object(Config)

# Extensiones
db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)
stripe.api_key = app.config['STRIPE_SECRET_KEY']
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    # Crear admin si no existe
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password_hash=generate_password_hash('admin123'))
        db.session.add(admin)
        db.session.commit()

# Funciones auxiliares
def dentro_horario(dt: datetime):
    wd, t = dt.weekday(), dt.time()
    horarios = {0:(time(15,0),time(20,0)),1:(time(9,0),time(20,0)),2:(time(9,0),time(20,0)),3:(time(9,0),time(20,0)),4:(time(9,0),time(20,0)),5:(time(9,0),time(18,0))}
    if wd==6: return False
    inicio,fin = horarios[wd]
    return inicio<=t<fin

def send_confirmation_email(appt):
    msg=Message('Confirmación Turno', recipients=[appt.customer_email])
    msg.body=f"Hola {appt.customer_name}, tu turno para {appt.service} es el {appt.start}.\nContacto: +54 9 11 1234-5678, Av Brasil 1669, Rosario"
    mail.send(msg)

# Rutas públicas
@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password_hash, request.form['password']):
            login_user(u)
            return redirect(url_for('admin'))
        flash('Credenciales incorrectas','danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('login'))

@app.route('/agendar', methods=['GET','POST'])
def agendar():
    if request.method=='POST':
        nombre,email,serv=request.form['nombre'],request.form['email'],request.form['servicio']
        inicio=datetime.fromisoformat(request.form['fecha_hora'])
        dur=Appointment.duration_for(serv)
        fin=inicio+dur
        if not dentro_horario(inicio): flash('Fuera de horario','danger');return redirect('agendar')
        sod=datetime.combine(inicio.date(),time.min)
        eod=datetime.combine(inicio.date(),time.max)
        conf=Appointment.query.filter(Appointment.start>=sod,Appointment.start<=eod,Appointment.start<fin,Appointment.end>inicio).all()
        if conf: flash('Ya hay reserva','danger');return redirect('agendar')
        appt=Appointment(customer_name=nombre,customer_email=email,service=serv,start=inicio,end=fin)
        db.session.add(appt); db.session.commit()
        send_confirmation_email(appt)
        flash('Turno confirmado','success'); return redirect(url_for('index'))
    return render_template('agendar.html')

@app.route('/api/turnos')
def api_turnos():
    return jsonify({'turnos':[t[0].isoformat() for t in Appointment.query.with_entities(Appointment.start).all()]})

@app.route('/horarios_disponibles')
def horarios_disponibles():
    from datetime import datetime, time as _time, timedelta

    # Parámetros recibidos
    fecha = request.args.get('fecha')       # ej. "2025-05-21"
    servicio = request.args.get('servicio') # "Corte" o "Corte + Barba"

    # Validación básica
    if not fecha or not servicio:
        return jsonify([])

    # Parsear la fecha
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    # Ventanas de atención según día de la semana (0=Dom, 6=Sáb)
    horarios_dia = {
        0: None,  # Domingo cerrado
        1: (_time(15, 0), _time(20, 0)),  # Lunes
        2: (_time(9, 0),  _time(20, 0)),  # Martes
        3: (_time(9, 0),  _time(20, 0)),  # Miércoles
        4: (_time(9, 0),  _time(20, 0)),  # Jueves
        5: (_time(9, 0),  _time(20, 0)),  # Viernes
        6: (_time(9, 0),  _time(18, 0)),  # Sábado
    }
    ventana = horarios_dia.get(fecha_obj.weekday())
    if ventana is None:
        # Día cerrado
        return jsonify([])

    inicio_h, fin_h = ventana
    duracion = Appointment.duration_for(servicio)

    # Obtengo todas las reservas de ese día
    start_day = datetime.combine(fecha_obj, _time.min)
    end_day   = datetime.combine(fecha_obj, _time.max)
    reservas = Appointment.query.filter(
        Appointment.start >= start_day,
        Appointment.start <= end_day
    ).all()

    # Genero slots cada 10 minutos dentro de la ventana
    slots = []
    actual = datetime.combine(fecha_obj, inicio_h)
    ultimo_inicio = datetime.combine(fecha_obj, fin_h) - duracion

    while actual <= ultimo_inicio:
        # Compruebo que no choque con reserva existente
        if not any(r.start < actual + duracion and r.end > actual for r in reservas):
            slots.append(actual.strftime('%H:%M'))
        actual += timedelta(minutes=10)

    return jsonify(slots)

@app.route('/admin')
@login_required
def admin():
    appts=Appointment.query.order_by(Appointment.start).all()
    return render_template('admin.html', appts=appts)

@app.route('/admin/delete/<int:id>')
@login_required
def admin_delete(id):
    a=Appointment.query.get_or_404(id)
    db.session.delete(a); db.session.commit()
    flash('Reserva eliminada','info'); return redirect(url_for('admin'))

if __name__=='__main__': app.run(debug=True)


@app.route('/change_password', methods=['GET','POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Verificar contraseña actual
        if not check_password_hash(current_user.password_hash,
                                   form.current_password.data):
            flash('Contraseña actual incorrecta', 'danger')
            return redirect(url_for('change_password'))

        # Actualizar con la nueva
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('Contraseña actualizada con éxito', 'success')
        return redirect(url_for('admin'))

    return render_template('change_password.html', form=form)
