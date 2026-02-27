import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'logic'))

from flask import Flask, jsonify, request, render_template
from datetime import datetime, timedelta
import threading
import time

from core import (
    animalitos, loterias, horarios,
    obtener_resultados, obtener_estadisticas, obtener_resultados_dia,
    buscar_patrones_similares, generar_pronosticos_patrones,
    buscar_patrones_animales, generar_pronosticos_animales,
    buscar_patrones_multiloterias,
    analizar_frecuencias,
    buscar_coincidencias_consecutivas,
    generar_multi_pronosticos,
    detectar_duplicados, eliminar_duplicados,
    scraping_historico, ScrapingLoteria
)

app = Flask(__name__)

# ─── Auto-scraping state ──────────────────────────────────────────────────────
auto_scraping_activo = False
ultima_actualizacion = "Nunca"
hilo_scraping = None

def _loop_auto_scraping():
    global ultima_actualizacion
    while auto_scraping_activo:
        try:
            hoy = datetime.now()
            for loteria in loterias:
                try:
                    scraper = ScrapingLoteria(loteria, hoy)
                    scraper.obtener_resultados()
                except Exception:
                    pass
            ultima_actualizacion = datetime.now().strftime('%H:%M:%S')
        except Exception as e:
            print(f"Auto-scraping error: {e}")
        time.sleep(300)  # 5 minutes

# ─── Main page ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    now = datetime.now()
    return render_template('index.html',
        loterias=loterias,
        horarios=horarios,
        animalitos=animalitos,
        now=now,
        now_minus_7=(now - timedelta(days=7)),
        now_minus_30=(now - timedelta(days=30)),
        now_minus_90=(now - timedelta(days=90)))

# ─── API: Resultados ──────────────────────────────────────────────────────────
@app.route('/api/resultados')
def api_resultados():
    fi = request.args.get('fecha_inicio', (datetime.now()-timedelta(days=7)).strftime('%d/%m/%Y'))
    ff = request.args.get('fecha_fin', datetime.now().strftime('%d/%m/%Y'))
    lot = request.args.get('loteria', 'TODAS')
    hor = request.args.get('horario', 'TODOS')
    data = obtener_resultados(fi, ff, lot, hor)
    return jsonify({'resultados': data, 'total': len(data)})

@app.route('/api/estadisticas')
def api_estadisticas():
    return jsonify(obtener_estadisticas())

# ─── API: Scraping ────────────────────────────────────────────────────────────
@app.route('/api/scraping', methods=['POST'])
def api_scraping():
    body = request.json or {}
    fi = body.get('fecha_inicio')
    ff = body.get('fecha_fin')
    lots = body.get('loterias', loterias)
    if not fi or not ff:
        return jsonify({'error': 'Faltan fechas'}), 400
    try:
        fecha_i = datetime.strptime(fi, '%d/%m/%Y')
        fecha_f = datetime.strptime(ff, '%d/%m/%Y')
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido. Use DD/MM/YYYY'}), 400
    result = scraping_historico(fecha_i, fecha_f, lots)
    return jsonify(result)

@app.route('/api/auto-scraping', methods=['POST'])
def api_toggle_auto_scraping():
    global auto_scraping_activo, hilo_scraping
    body = request.json or {}
    activar = body.get('activo', False)
    if activar and not auto_scraping_activo:
        auto_scraping_activo = True
        hilo_scraping = threading.Thread(target=_loop_auto_scraping, daemon=True)
        hilo_scraping.start()
    elif not activar:
        auto_scraping_activo = False
    return jsonify({'activo': auto_scraping_activo, 'ultima_actualizacion': ultima_actualizacion})

@app.route('/api/auto-scraping/status')
def api_auto_status():
    return jsonify({'activo': auto_scraping_activo, 'ultima_actualizacion': ultima_actualizacion})

# ─── API: Patrones Históricos ─────────────────────────────────────────────────
@app.route('/api/patrones/similares')
def api_patrones_similares():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    sim = int(request.args.get('min_similitud', 30))
    result = buscar_patrones_similares(lot, fr, fi, ff, sim)
    return jsonify(result)

@app.route('/api/patrones/pronosticos')
def api_patrones_pronosticos():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    top = int(request.args.get('top_n', 10))
    return jsonify(generar_pronosticos_patrones(lot, fr, fi, ff, top))

@app.route('/api/patrones/referencia')
def api_patrones_referencia():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fecha = request.args.get('fecha', datetime.now().strftime('%d/%m/%Y'))
    ref = obtener_resultados_dia(fecha, lot)
    from core import ordenar_horarios
    result = [{'horario': h, 'codigo': ref[h], 'nombre': animalitos.get(ref[h], '')} for h in ordenar_horarios(list(ref.keys()))]
    return jsonify({'resultados': result})

# ─── API: Patrones Animales ───────────────────────────────────────────────────
@app.route('/api/animales/patrones')
def api_animales_patrones():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    sim = int(request.args.get('min_similitud', 30))
    return jsonify(buscar_patrones_animales(lot, fr, fi, ff, sim))

@app.route('/api/animales/pronosticos')
def api_animales_pronosticos():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    top = int(request.args.get('top_n', 10))
    return jsonify(generar_pronosticos_animales(lot, fr, fi, ff, top))

# ─── API: Multiloterías ───────────────────────────────────────────────────────
@app.route('/api/multiloterias')
def api_multiloterias():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    sim = int(request.args.get('min_similitud', 30))
    lots_cmp = request.args.getlist('loterias') or loterias
    return jsonify(buscar_patrones_multiloterias(lot, fr, lots_cmp, fi, ff, sim))

# ─── API: Frecuencias ─────────────────────────────────────────────────────────
@app.route('/api/frecuencias')
def api_frecuencias():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fi = request.args.get('fecha_inicio', (datetime.now()-timedelta(days=30)).strftime('%d/%m/%Y'))
    ff = request.args.get('fecha_fin', datetime.now().strftime('%d/%m/%Y'))
    tipo = request.args.get('tipo', 'despues')
    return jsonify(analizar_frecuencias(lot, fi, ff, tipo))

# ─── API: Coincidencias Consecutivas ─────────────────────────────────────────
@app.route('/api/coincidencias')
def api_coincidencias():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    a1 = request.args.get('animal1', '1')
    a2 = request.args.get('animal2', '2')
    fi = request.args.get('fecha_inicio', (datetime.now()-timedelta(days=30)).strftime('%d/%m/%Y'))
    ff = request.args.get('fecha_fin', datetime.now().strftime('%d/%m/%Y'))
    return jsonify(buscar_coincidencias_consecutivas(lot, a1, a2, fi, ff))

@app.route('/api/coincidencias/dia')
def api_coincidencias_dia():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'error': 'Fecha requerida'}), 400
    ref = obtener_resultados_dia(fecha, lot)
    from core import ordenar_horarios
    result = [{'horario': h, 'codigo': ref[h], 'nombre': animalitos.get(ref[h], '')} for h in ordenar_horarios(list(ref.keys()))]
    return jsonify({'resultados': result})

# ─── API: Multipronósticos ────────────────────────────────────────────────────
@app.route('/api/multipronosticos')
def api_multipronosticos():
    lot = request.args.get('loteria', 'LOTTO ACTIVO')
    fr = request.args.get('fecha_referencia', datetime.now().strftime('%d/%m/%Y'))
    fi = request.args.get('fecha_inicio')
    ff = request.args.get('fecha_fin')
    if not fi or not ff:
        return jsonify({'error': 'Fechas requeridas'}), 400
    return jsonify(generar_multi_pronosticos(lot, fr, fi, ff))

# ─── API: Mantenimiento ───────────────────────────────────────────────────────
@app.route('/api/db/duplicados')
def api_duplicados():
    return jsonify(detectar_duplicados())

@app.route('/api/db/eliminar-duplicados', methods=['POST'])
def api_eliminar_duplicados():
    return jsonify(eliminar_duplicados())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
