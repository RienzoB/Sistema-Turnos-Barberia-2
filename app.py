from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Appointment, Product, Order
from flask_mail import Mail, Message
from datetime import datetime, time
import stripe

app = Flask(__name__)
app.config.from_object(Config)

# Extensiones
db.init_app(app)
mail = Mail(app)
stripe.api_key = app.config['STRIPE_SECRET_KEY']

with app.app_context():
    db.create_all()

# ----- Funciones auxiliares -----

def dentro_horario(dt: datetime):
    wd, t = dt.weekday(), dt.time()
    horarios = {
        0: (time(15,0), time(20,0)),
        1: (time(9,0), time(20,0)),
        2: (time(9,0), time(20,0)),
        3: (time(9,0), time(20,0)),
        4: (time(9,0), time(20,0)),
        5: (time(9,0), time(18,0)),
    }
    if wd == 6:
        return False
    inicio, fin = horarios[wd]
    return inicio <= t < fin

# Función de envío de email
def send_confirmation_email(appointment):
     msg = Message(
        subject='Confirmación de Turno - Star Barbers',
        recipients=[appointment.customer_email]
     )
     msg.body = f"Hola {appointment.customer_name},\n\nTu turno para '{appointment.service}' está confirmado el {appointment.start}.\n¡Te esperamos!"
     mail.send(msg)

# ----- Rutas -----

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agendar', methods=['GET','POST'])
def agendar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        servicio = request.form['servicio']
        inicio = datetime.fromisoformat(request.form['fecha_hora'])
        dur = Appointment.duration_for(servicio)
        if not dentro_horario(inicio):
            flash('Horario fuera de atención', 'danger')
            return redirect(url_for('agendar'))
        cita = Appointment(
            customer_name=nombre,
            customer_email=email,
            service=servicio,
            start=inicio,
            end=inicio+dur
        )
        db.session.add(cita)
        db.session.commit()

        # Envío de email
        send_confirmation_email(cita)

        flash('Cita agendada y correo enviado!', 'success')
        return redirect(url_for('index'))
    return render_template('agendar.html')

# Resto de rutas e-commerce...
# (igual que antes)