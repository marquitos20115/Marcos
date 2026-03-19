from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = "tareas.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            objetivo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            prioridad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT,
            estado TEXT NOT NULL,
            descripcion TEXT,
            notas TEXT
        )
    """)
    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        objetivo = request.form.get("objetivo", "").strip()
        categoria = request.form.get("categoria", "").strip()
        prioridad = request.form.get("prioridad", "").strip()
        fecha = request.form.get("fecha", "").strip()
        hora = request.form.get("hora", "").strip()
        estado = request.form.get("estado", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        notas = request.form.get("notas", "").strip()

        if titulo and objetivo and categoria and prioridad and fecha and estado:
            conn = get_connection()
            conn.execute("""
                INSERT INTO tareas (
                    titulo, objetivo, categoria, prioridad, fecha, hora, estado, descripcion, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (titulo, objetivo, categoria, prioridad, fecha, hora, estado, descripcion, notas))
            conn.commit()
            conn.close()

        return redirect(url_for("home"))

    conn = get_connection()
    tareas = conn.execute("""
        SELECT * FROM tareas
        ORDER BY
            CASE prioridad
                WHEN 'Alta' THEN 1
                WHEN 'Media' THEN 2
                WHEN 'Baja' THEN 3
                ELSE 4
            END,
            fecha ASC,
            hora ASC
    """).fetchall()
    conn.close()

    return render_template("index.html", tareas=tareas)


@app.route("/completar/<int:tarea_id>", methods=["POST"])
def completar_tarea(tarea_id):
    conn = get_connection()
    conn.execute("""
        UPDATE tareas
        SET estado = 'Completada'
        WHERE id = ?
    """, (tarea_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


@app.route("/eliminar/<int:tarea_id>", methods=["POST"])
def eliminar_tarea(tarea_id):
    conn = get_connection()
    conn.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
