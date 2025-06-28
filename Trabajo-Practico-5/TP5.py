# app.py
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
import random
import io
import os
from datetime import datetime

app = Flask(__name__)

# --- Variables globales para almacenar los datos de Euler ---
euler_data_storage = {}

def resolver_euler(C, T, h, d_corte):
    """
    Resuelve la ecuación diferencial dD/dt = C + 0.2*T + t^2 usando el método de Euler.
    Devuelve el tiempo 't' final, el valor 'D' final, y un DataFrame con los pasos
    INCLUYENDO la primera fila que supera dicho umbral.
    """
    t = 0
    D = 0
    dD_dt_func = lambda t_actual, D_actual: C + 0.2 * T + t_actual**2
    pasos = []
    
    while D <= d_corte:
        dD_dt_valor = dD_dt_func(t, D)
        f_por_h = dD_dt_valor * h
        D_siguiente = D + f_por_h
        
        pasos.append({
            't (minutos)': t, 
            'D (valor actual)': D, 
            'dD/dt': dD_dt_valor,
            'f(t,D)*h': f_por_h,
            'D_i+1': D_siguiente
        })
        
        D = D_siguiente
        t += h
    
    t_final = t - h 
    D_final = D 
    pasos_df = pd.DataFrame(pasos)
    return t_final, D_final, pasos_df

@app.route('/')
def index():
    """Muestra el formulario inicial."""
    return render_template('index.html')

@app.route('/descargar_euler', methods=['POST'])
def descargar_euler():
    """Genera y envía el archivo Excel con los pasos de Euler para un cliente específico."""
    global euler_data_storage
    try:
        paso_h = float(request.form.get('paso_h_euler'))
        cliente_id_str = request.form.get('cliente_id_euler')
        dia_str = request.form.get('dia_euler')
        
        if not cliente_id_str or not dia_str:
            return "Por favor, ingrese un día y un ID de cliente.", 400
            
        cliente_id = int(cliente_id_str)
        dia = int(dia_str)
            
    except (ValueError, TypeError):
        return "Parámetros inválidos.", 400
        
    if dia in euler_data_storage and cliente_id in euler_data_storage[dia]:
        datos_cliente = euler_data_storage[dia][cliente_id]
        C, T, d_corte = datos_cliente['C'], datos_cliente['T'], datos_cliente['d_corte']
        t_final, D_final, pasos_df = resolver_euler(C, T, h=paso_h, d_corte=d_corte)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            sheet_name = f'Euler_Cliente_{cliente_id}'
            
            pasos_df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=10)
            
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#4F81BD', 'align': 'center', 'valign': 'vcenter', 'border': 1})
            value_format = workbook.add_format({'align': 'right', 'border': 1, 'num_format': '0.00'})
            value_format_h = workbook.add_format({'align': 'right', 'border': 1, 'num_format': '0.000'})
            label_format = workbook.add_format({'bold': True, 'align': 'left', 'border': 1})
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
            formula_format = workbook.add_format({'italic': True, 'align': 'center', 'valign': 'vcenter'})

            worksheet.merge_range('A1:E1', f'Detalles del Cálculo de Euler (Cliente {cliente_id}, Día {dia})', title_format)
            worksheet.merge_range('A2:E2', 'Ecuación Diferencial: dD/dt = C + 0.2*T + t^2', formula_format)
            
            worksheet.merge_range('A4:B4', 'Parámetros de Entrada', header_format)
            worksheet.write('A5', 'C (Cola)', label_format)
            worksheet.write('B5', C, value_format)
            worksheet.write('A6', 'T (Random Atención)', label_format)
            worksheet.write('B6', T, value_format)
            worksheet.write('A7', 'Paso (h)', label_format)
            worksheet.write('B7', paso_h, value_format_h)

            worksheet.merge_range('D4:E4', 'Condiciones y Resultados', header_format)
            worksheet.write('D5', 'Condición Inicial D(0)', label_format)
            worksheet.write('E5', 0, value_format)
            worksheet.write('D6', f'D Corte (> {d_corte})', label_format)
            worksheet.write('E6', D_final, value_format)
            worksheet.write('D7', 't final (min)', label_format)
            worksheet.write('E7', t_final, value_format)

            worksheet.merge_range('A10:E10', 'Pasos de la Integración Numérica', header_format)
            
            worksheet.set_column('A:E', 25)

        output.seek(0)
        
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f'calculo_euler_dia{dia}_cliente{cliente_id}.xlsx')
    return f"No se encontraron datos de Euler para el cliente {cliente_id} en el día {dia}.", 404

@app.route('/simular', methods=['POST'])
def simular():
    """Ejecuta la simulación principal."""
    global euler_data_storage
    euler_data_storage.clear()
    
    try:
        tiempo_simulacion_valor = int(request.form['tiempo_simulacion'])
        unidad_tiempo = request.form.get('unidad_tiempo', 'horas')
        max_filas_a_mostrar = int(request.form['cantidad_iteraciones'])  # Límite para mostrar, no para simular.
        hora_comienzo_display = int(request.form['hora_comienzo'])
        paso_h_inicial = float(request.form['paso_h_euler'])
        llegada_a = float(request.form['llegada_a'])
        llegada_b = float(request.form['llegada_b'])
        atencion_a = float(request.form['atencion_a'])
        atencion_b = float(request.form['atencion_b'])
        d_corte = float(request.form['d_corte'])
    except (ValueError, KeyError) as e:
        return f"Error en los parámetros de entrada: {e}. Por favor, verifique los valores.", 400

    if llegada_a >= llegada_b or atencion_a >= atencion_b:
        return "Error: El valor de 'b' debe ser mayor que el valor de 'a' para las distribuciones.", 400
        
    dias_a_simular = 0
    tiempo_a_simular_min = float('inf') 
    original_tiempo_sim_min = 0 
    if unidad_tiempo == 'dias':
        dias_a_simular = tiempo_simulacion_valor
        # Para el caso días, calculamos el tiempo total en minutos para mostrar la fila final:
        original_tiempo_sim_min = dias_a_simular * 480.0  # 480 min = 8 horas por día
        tiempo_a_simular_min = original_tiempo_sim_min + 0.000001
    else:
        original_tiempo_sim_min = tiempo_simulacion_valor * 60
        tiempo_a_simular_min = original_tiempo_sim_min + 0.000001

    vector_estado = []
    reloj = 0.0 
    dia = 1
    evento = "Inicio de Día"
    tiempo_dias_completos = 0.0
    cliente_n_dia = 0
    cliente_en_atencion_id = None
    cola_clientes = [] 
    clientes_impacientes = 0
    clientes_atendidos = 0
    dias_cierre_a_horario = 0
    inicio_atencion_tiempos = {}
    duracion_servicios = {}
    acumulador_tiempo_atencion = 0.0
    cliente_siendo_atendido = "-"
    
    rnd_llegada = round(random.random(), 2)
    tiempo_llegada = llegada_a + (llegada_b - llegada_a) * rnd_llegada
    proxima_llegada = reloj + tiempo_llegada
    
    rnd_atencion, T_atencion, duracion_atencion_actual = "-", "-", "-"
    fin_atencion = float('inf')

    estilista_estado = "Libre"
    fin_recepcion_clientes = 480.0
    iteracion_num_procesada = 0
    
    limite_seguridad_iteraciones = 200000 
    
    while iteracion_num_procesada < limite_seguridad_iteraciones:
        reloj_absoluto_actual = tiempo_dias_completos + reloj
        if unidad_tiempo == 'dias':
            if dia > dias_a_simular:
                break
        else:
            if reloj_absoluto_actual >= tiempo_a_simular_min:
                break

        fin_impaciencia = min((c['fin_impaciencia_reloj'] for c in cola_clientes), default=float('inf'))
        tiempos_eventos = {
            "Llegada de Cliente": proxima_llegada,
            "Finalización de Atención": fin_atencion,
            "Fin Impaciencia Cliente": fin_impaciencia,
            "Finalización de Recepción de Clientes": fin_recepcion_clientes
        }
        
        proximo_evento_nombre = min(tiempos_eventos, key=tiempos_eventos.get)

        if proxima_llegada == float('inf') and fin_atencion == float('inf') and not cola_clientes:
            proximo_evento_nombre = "Inicio de Día"
        
        if unidad_tiempo == 'horas' and proximo_evento_nombre != "Inicio de Día" and (tiempos_eventos[proximo_evento_nombre] + tiempo_dias_completos) >= tiempo_a_simular_min:
            proximo_evento_nombre = "Fin de Simulación"
        elif unidad_tiempo == 'dias' and proximo_evento_nombre != "Inicio de Día" and tiempo_dias_completos >= original_tiempo_sim_min:
            proximo_evento_nombre = "Fin de Simulación"

        # Guardar fila si está dentro del rango y no se superó el límite
        if reloj_absoluto_actual >= hora_comienzo_display and len(vector_estado) < max_filas_a_mostrar:
            fila_actual = {
                "Nro Fila": iteracion_num_procesada + 1, "Día": dia, "Reloj (min)": round(reloj, 2),
                "Minutos Acumulados": round(reloj_absoluto_actual, 2), "Horas Acumuladas": round(reloj_absoluto_actual / 60, 2),
                "Evento": evento, "Próximo Evento": proximo_evento_nombre, "RND Llegada": rnd_llegada,
                "Tiempo Llegada (min)": round(tiempo_llegada, 2) if isinstance(tiempo_llegada, float) else "-",
                "Hora Próxima Llegada (min)": round(proxima_llegada, 2) if proxima_llegada != float('inf') else "N/A",
                "Cola (Clientes)": f"{[(c['id'], round(c['fin_impaciencia_reloj'],2)) for c in cola_clientes]}" if cola_clientes else "Vacía",
                "Tamaño de la Cola": len(cola_clientes), "RND T": rnd_atencion, "T": T_atencion,
                "Duración Atención (min)": duracion_atencion_actual,
                "Hora Fin Atención (min)": round(fin_atencion, 2) if fin_atencion != float('inf') else "N/A",
                "Tiempos Inicio Atención": f"{ {k: round(v, 2) for k, v in inicio_atencion_tiempos.items()} }",
                "Estado Estilista": estilista_estado, "ID Cliente Siendo Atendido": cliente_siendo_atendido, "Clientes Atendidos": clientes_atendidos,
                "Clientes Impacientes": clientes_impacientes,
                "Acumulador Tiempo Atención (min)": round(acumulador_tiempo_atencion, 2),
                "Días de Cierre a Horario": dias_cierre_a_horario
            }
            vector_estado.append(fila_actual)
        
        iteracion_num_procesada += 1
        
        reloj_anterior = reloj
        rnd_llegada, tiempo_llegada, rnd_atencion, T_atencion, duracion_atencion_actual = "-", "-", "-", "-", "-"
        
        evento = proximo_evento_nombre
        if evento == "Fin de Simulación":
            break
        
        if evento == "Inicio de Día":
            if np.isclose(reloj_anterior, 480.0):
                dias_cierre_a_horario += 1
            
            tiempo_dias_completos += reloj_anterior
            dia += 1
            reloj, cliente_n_dia = 0.0, 0
            inicio_atencion_tiempos, duracion_servicios = {}, {}
            rnd_llegada = round(random.random(), 2)
            tiempo_llegada = llegada_a + (llegada_b - llegada_a) * rnd_llegada
            proxima_llegada = reloj + tiempo_llegada
            fin_recepcion_clientes = 480.0
            continue 
            
        reloj = tiempos_eventos[evento]

        if evento == "Llegada de Cliente":
            cliente_n_dia += 1
            evento = f"Llegada de Cliente {cliente_n_dia}" 
            if estilista_estado == "Libre":
                estilista_estado, cliente_en_atencion_id = "Ocupado", cliente_n_dia
                cliente_siendo_atendido = cliente_en_atencion_id
                rnd_atencion = round(random.random(), 2)
                T_atencion = atencion_a + (atencion_b - atencion_a) * rnd_atencion
                cola_actual_para_calculo = len(cola_clientes)
                tiempo_servicio, _, _ = resolver_euler(C=cola_actual_para_calculo, T=T_atencion, h=paso_h_inicial, d_corte=d_corte)
                duracion_atencion_actual = round(tiempo_servicio, 2)
                euler_data_storage.setdefault(dia, {})[cliente_en_atencion_id] = {'C': cola_actual_para_calculo, 'T': T_atencion, 'd_corte': d_corte}
                inicio_atencion_tiempos[cliente_en_atencion_id], duracion_servicios[cliente_en_atencion_id] = reloj, tiempo_servicio
                fin_atencion = reloj + tiempo_servicio
            else:
                cola_clientes.append({'id': cliente_n_dia, 'fin_impaciencia_reloj': reloj + 30})

            if reloj < fin_recepcion_clientes:
                rnd_llegada = round(random.random(), 2)
                tiempo_llegada = llegada_a + (llegada_b - llegada_a) * rnd_llegada
                proxima_llegada = reloj + tiempo_llegada
            else:
                proxima_llegada = float('inf')
        
        elif evento == "Finalización de Atención":
            cliente_finalizado_id, evento = cliente_en_atencion_id, f"Finalización de Atención {cliente_en_atencion_id}"
            acumulador_tiempo_atencion += duracion_servicios.get(cliente_finalizado_id, 0)
            clientes_atendidos += 1
            if cola_clientes:
                siguiente_cliente = cola_clientes.pop(0)
                cola_actual_para_calculo = len(cola_clientes)
                cliente_en_atencion_id = siguiente_cliente['id']
                cliente_siendo_atendido = cliente_en_atencion_id
                estilista_estado = "Ocupado"
                rnd_atencion = round(random.random(), 2)
                T_atencion = atencion_a + (atencion_b - atencion_a) * rnd_atencion
                tiempo_servicio, _, _ = resolver_euler(C=cola_actual_para_calculo, T=T_atencion, h=paso_h_inicial, d_corte=d_corte)
                duracion_atencion_actual = round(tiempo_servicio, 2)
                euler_data_storage.setdefault(dia, {})[cliente_en_atencion_id] = {'C': cola_actual_para_calculo, 'T': T_atencion, 'd_corte': d_corte}
                inicio_atencion_tiempos[cliente_en_atencion_id], duracion_servicios[cliente_en_atencion_id] = reloj, tiempo_servicio
                fin_atencion = reloj + tiempo_servicio
            else:
                estilista_estado, fin_atencion, cliente_en_atencion_id = "Libre", float('inf'), None
                cliente_siendo_atendido = "-"
        
        elif evento == "Fin Impaciencia Cliente":
            cliente_impaciente = min(cola_clientes, key=lambda x: x['fin_impaciencia_reloj'])
            cola_clientes = [c for c in cola_clientes if c['id'] != cliente_impaciente['id']]
            clientes_impacientes += 1
            evento = f"Fin Impaciencia Cliente {cliente_impaciente['id']}"

        elif evento == "Finalización de Recepción de Clientes":
            proxima_llegada, fin_recepcion_clientes = float('inf'), float('inf')
    
    # Construir la fila final de simulación, para ambos casos (horas o días)
    ultima_fila_final = {
        "Nro Fila": iteracion_num_procesada, "Día": dia,
        "Reloj (min)": round(min(original_tiempo_sim_min - tiempo_dias_completos, reloj), 2),
        "Minutos Acumulados": original_tiempo_sim_min,
        "Horas Acumuladas": round(original_tiempo_sim_min / 60, 2),
        "Evento": "Fin de Simulación", "Próximo Evento": "-",
        "RND Llegada": "-", "Tiempo Llegada (min)": "-", "Hora Próxima Llegada (min)": "N/A",
        "Cola (Clientes)": "-", "Tamaño de la Cola": "-",
        "RND T": "-", "T": "-", "Duración Atención (min)": "-",
        "Hora Fin Atención (min)": "N/A", "Tiempos Inicio Atención": "-",
        "Estado Estilista": "-", "ID Cliente Siendo Atendido": "-",
        "Clientes Atendidos": clientes_atendidos,
        "Clientes Impacientes": clientes_impacientes,
        "Acumulador Tiempo Atención (min)": round(acumulador_tiempo_atencion, 2),
        "Días de Cierre a Horario": dias_cierre_a_horario
    }
    if len(vector_estado) > max_filas_a_mostrar:
        vector_estado[-1] = ultima_fila_final
    else:
        vector_estado.append(ultima_fila_final)

    df = pd.DataFrame(vector_estado)
    if not df.empty:
        df.drop(columns=['Minutos Acumulados'], inplace=True, errors='ignore')
        resultados_finales = df.to_dict('records')
    else:
        resultados_finales = []

    total_atendidos, total_acumulado = clientes_atendidos, acumulador_tiempo_atencion
    promedio_atencion = (total_acumulado / total_atendidos) if total_atendidos > 0 else 0
    
    formula_params = {
        'llegada_a': llegada_a, 'llegada_b': llegada_b,
        'atencion_a': atencion_a, 'atencion_b': atencion_b,
        'd_corte': d_corte
    }
    
    metricas = {
        "total_atendidos": total_atendidos, "total_acumulado": round(total_acumulado, 2),
        "promedio_atencion": round(promedio_atencion, 2),
        "dias_cierre_a_horario": dias_cierre_a_horario
    }

    return render_template('resultado.html', data=resultados_finales,
                           paso_h_inicial=paso_h_inicial, metricas=metricas, formula_params=formula_params)


if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    index_html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simulación Peluquería - Parámetros</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; }
            .container { max-width: 600px; margin-top: 50px; }
            .card { border: none; box-shadow: 0 0.5rem 1rem rgba(0,0,0,.1); }
            .dist-label { font-size: 0.9rem; font-weight: 500; text-align: center; margin-bottom: 0.5rem; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">Parámetros de Simulación de Peluquería</h4>
                </div>
                <div class="card-body">
                    <form action="/simular" method="post">
                        <div class="mb-3">
                            <label for="tiempo_simulacion" class="form-label">Tiempo a Simular</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="tiempo_simulacion" name="tiempo_simulacion" required min="1" value="8">
                                <select class="form-select" name="unidad_tiempo">
                                    <option value="horas" selected>Horas</option>
                                    <option value="dias">Días</option>
                                </select>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="cantidad_iteraciones" class="form-label">Cantidad Máxima de Iteraciones a Mostrar</label>
                            <input type="number" class="form-control" id="cantidad_iteraciones" name="cantidad_iteraciones" required min="1" max="100000" value="500">
                        </div>
                        <div class="mb-3">
                            <label for="hora_comienzo" class="form-label">Mostrar Simulación Desde (Minuto Acumulado)</label>
                            <input type="number" class="form-control" id="hora_comienzo" name="hora_comienzo" required min="0" value="0">
                        </div>
                        <hr>
                        <div class="mb-3">
                            <div class="dist-label">Distribución Tiempo Llegadas: U(a, b) ~ <code>a + RND * (b - a)</code></div>
                            <div class="row">
                                <div class="col">
                                    <label for="llegada_a" class="form-label">Valor de 'a'</label>
                                    <input type="number" class="form-control" id="llegada_a" name="llegada_a" value="2" step="any">
                                </div>
                                <div class="col">
                                    <label for="llegada_b" class="form-label">Valor de 'b'</label>
                                    <input type="number" class="form-control" id="llegada_b" name="llegada_b" value="12" step="any">
                                </div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <div class="dist-label">Distribución Parámetro T: U(a, b) ~ <code>a + RND * (b - a)</code></div>
                            <div class="row">
                                <div class="col">
                                    <label for="atencion_a" class="form-label">Valor de 'a'</label>
                                    <input type="number" class="form-control" id="atencion_a" name="atencion_a" value="130" step="any">
                                </div>
                                <div class="col">
                                    <label for="atencion_b" class="form-label">Valor de 'b'</label>
                                    <input type="number" class="form-control" id="atencion_b" name="atencion_b" value="180" step="any">
                                </div>
                            </div>
                        </div>
                        <hr>
                        <div class="mb-3">
                            <label for="d_corte" class="form-label">Valor de Corte D</label>
                            <input type="number" class="form-control" id="d_corte" name="d_corte" value="700" step="any">
                        </div>
                        <div class="mb-3">
                            <label for="paso_h_euler" class="form-label">Paso (h) para Método de Euler</label>
                            <input type="number" class="form-control" id="paso_h_euler" name="paso_h_euler" step="0.001" required min="0.001" value="0.1">
                        </div>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary">Iniciar Simulación</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(index_html_content)

    resultado_html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultados de la Simulación</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; }
            .table-responsive { max-height: 70vh; }
            th { position: sticky; top: 0; background-color: #343a40; color: white; white-space: nowrap; }
            td { white-space: nowrap; }
            .download-form-container {
                display: flex;
                justify-content: center;
                margin-bottom: 2rem;
            }
            .download-form {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0.5rem 1rem rgba(0,0,0,.15);
                max-width: 500px;
                width: 100%;
            }
            .metric-card {
                background-color: #fff;
                border-radius: .75rem;
                padding: 1.25rem;
                text-align: center;
                box-shadow: 0 0.25rem 0.5rem rgba(0,0,0,.075);
                margin-bottom: 1rem;
            }
            .metric-title {
                font-size: 0.9rem;
                color: #6c757d;
                font-weight: 500;
            }
            .metric-value {
                font-size: 1.75rem;
                font-weight: 700;
                color: #343a40;
            }
            .formulas-card {
                background-color: #e9ecef;
                border: 1px solid #dee2e6;
            }
        </style>
    </head>
    <body>
        <div class="container-fluid mt-4">
            <h2 class="text-center mb-4">Resultados de la Simulación</h2>
            
            {% if data %}
            <div class="download-form-container">
                <div class="download-form card">
                    <div class="card-body">
                        <h5 class="card-title">Descargar Cálculo de Euler</h5>
                        <p class="card-text small">Ingrese el <strong>Día</strong>, <strong>ID del Cliente</strong> y el paso (h) para descargar su cálculo de integración.</p>
                        <form action="/descargar_euler" method="post" class="d-flex align-items-end">
                             <div class="flex-grow-1 me-2">
                                <label for="dia_euler" class="form-label">Día</label>
                                <input type="number" class="form-control" id="dia_euler" name="dia_euler" required min="1">
                             </div>
                             <div class="flex-grow-1 me-2">
                                <label for="cliente_id_euler" class="form-label">ID del Cliente</label>
                                <input type="number" class="form-control" id="cliente_id_euler" name="cliente_id_euler" required min="1">
                            </div>
                            <div class="me-2">
                                <label for="paso_h_euler" class="form-label">Paso (h)</label>
                                <input type="number" class="form-control" id="paso_h_euler" name="paso_h_euler" step="0.001" required min="0.001" value="{{ paso_h_inicial or 0.1 }}">
                            </div>
                            <button type="submit" class="btn btn-success">Descargar</button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="row justify-content-center mb-4">
                <div class="col-lg-3 col-md-6">
                    <div class="metric-card">
                        <div class="metric-title">CLIENTES TOTALES ATENDIDOS</div>
                        <div class="metric-value">{{ metricas.total_atendidos }}</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="metric-card">
                        <div class="metric-title">TIEMPO TOTAL DE ATENCIÓN (MIN)</div>
                        <div class="metric-value">{{ metricas.total_acumulado }}</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="metric-card">
                        <div class="metric-title">TIEMPO PROMEDIO DE ATENCIÓN (MIN)</div>
                        <div class="metric-value">{{ metricas.promedio_atencion }}</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <div class="metric-card">
                        <div class="metric-title">DÍAS DE CIERRE A HORARIO</div>
                        <div class="metric-value">{{ metricas.dias_cierre_a_horario }}</div>
                    </div>
                </div>
            </div>

            <div class="row justify-content-center mb-4">
                <div class="col-lg-9">
                    <div class="card formulas-card">
                        <div class="card-header">
                            <strong>Fórmulas Clave de la Simulación</strong>
                        </div>
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item bg-transparent"><strong>Tiempo entre Llegadas (min):</strong> <code>{{ formula_params.llegada_a }} + RND * ({{ formula_params.llegada_b }} - {{ formula_params.llegada_a }})</code></li>
                            <li class="list-group-item bg-transparent"><strong>Parámetro T de Atención:</strong> <code>{{ formula_params.atencion_a }} + RND * ({{ formula_params.atencion_b }} - {{ formula_params.atencion_a }})</code></li>
                            <li class="list-group-item bg-transparent"><strong>Fin Impaciencia Cliente (min):</strong> <code>Reloj de Llegada + 30</code></li>
                            <li class="list-group-item bg-transparent"><strong>Duración de Atención (t):</strong> Se obtiene resolviendo <code>dD/dt = C + 0.2*T + t²</code> hasta que <code>D > {{ formula_params.d_corte }}</code>.</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-striped table-bordered table-hover table-sm">
                    <thead class="table-dark">
                        <tr>
                            {% for key in data[0].keys() %}
                                <th>{{ key }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in data %}
                        <tr>
                            {% for value in row.values() %}
                                <td>{{ value }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            {% else %}
            <div class="alert alert-warning" role="alert">
              No se generaron datos para los parámetros ingresados. Intente con un tiempo de simulación mayor o más iteraciones.
            </div>
            {% endif %}

            <div class="text-center mt-4 mb-4">
                <a href="/" class="btn btn-primary">Volver a Parámetros</a>
            </div>
        </div>
    </body>
    </html>
    """
    with open("templates/resultado.html", "w", encoding="utf-8") as f:
        f.write(resultado_html_content)

    app.run(debug=True)