from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

tareas = []

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        titulo = request.form.get("titulo")
        objetivo = request.form.get("objetivo")
        categoria = request.form.get("categoria")
        prioridad = request.form.get("prioridad")
        fecha = request.form.get("fecha")
        hora = request.form.get("hora")
        estado = request.form.get("estado")
        descripcion = request.form.get("descripcion")
        notas = request.form.get("notas")

        nueva_tarea = {
            "titulo": titulo,
            "objetivo": objetivo,
            "categoria": categoria,
            "prioridad": prioridad,
            "fecha": fecha,
            "hora": hora,
            "estado": estado,
            "descripcion": descripcion,
            "notas": notas
        }

        tareas.append(nueva_tarea)
        return redirect(url_for("home"))

    return render_template("index.html", tareas=tareas)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
