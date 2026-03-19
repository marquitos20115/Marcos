from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps
import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = os.environ.get("SECRET_KEY", "clave_local_solo_desarrollo")

DATABASE = os.path.join(BASE_DIR, "tareas.db")

MAIL_REMITENTE = "lucycastro007@hotmail.com"
MAIL_PASSWORD = "TU_CLAVE_DE_APLICACION"
MAIL_DESTINO = "lucycastro007@hotmail.com"

PROFESIONAL_NOMBRE = "Lucy Catherine Castro"

HORARIOS_DISPONIBLES = [
    "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "12:30",
    "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00"
]


@app.context_processor
def inject_global_data():
    return {
        "profesional_nombre": PROFESIONAL_NOMBRE
    }


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def enviar_mail_solicitud_paciente(
    nombre_paciente,
    email_paciente,
    especialidad,
    motivo_consulta,
    prioridad,
    fecha_turno,
    hora_turno
):
    if not MAIL_REMITENTE or not MAIL_PASSWORD or not MAIL_DESTINO:
        print("Faltan variables de entorno de correo.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = MAIL_REMITENTE
        msg["To"] = MAIL_DESTINO
        msg["Subject"] = f"Nueva solicitud de turno - {nombre_paciente}"

        cuerpo = f"""
Nueva solicitud de turno recibida

Profesional: {PROFESIONAL_NOMBRE}
Paciente: {nombre_paciente}
Correo del paciente: {email_paciente}
Especialidad: {especialidad}
Motivo de consulta: {motivo_consulta}
Prioridad: {prioridad}
Fecha del turno: {fecha_turno}
Hora del turno: {hora_turno}
        """

        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        servidor = smtplib.SMTP("smtp.office365.com", 587)
        servidor.starttls()
        servidor.login(MAIL_REMITENTE, MAIL_PASSWORD)
        servidor.sendmail(MAIL_REMITENTE, [MAIL_DESTINO], msg.as_string())
        servidor.quit()
        return True

    except Exception as e:
        print("Error al enviar mail:", e)
        return False


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL UNIQUE,
            nombre_completo TEXT NOT NULL,
            cedula TEXT NOT NULL,
            edad TEXT NOT NULL,
            telefono TEXT NOT NULL,
            email TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            especialidad TEXT NOT NULL,
            motivo_consulta TEXT NOT NULL,
            prioridad TEXT NOT NULL,
            fecha_turno TEXT NOT NULL,
            hora_turno TEXT NOT NULL,
            observaciones_profesional TEXT,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            derivado TEXT NOT NULL DEFAULT 'No',
            especialidad_derivada TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        )
    """)

    conn.commit()

    profesional = conn.execute(
        "SELECT id FROM usuarios WHERE usuario = ?",
        ("lucy",)
    ).fetchone()

    if not profesional:
        conn.execute("""
            INSERT INTO usuarios (nombre, usuario, password, rol)
            VALUES (?, ?, ?, ?)
        """, (
            PROFESIONAL_NOMBRE,
            "lucy",
            generate_password_hash("Lucy12345"),
            "profesional"
        ))
        conn.commit()

    conn.close()


def login_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def profesional_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "profesional":
            return redirect(url_for("panel_paciente"))
        return func(*args, **kwargs)
    return wrapper


def paciente_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "paciente":
            return redirect(url_for("home"))
        return func(*args, **kwargs)
    return wrapper


def validar_cedula(cedula):
    cedula_limpia = cedula.replace(".", "").replace("-", "").replace(" ", "")
    return cedula_limpia.isdigit() and 7 <= len(cedula_limpia) <= 8


def validar_edad(edad):
    if not edad.isdigit():
        return False
    edad_num = int(edad)
    return 0 < edad_num <= 120


def validar_telefono_uruguay(telefono):
    tel = telefono.replace(" ", "").replace("-", "")
    if tel.startswith("+598"):
        tel = tel[4:]
    return tel.isdigit() and len(tel) == 9 and tel.startswith("09")


def validar_email(email):
    patron = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(patron, email) is not None


def es_dia_habil(fecha_texto):
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d")
        return fecha.weekday() < 6  # lunes a sábado
    except ValueError:
        return False


def fecha_no_pasada(fecha_texto):
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
        return fecha >= date.today()
    except ValueError:
        return False


def turno_ya_ocupado(fecha_turno, hora_turno):
    conn = get_connection()
    existente = conn.execute("""
        SELECT id FROM turnos
        WHERE fecha_turno = ? AND hora_turno = ? AND estado != 'Cancelado'
    """, (fecha_turno, hora_turno)).fetchone()
    conn.close()
    return existente is not None


@app.route("/")
@login_requerido
def home():
    if session.get("rol") == "profesional":
        return render_template("index.html", usuario=session.get("usuario_nombre"))
    return redirect(url_for("panel_paciente"))


@app.route("/registro")
def registro():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?",
            (usuario,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["usuario_id"] = user["id"]
            session["usuario_nombre"] = user["nombre"]
            session["usuario_user"] = user["usuario"]
            session["rol"] = user["rol"]

            if user["rol"] == "profesional":
                return redirect(url_for("home"))
            return redirect(url_for("panel_paciente"))
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profesional/pacientes")
@login_requerido
@profesional_requerido
def lista_pacientes():
    conn = get_connection()
    pacientes = conn.execute("""
        SELECT pacientes.*, usuarios.usuario
        FROM pacientes
        JOIN usuarios ON pacientes.usuario_id = usuarios.id
        ORDER BY pacientes.nombre_completo ASC
    """).fetchall()
    conn.close()

    return render_template(
        "lista_pacientes.html",
        pacientes=pacientes,
        usuario=session.get("usuario_nombre")
    )


@app.route("/profesional/pacientes/crear", methods=["GET", "POST"])
@login_requerido
@profesional_requerido
def crear_paciente():
    error = None
    success = None

    if request.method == "POST":
        nombre_completo = request.form.get("nombre_completo", "").strip()
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()
        cedula = request.form.get("cedula", "").strip()
        edad = request.form.get("edad", "").strip()
        telefono = request.form.get("telefono", "").strip()
        email = request.form.get("email", "").strip()

        if not nombre_completo or not usuario or not password or not cedula or not edad or not telefono or not email:
            error = "Completá todos los campos obligatorios."
        elif not validar_cedula(cedula):
            error = "La cédula de identificación no es válida."
        elif not validar_edad(edad):
            error = "La edad ingresada no es válida."
        elif not validar_telefono_uruguay(telefono):
            error = "El teléfono no es válido. Debe ser de Uruguay, por ejemplo: 099123456."
        elif not validar_email(email):
            error = "El correo electrónico no es válido."
        else:
            conn = get_connection()

            existente = conn.execute(
                "SELECT id FROM usuarios WHERE usuario = ?",
                (usuario,)
            ).fetchone()

            if existente:
                error = "Ese nombre de usuario ya existe."
            else:
                conn.execute("""
                    INSERT INTO usuarios (nombre, usuario, password, rol)
                    VALUES (?, ?, ?, ?)
                """, (
                    nombre_completo,
                    usuario,
                    generate_password_hash(password),
                    "paciente"
                ))
                conn.commit()

                nuevo_usuario = conn.execute(
                    "SELECT id FROM usuarios WHERE usuario = ?",
                    (usuario,)
                ).fetchone()

                conn.execute("""
                    INSERT INTO pacientes (
                        usuario_id, nombre_completo, cedula, edad, telefono, email
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    nuevo_usuario["id"],
                    nombre_completo,
                    cedula.replace(".", "").replace("-", "").replace(" ", ""),
                    edad,
                    telefono,
                    email
                ))
                conn.commit()
                success = "Paciente creado correctamente."

            conn.close()

    return render_template(
        "crear_paciente.html",
        error=error,
        success=success,
        usuario=session.get("usuario_nombre")
    )


@app.route("/paciente")
@login_requerido
@paciente_requerido
def panel_paciente():
    conn = get_connection()

    paciente = conn.execute("""
        SELECT * FROM pacientes
        WHERE usuario_id = ?
    """, (session["usuario_id"],)).fetchone()

    turnos = []
    if paciente:
        turnos = conn.execute("""
            SELECT * FROM turnos
            WHERE paciente_id = ?
            ORDER BY fecha_turno ASC, hora_turno ASC
        """, (paciente["id"],)).fetchall()

    conn.close()

    return render_template(
        "panel_paciente.html",
        usuario=session.get("usuario_nombre"),
        paciente=paciente,
        turnos=turnos
    )


@app.route("/paciente/solicitar-turno", methods=["GET", "POST"])
@login_requerido
@paciente_requerido
def solicitar_turno():
    error = None
    success = None

    conn = get_connection()
    paciente = conn.execute("""
        SELECT * FROM pacientes WHERE usuario_id = ?
    """, (session["usuario_id"],)).fetchone()

    if not paciente:
        conn.close()
        return "No tenés un perfil de paciente creado. La profesional debe crear tu perfil primero."

    if request.method == "POST":
        especialidad = request.form.get("especialidad", "").strip()
        motivo_consulta = request.form.get("motivo_consulta", "").strip()
        prioridad = request.form.get("prioridad", "").strip()
        fecha_turno = request.form.get("fecha_turno", "").strip()
        hora_turno = request.form.get("hora_turno", "").strip()

        if not especialidad or not motivo_consulta or not prioridad or not fecha_turno or not hora_turno:
            error = "Completá todos los campos."
        elif not fecha_no_pasada(fecha_turno):
            error = "No podés seleccionar una fecha pasada."
        elif not es_dia_habil(fecha_turno):
            error = "Solo se pueden solicitar turnos de lunes a sábado."
        elif hora_turno not in HORARIOS_DISPONIBLES:
            error = "El horario seleccionado no es válido."
        elif turno_ya_ocupado(fecha_turno, hora_turno):
            error = "Ese turno ya está ocupado. Elegí otro horario."
        else:
            conn.execute("""
                INSERT INTO turnos (
                    paciente_id, especialidad, motivo_consulta, prioridad,
                    fecha_turno, hora_turno
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                paciente["id"],
                especialidad,
                motivo_consulta,
                prioridad,
                fecha_turno,
                hora_turno
            ))
            conn.commit()

            enviar_mail_solicitud_paciente(
                paciente["nombre_completo"],
                paciente["email"],
                especialidad,
                motivo_consulta,
                prioridad,
                fecha_turno,
                hora_turno
            )

            success = "Turno solicitado correctamente."

    conn.close()

    return render_template(
        "solicitud_turno.html",
        error=error,
        success=success,
        horarios=HORARIOS_DISPONIBLES,
        usuario=session.get("usuario_nombre")
    )


@app.route("/profesional/turnos")
@login_requerido
@profesional_requerido
def admin_solicitudes():
    conn = get_connection()

    turnos = conn.execute("""
        SELECT turnos.*, pacientes.nombre_completo, pacientes.cedula, pacientes.edad,
               pacientes.telefono, pacientes.email
        FROM turnos
        JOIN pacientes ON turnos.paciente_id = pacientes.id
        ORDER BY
            CASE turnos.estado
                WHEN 'Pendiente' THEN 1
                WHEN 'Confirmada' THEN 2
                WHEN 'Respondida' THEN 3
                WHEN 'Derivada' THEN 4
                ELSE 5
            END,
            turnos.fecha_turno ASC,
            turnos.hora_turno ASC
    """).fetchall()

    total = conn.execute("SELECT COUNT(*) AS total FROM turnos").fetchone()["total"]
    pendientes = conn.execute("SELECT COUNT(*) AS total FROM turnos WHERE estado = 'Pendiente'").fetchone()["total"]
    confirmadas = conn.execute("SELECT COUNT(*) AS total FROM turnos WHERE estado = 'Confirmada'").fetchone()["total"]
    derivadas = conn.execute("SELECT COUNT(*) AS total FROM turnos WHERE estado = 'Derivada'").fetchone()["total"]

    conn.close()

    return render_template(
        "admin_solicitudes.html",
        solicitudes=turnos,
        usuario=session.get("usuario_nombre"),
        total=total,
        pendientes=pendientes,
        confirmadas=confirmadas,
        derivadas=derivadas
    )


@app.route("/profesional/turnos/confirmar/<int:turno_id>", methods=["POST"])
@login_requerido
@profesional_requerido
def confirmar_turno(turno_id):
    conn = get_connection()
    conn.execute("""
        UPDATE turnos
        SET estado = 'Confirmada'
        WHERE id = ?
    """, (turno_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_solicitudes"))


@app.route("/profesional/turnos/responder/<int:turno_id>", methods=["POST"])
@login_requerido
@profesional_requerido
def responder_solicitud(turno_id):
    conn = get_connection()
    conn.execute("""
        UPDATE turnos
        SET estado = 'Respondida'
        WHERE id = ?
    """, (turno_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_solicitudes"))


@app.route("/profesional/turnos/derivar/<int:turno_id>", methods=["POST"])
@login_requerido
@profesional_requerido
def derivar_psiquiatria(turno_id):
    conn = get_connection()
    conn.execute("""
        UPDATE turnos
        SET derivado = 'Sí',
            especialidad_derivada = 'Psiquiatría',
            estado = 'Derivada'
        WHERE id = ?
    """, (turno_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_solicitudes"))


@app.route("/profesional/turnos/observacion/<int:turno_id>", methods=["POST"])
@login_requerido
@profesional_requerido
def guardar_observacion(turno_id):
    observaciones = request.form.get("observaciones_profesional", "").strip()

    conn = get_connection()
    conn.execute("""
        UPDATE turnos
        SET observaciones_profesional = ?
        WHERE id = ?
    """, (observaciones, turno_id))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_solicitudes"))


@app.route("/profesional/turnos/eliminar/<int:turno_id>", methods=["POST"])
@login_requerido
@profesional_requerido
def eliminar_solicitud(turno_id):
    conn = get_connection()
    conn.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_solicitudes"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)