from flask import Flask, render_template, request, redirect
import os

app = Flask(__name__)

tareas = []


@app.route('/', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        texto = request.form.get('tarea', '').strip()

        if texto:
            tareas.append({
                'texto': texto,
                'completada': False
            })

        return redirect('/')

    tareas_totales = len(tareas)
    tareas_completadas = sum(1 for tarea in tareas if tarea['completada'])

    return render_template(
        'index.html',
        tareas=tareas,
        tareas_totales=tareas_totales,
        tareas_completadas=tareas_completadas
    )


@app.route('/eliminar/<int:index>')
def eliminar(index):
    if 0 <= index < len(tareas):
        tareas.pop(index)
    return redirect('/')


@app.route('/completar/<int:index>')
def completar(index):
    if 0 <= index < len(tareas):
        tareas[index]['completada'] = not tareas[index]['completada']
    return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
