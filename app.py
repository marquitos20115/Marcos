from flask import Flask, render_template, request, redirect
import os

app = Flask(__name__)

tareas = []

@app.route('/', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        nueva_tarea = request.form.get('tarea')
        if nueva_tarea:
            tareas.append(nueva_tarea)
    return render_template('index.html', tareas=tareas)

@app.route('/eliminar/<int:index>')
def eliminar(index):
    if 0 <= index < len(tareas):
        tareas.pop(index)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))