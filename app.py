from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_NAME = "tareas.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto TEXT NOT NULL,
            completada INTEGER NOT NULL DEFAULT 0,
            creada_en TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        texto = request.form.get("tarea", "").strip()

        if texto:
            conn = get_connection()
            conn.execute(
                "INSERT INTO tareas (texto, completada, creada_en) VALUES (?, ?, ?)",
                (texto, 0, datetime.now().strftime("%d/%m/%Y %H:%M"))
            )
            conn.commit()
            conn.close()

        return redirect("/")

    conn = get_connection()
    tareas = conn.execute("SELECT * FROM tareas ORDER BY id DESC").fetchall()
    conn.close()

    tareas_totales = len(tareas)
    tareas_completadas = sum(1 for tarea in tareas if tarea["completada"] == 1)

    return render_template(
        "index.html",
        tareas=tareas,
        tareas_totales=tareas_totales,
        tareas_completadas=tareas_completadas
    )


@app.route("/completar/<int:tarea_id>")
def completar(tarea_id):
    conn = get_connection()
    tarea = conn.execute(
        "SELECT completada FROM tareas WHERE id = ?",
        (tarea_id,)
    ).fetchone()

    if tarea:
        nuevo_estado = 0 if tarea["completada"] == 1 else 1
        conn.execute(
            "UPDATE tareas SET completada = ? WHERE id = ?",
            (nuevo_estado, tarea_id)
        )
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/eliminar/<int:tarea_id>")
def eliminar(tarea_id):
    conn = get_connection()
    conn.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
