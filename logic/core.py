from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import requests
from bs4 import BeautifulSoup
import time

from database import get_db_connection

# ─── Constants ────────────────────────────────────────────────────────────────

animalitos = {
    '0': 'DELFIN', '00': 'BALLENA', '1': 'CARNERO', '2': 'TORO', '3': 'CIEMPIES',
    '4': 'ALACRAN', '5': 'LEON', '6': 'RANA', '7': 'PERICO', '8': 'RATON',
    '9': 'AGUILA', '10': 'TIGRE', '11': 'GATO', '12': 'CABALLO', '13': 'MONO',
    '14': 'PALOMA', '15': 'ZORRO', '16': 'OSO', '17': 'PAVO', '18': 'BURRO',
    '19': 'CHIVO', '20': 'COCHINO', '21': 'GALLO', '22': 'CAMELLO', '23': 'CEBRA',
    '24': 'IGUANA', '25': 'GALLINA', '26': 'VACA', '27': 'PERRO', '28': 'ZAMURO',
    '29': 'ELEFANTE', '30': 'CAIMAN', '31': 'LAPA', '32': 'ARDILLA', '33': 'PESCADO',
    '34': 'VENADO', '35': 'JIRAFA', '36': 'CULEBRA', '37': 'TORTUGA', '38': 'BUFALO',
    '39': 'LECHUZA', '40': 'AVISPA', '41': 'CANGURO', '42': 'TUCAN', '43': 'MARIPOSA',
    '44': 'CHIGUIRE', '45': 'GARZA', '46': 'PUMA', '47': 'PAVO REAL', '48': 'PUERCOESPIN',
    '49': 'PEREZA', '50': 'CANARIO', '51': 'PELICANO', '52': 'PULPO', '53': 'CARACOL',
    '54': 'GRILLO', '55': 'OSO HORMIGUERO', '56': 'TIBURON', '57': 'PATO',
    '58': 'HORMIGA', '59': 'PANTERA', '60': 'CAMALEON', '61': 'PANDA',
    '62': 'CACHICAMO', '63': 'CANGREJO', '64': 'GAVILAN', '65': 'ARANA',
    '66': 'LOBO', '67': 'AVESTRUZ', '68': 'JAGUAR', '69': 'CONEJO', '70': 'BISONTE',
    '71': 'GUACAMAYA', '72': 'GORILA', '73': 'HIPOPOTAMO', '74': 'TURPIAL', '75': 'GUACHARO'
}

loterias = [
    'LOTTO ACTIVO', 'LA GRANJITA', 'LOTTO REY', 'SELVA PLUS',
    'RULETA ACTIVA', 'LOTTO ACT INT', 'LOTTO ACTIVO RD',
    'GUACHARO ACTIVO', 'LA RICACHONA'
]

horarios = [
    '08:00AM', '08:30AM', '09:00AM', '09:30AM', '10:00AM', '10:30AM',
    '11:00AM', '11:30AM', '12:00PM', '12:30PM', '01:00PM', '01:30PM',
    '02:00PM', '02:30PM', '03:00PM', '03:30PM', '04:00PM', '04:30PM',
    '05:00PM', '05:30PM', '06:00PM', '06:30PM', '07:00PM'
]

urls_scraping = {
    'LOTTO ACTIVO': 'https://loteriadehoy.com/animalito/lottoactivo/resultados/',
    'LA GRANJITA': 'https://loteriadehoy.com/animalito/lagranjita/resultados/',
    'SELVA PLUS': 'https://loteriadehoy.com/animalito/selvaplus/resultados/',
    'LOTTO REY': 'https://loteriadehoy.com/animalito/lottorey/resultados/',
    'RULETA ACTIVA': 'https://loteriadehoy.com/animalito/ruletaactiva/resultados/',
    'LOTTO ACT INT': 'https://loteriadehoy.com/animalito/lottoactivordint/resultados/',
    'LOTTO ACTIVO RD': 'https://loteriadehoy.com/animalito/lottoactivordominicana/resultados/',
    'GUACHARO ACTIVO': 'https://loteriadehoy.com/animalito/guacharoactivo/resultados/',
    'LA RICACHONA': 'https://loteriadehoy.com/animalito/la-ricachona/resultados/'
}

# ─── Date / Time Helpers ──────────────────────────────────────────────────────

def fecha_dd_mm_yyyy_a_iso(fecha):
    try:
        partes = fecha.split('/')
        if len(partes) == 3:
            dia, mes, anio = partes
            return f'{anio}-{mes}-{dia}'
    except Exception:
        pass
    return fecha


def fecha_iso_a_dd_mm_yyyy(fecha_iso):
    try:
        partes = fecha_iso.split('-')
        if len(partes) == 3:
            anio, mes, dia = partes
            return f'{dia}/{mes}/{anio}'
    except Exception:
        pass
    return fecha_iso


def convertir_horario_a_minutos(horario_str):
    try:
        tiempo_str = horario_str[:-2]
        periodo = horario_str[-2:]
        hora, minutos = map(int, tiempo_str.split(':'))
        if periodo == 'PM' and hora != 12:
            hora += 12
        elif periodo == 'AM' and hora == 12:
            hora = 0
        return hora * 60 + minutos
    except Exception:
        return 0


def ordenar_horarios(horarios_lista):
    return sorted(horarios_lista, key=convertir_horario_a_minutos)


def normalizar_horario_ml(horario):
    if not horario or horario == 'No disponible':
        return horario
    try:
        tiempo_str = horario[:-2]
        periodo = horario[-2:]
        hora, minutos = tiempo_str.split(':')
        hora_int = int(hora)
        if minutos in ('10', '40'):
            minutos = '00' if minutos == '10' else '30'
        elif minutos == '30':
            minutos = '00'
        return f'{hora_int:02d}:{minutos}{periodo}'
    except Exception:
        return horario


def normalizar_resultados_ml(resultados):
    if not resultados:
        return {}
    return {normalizar_horario_ml(h): a for h, a in resultados.items()}

# ─── Database helpers ─────────────────────────────────────────────────────────

def _fetchall(query, params=()):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Query error: {e}")
        return []
    finally:
        conn.close()


def _fetchone(query, params=()):
    rows = _fetchall(query, params)
    return rows[0] if rows else None


def _execute(query, params=()):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Execute error: {e}")
        return False
    finally:
        conn.close()

# ─── Resultados DB ────────────────────────────────────────────────────────────

def obtener_resultados(fecha_inicio=None, fecha_fin=None, loteria=None, horario=None):
    query = "SELECT fecha, loteria, horario_sorteo, animalito_ganador FROM resultados WHERE 1=1"
    params = []
    if fecha_inicio and fecha_fin:
        query += " AND fecha_iso BETWEEN %s AND %s"
        params += [fecha_dd_mm_yyyy_a_iso(fecha_inicio), fecha_dd_mm_yyyy_a_iso(fecha_fin)]
    if loteria and loteria != 'TODAS':
        query += " AND loteria = %s"
        params.append(loteria)
    if horario and horario != 'TODOS':
        query += " AND horario_sorteo = %s"
        params.append(horario)
    query += " ORDER BY fecha_iso DESC, loteria, horario_sorteo"
    rows = _fetchall(query, params)
    for r in rows:
        r['animalito_nombre'] = animalitos.get(r['animalito_ganador'], 'DESCONOCIDO')
    return rows


def obtener_estadisticas():
    total = _fetchone("SELECT COUNT(*) AS cnt FROM resultados") or {}
    fechas = _fetchone("SELECT MIN(fecha_iso) AS min_f, MAX(fecha_iso) AS max_f FROM resultados") or {}
    por_loteria = _fetchall(
        "SELECT loteria, COUNT(*) AS total FROM resultados GROUP BY loteria ORDER BY total DESC"
    )
    return {
        'total': total.get('cnt', 0),
        'fecha_min': fecha_iso_a_dd_mm_yyyy(str(fechas.get('min_f', ''))) if fechas.get('min_f') else 'N/A',
        'fecha_max': fecha_iso_a_dd_mm_yyyy(str(fechas.get('max_f', ''))) if fechas.get('max_f') else 'N/A',
        'por_loteria': [dict(r) for r in por_loteria]
    }


def obtener_resultados_dia(fecha, loteria):
    rows = _fetchall(
        "SELECT horario_sorteo, animalito_ganador FROM resultados WHERE fecha=%s AND loteria=%s ORDER BY horario_sorteo",
        (fecha, loteria)
    )
    return {r['horario_sorteo']: r['animalito_ganador'] for r in rows}


def obtener_dias_con_datos(loteria, fecha_inicio=None, fecha_fin=None):
    if fecha_inicio and fecha_fin:
        rows = _fetchall(
            "SELECT DISTINCT fecha FROM resultados WHERE fecha_iso BETWEEN %s AND %s AND loteria=%s ORDER BY fecha_iso DESC",
            (fecha_dd_mm_yyyy_a_iso(fecha_inicio), fecha_dd_mm_yyyy_a_iso(fecha_fin), loteria)
        )
    else:
        fecha_limite = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        rows = _fetchall(
            "SELECT DISTINCT fecha FROM resultados WHERE fecha_iso >= %s AND loteria=%s ORDER BY fecha_iso DESC",
            (fecha_limite, loteria)
        )
    return [r['fecha'] for r in rows]


def obtener_animales_dia(fecha, loteria):
    rows = _fetchall(
        "SELECT animalito_ganador FROM resultados WHERE fecha=%s AND loteria=%s",
        (fecha, loteria)
    )
    return set(r['animalito_ganador'] for r in rows)

# ─── Scraping ─────────────────────────────────────────────────────────────────

class ScrapingLoteria:
    def __init__(self, loteria_nombre, fecha=None):
        self.loteria_nombre = loteria_nombre
        self.url = urls_scraping.get(loteria_nombre)
        if not self.url:
            raise ValueError(f'No hay URL para: {loteria_nombre}')
        if fecha:
            self.url = f'{self.url}{fecha.strftime("%Y-%m-%d")}/'
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})

    def obtener_resultados(self):
        try:
            r = self.session.get(self.url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')
            contenedor = soup.find('div', class_='js-con') or soup.find('div', class_='container')
            if not contenedor:
                return {'error': 'Contenedor no encontrado'}
            elementos = contenedor.find_all('div', class_=lambda x: x and 'col-' in x and 'mb-' in x)
            if not elementos:
                elementos = contenedor.find_all('div', class_=lambda x: x and 'col-' in x)
            resultados = []
            for elem in elementos:
                try:
                    data = self._procesar_elemento(elem)
                    if data:
                        resultados.append(data)
                except Exception:
                    continue
            return {'success': True, 'resultados': resultados, 'total': len(resultados)}
        except Exception as e:
            return {'error': str(e)}

    def _corregir_nombre(self, nombre):
        correcciones = {'GIEMPIESS': 'CIEMPIES', 'CIEMPIESS': 'CIEMPIES'}
        return correcciones.get(nombre, nombre)

    def _buscar_codigo(self, nombre, numero):
        if numero in animalitos and animalitos[numero].upper() == nombre.upper():
            return numero
        for cod, nom in animalitos.items():
            if nom.upper() == nombre.upper():
                return cod
        return numero

    def _procesar_elemento(self, elem):
        data = {}
        ani_el = (elem.find('h4') or elem.find('h3') or elem.find('h2'))
        if ani_el:
            txt = ani_el.get_text(strip=True)
            if txt and txt != '@':
                m = re.match(r'^(\$|\d+)\s+(.+)$', txt)
                if m:
                    num = m.group(1).replace('$', '').strip()
                    nombre = self._corregir_nombre(m.group(2).strip().upper())
                    data.update({'numero_animalito': num, 'nombre_animalito': nombre,
                                 'codigo_correcto': self._buscar_codigo(nombre, num)})
                else:
                    nums = re.findall(r'\d+', txt)
                    data.update({'numero_animalito': nums[0] if nums else '',
                                 'nombre_animalito': txt.upper(), 'codigo_correcto': ''})
            else:
                data.update({'numero_animalito': 'Pendiente', 'nombre_animalito': 'Pendiente', 'codigo_correcto': ''})
        else:
            return None
        hor_el = elem.find('h5') or elem.find('h4')
        if hor_el:
            hr_txt = hor_el.get_text(strip=True)
            m = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', hr_txt, re.IGNORECASE)
            if m:
                data['hora'] = m.group(1).upper().replace(' ', '')
                data['tipo_loteria'] = self.loteria_nombre
            else:
                return None
        else:
            return None
        if data.get('hora') and data.get('numero_animalito') not in ('', 'Pendiente'):
            return data
        return None


def scraping_historico(fecha_inicio, fecha_fin, loterias_sel, progress_callback=None):
    conn = get_db_connection()
    if not conn:
        return {'error': 'No se pudo conectar a la base de datos'}
    cursor = conn.cursor()
    total = 0
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        fecha_str = fecha_actual.strftime('%d/%m/%Y')
        fecha_iso = fecha_actual.strftime('%Y-%m-%d')
        if progress_callback:
            progress_callback(f'Procesando {fecha_str}')
        for loteria in loterias_sel:
            try:
                scraper = ScrapingLoteria(loteria, fecha_actual)
                res = scraper.obtener_resultados()
                if 'error' in res or not res.get('resultados'):
                    continue
                for r in res['resultados']:
                    codigo = r.get('codigo_correcto') or r.get('numero_animalito', '')
                    if not codigo or codigo == 'Pendiente':
                        continue
                    try:
                        cursor.execute("""
                            INSERT INTO resultados (fecha, fecha_iso, loteria, horario_sorteo, animalito_ganador)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (fecha, loteria, horario_sorteo) DO UPDATE
                              SET animalito_ganador = EXCLUDED.animalito_ganador
                        """, (fecha_str, fecha_iso, r['tipo_loteria'], r['hora'], codigo))
                        total += 1
                    except Exception as e:
                        print(f"Insert error: {e}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Scraping error {loteria}: {e}")
        fecha_actual += timedelta(days=1)
    conn.commit()
    conn.close()
    return {'success': True, 'total_resultados': total}

# ─── Análisis: Patrones Históricos ────────────────────────────────────────────

def calcular_similitud_patrones(pat_ref, pat_hist, horarios_compare):
    aciertos = total = 0
    for h in horarios_compare:
        if h in pat_ref and h in pat_hist:
            if pat_ref[h] == pat_hist[h]:
                aciertos += 1
            total += 1
    if total == 0:
        return 0, 0, 0
    return aciertos / total * 100, aciertos, total


def buscar_patrones_similares(loteria, fecha_referencia, fecha_inicio=None, fecha_fin=None, min_similitud=30):
    ref = obtener_resultados_dia(fecha_referencia, loteria)
    if not ref:
        return {'error': f'No hay resultados para {loteria} en {fecha_referencia}'}
    horarios_ref = ordenar_horarios(list(ref.keys()))
    if len(horarios_ref) < 2:
        return {'error': 'Se necesitan al menos 2 resultados en la fecha de referencia'}
    dias = obtener_dias_con_datos(loteria, fecha_inicio, fecha_fin)
    if not dias:
        return {'error': 'No hay datos históricos'}
    patrones = []
    for fecha_hist in dias:
        if fecha_hist == fecha_referencia:
            continue
        hist = obtener_resultados_dia(fecha_hist, loteria)
        if not hist:
            continue
        sim, aci, tot = calcular_similitud_patrones(ref, hist, horarios_ref)
        if sim >= min_similitud:
            futuros = [
                {'horario': h, 'animalito': hist[h], 'nombre_animalito': animalitos.get(hist[h], 'DESCONOCIDO')}
                for h in ordenar_horarios(list(hist.keys()))
                if h not in horarios_ref
            ]
            patrones.append({
                'fecha': fecha_hist, 'similitud': round(sim, 1),
                'aciertos': aci, 'total_comparaciones': tot,
                'resultados_futuros': futuros, 'total_futuros': len(futuros)
            })
    patrones.sort(key=lambda x: (x['aciertos'], x['similitud']), reverse=True)
    return {
        'patrones_similares': patrones[:50],
        'resultados_referencia': ref,
        'horarios_referencia': horarios_ref,
        'total_referencia': len(horarios_ref),
        'total_analizados': len(dias),
        'loteria': loteria, 'fecha_referencia': fecha_referencia
    }


def generar_pronosticos_patrones(loteria, fecha_referencia, fecha_inicio=None, fecha_fin=None, top_n=10):
    res = buscar_patrones_similares(loteria, fecha_referencia, fecha_inicio, fecha_fin)
    if 'error' in res:
        return res
    patrones = res['patrones_similares']
    if not patrones:
        return {'error': 'No se encontraron patrones similares'}
    frec = Counter()
    peso_total = 0
    for p in patrones:
        peso = p['similitud'] / 100.0
        for rf in p['resultados_futuros']:
            frec[rf['animalito']] += peso
        peso_total += peso
    if not frec:
        return {'error': 'No hay datos futuros'}
    pronosticos = []
    for ani, f in frec.most_common():
        if ani in animalitos:
            pronosticos.append({
                'numero': ani, 'animalito': animalitos.get(ani, 'DESCONOCIDO'),
                'puntuacion': round(f / peso_total * 10, 2), 'frecuencia': round(f, 2)
            })
    pronosticos = sorted(pronosticos, key=lambda x: x['puntuacion'], reverse=True)[:top_n]
    return {
        'pronosticos': pronosticos,
        'total_patrones': len(patrones),
        'mejor_similitud': patrones[0]['similitud'] if patrones else 0,
        'loteria': loteria, 'fecha_referencia': fecha_referencia,
        'metodo': 'PATRONES_HISTORICOS'
    }

# ─── Análisis: Patrones Animales ──────────────────────────────────────────────

def buscar_patrones_animales(loteria, fecha_referencia, fecha_inicio=None, fecha_fin=None, min_similitud=30):
    animales_ref = obtener_animales_dia(fecha_referencia, loteria)
    if not animales_ref or len(animales_ref) < 2:
        return {'error': 'Se necesitan al menos 2 animales en la fecha de referencia'}
    dias = obtener_dias_con_datos(loteria, fecha_inicio, fecha_fin)
    if not dias:
        return {'error': 'No hay datos históricos'}
    patrones = []
    for fd in dias:
        if fd == fecha_referencia:
            continue
        animales_hist = obtener_animales_dia(fd, loteria)
        if not animales_hist:
            continue
        comunes = animales_ref.intersection(animales_hist)
        if not animales_ref:
            continue
        sim = len(comunes) / len(animales_ref) * 100
        if sim >= min_similitud:
            futuros = animales_hist - animales_ref
            patrones.append({
                'fecha': fd, 'similitud': round(sim, 1),
                'aciertos': len(comunes),
                'animales_referencia': len(animales_ref),
                'animales_historicos': len(animales_hist),
                'animales_futuros': [{'animalito': a, 'nombre_animalito': animalitos.get(a, '')} for a in futuros],
                'total_futuros': len(futuros)
            })
    patrones.sort(key=lambda x: (x['aciertos'], x['similitud']), reverse=True)
    return {'patrones_similares': patrones[:50], 'animales_referencia': list(animales_ref), 'total_analizados': len(dias)}


def generar_pronosticos_animales(loteria, fecha_referencia, fecha_inicio=None, fecha_fin=None, top_n=10):
    res = buscar_patrones_animales(loteria, fecha_referencia, fecha_inicio, fecha_fin)
    if 'error' in res:
        return res
    patrones = res['patrones_similares']
    if not patrones:
        return {'error': 'Sin patrones'}
    max_aci = max(p['aciertos'] for p in patrones)
    if max_aci == 0:
        return {'error': 'Sin aciertos'}
    filtrados = [p for p in patrones if p['aciertos'] >= max_aci - 1]
    frec = Counter()
    pesos = {}
    for p in filtrados:
        peso = 3.0 if p['aciertos'] == max_aci else 2.0
        pesos[p['fecha']] = peso
        for af in p['animales_futuros']:
            frec[af['animalito']] += peso
    if not frec:
        return {'error': 'Sin animales futuros'}
    total_peso = sum(pesos.values())
    pronosticos = []
    for ani, f in frec.most_common():
        if ani in animalitos:
            pronosticos.append({
                'numero': ani, 'animalito': animalitos.get(ani, ''),
                'puntuacion': round(f / total_peso * 100, 2),
                'frecuencia': round(f, 2),
                'fechas_aparicion': sum(1 for p in filtrados if any(a['animalito'] == ani for a in p['animales_futuros']))
            })
    return {
        'pronosticos': sorted(pronosticos, key=lambda x: x['puntuacion'], reverse=True)[:top_n],
        'total_patrones': len(filtrados), 'max_aciertos': max_aci,
        'loteria': loteria, 'fecha_referencia': fecha_referencia,
        'metodo': 'PATRONES_ANIMALES'
    }

# ─── Análisis: Frecuencias ────────────────────────────────────────────────────

def analizar_frecuencias(loteria, fecha_inicio, fecha_fin, tipo='despues'):
    rows = _fetchall(
        "SELECT fecha, horario_sorteo, animalito_ganador FROM resultados WHERE fecha_iso BETWEEN %s AND %s AND loteria=%s ORDER BY fecha_iso, horario_sorteo",
        (fecha_dd_mm_yyyy_a_iso(fecha_inicio), fecha_dd_mm_yyyy_a_iso(fecha_fin), loteria)
    )
    if not rows:
        return {'error': 'Sin datos'}
    por_dia = defaultdict(dict)
    for r in rows:
        por_dia[r['fecha']][r['horario_sorteo']] = r['animalito_ganador']
    frecuencias = defaultdict(Counter)
    for fecha, resultados_dia in por_dia.items():
        hs = ordenar_horarios(list(resultados_dia.keys()))
        for i, h in enumerate(hs):
            ani = resultados_dia[h]
            if tipo == 'despues' and i < len(hs) - 1:
                frecuencias[ani][resultados_dia[hs[i+1]]] += 1
            elif tipo == 'antes' and i > 0:
                frecuencias[ani][resultados_dia[hs[i-1]]] += 1
    resultado = {}
    for ani, cnt in frecuencias.items():
        resultado[ani] = [
            {'animalito': a, 'nombre': animalitos.get(a, ''), 'frecuencia': f}
            for a, f in cnt.most_common()
        ]
    return {'frecuencias': resultado, 'total_dias': len(por_dia), 'tipo': tipo}

# ─── Análisis: Coincidencias Consecutivas ────────────────────────────────────

def buscar_coincidencias_consecutivas(loteria, animal1, animal2, fecha_inicio, fecha_fin):
    rows = _fetchall(
        "SELECT fecha, horario_sorteo, animalito_ganador FROM resultados WHERE fecha_iso BETWEEN %s AND %s AND loteria=%s ORDER BY fecha_iso, horario_sorteo",
        (fecha_dd_mm_yyyy_a_iso(fecha_inicio), fecha_dd_mm_yyyy_a_iso(fecha_fin), loteria)
    )
    if not rows:
        return {'error': 'Sin datos'}
    por_dia = defaultdict(list)
    for r in rows:
        por_dia[r['fecha']].append((r['horario_sorteo'], r['animalito_ganador']))
    coincidencias = []
    for fecha, resultados_dia in por_dia.items():
        ordenados = sorted(resultados_dia, key=lambda x: convertir_horario_a_minutos(x[0]))
        for i in range(len(ordenados) - 1):
            if ordenados[i][1] == animal1 and ordenados[i+1][1] == animal2:
                coincidencias.append({
                    'fecha': fecha,
                    'horario_animal1': ordenados[i][0],
                    'horario_animal2': ordenados[i+1][0],
                    'posicion': i + 1,
                    'total_resultados_dia': len(ordenados)
                })
                break
    return {
        'fechas_coincidentes': coincidencias,
        'total_coincidencias': len(coincidencias),
        'animal1': animal1, 'animal2': animal2,
        'nombre_animal1': animalitos.get(animal1, ''),
        'nombre_animal2': animalitos.get(animal2, '')
    }

# ─── Análisis: Multiloterías ───────────────────────────────────────────────────

def buscar_patrones_multiloterias(loteria_ref, fecha_ref, loterias_comparar, fecha_inicio=None, fecha_fin=None, min_similitud=30):
    ref = obtener_resultados_dia(fecha_ref, loteria_ref)
    if not ref:
        return {'error': f'Sin resultados para {loteria_ref} en {fecha_ref}'}
    horarios_ref = ordenar_horarios(list(ref.keys()))
    if len(horarios_ref) < 2:
        return {'error': 'Se necesitan al menos 2 resultados'}
    ref_norm = normalizar_resultados_ml(ref)
    patrones = []
    for lot_cmp in loterias_comparar:
        if lot_cmp == loteria_ref:
            continue
        dias = obtener_dias_con_datos(lot_cmp, fecha_inicio, fecha_fin)
        for fd in dias:
            hist = obtener_resultados_dia(fd, lot_cmp)
            if not hist:
                continue
            hist_norm = normalizar_resultados_ml(hist)
            h_ref_norm = [normalizar_horario_ml(h) for h in horarios_ref]
            aciertos = total = 0
            for hn in h_ref_norm:
                if hn in ref_norm and hn in hist_norm:
                    if ref_norm[hn] == hist_norm[hn]:
                        aciertos += 1
                    total += 1
            if total == 0:
                continue
            sim = aciertos / total * 100
            if sim >= min_similitud:
                futuros = [
                    {'horario': h, 'animalito': hist[h], 'nombre_animalito': animalitos.get(hist[h], '')}
                    for h in ordenar_horarios(list(hist.keys()))
                    if normalizar_horario_ml(h) not in h_ref_norm
                ]
                patrones.append({
                    'loteria_referencia': loteria_ref, 'fecha_referencia': fecha_ref,
                    'loteria_comparada': lot_cmp, 'fecha_comparada': fd,
                    'similitud': round(sim, 1), 'aciertos': aciertos,
                    'total_comparaciones': total,
                    'resultados_futuros': futuros, 'total_futuros': len(futuros),
                    'horarios_referencia': horarios_ref
                })
    patrones.sort(key=lambda x: x['aciertos'], reverse=True)
    return {
        'patrones_multiloterias': patrones[:50],
        'resultados_referencia': ref,
        'horarios_referencia': horarios_ref,
        'loteria_referencia': loteria_ref, 'fecha_referencia': fecha_ref
    }

# ─── Multipronósticos ─────────────────────────────────────────────────────────

def generar_multi_pronosticos(loteria, fecha_referencia, fecha_inicio, fecha_fin):
    puntos = defaultdict(int)
    detalles = defaultdict(list)
    puntos_patrones = defaultdict(int)
    puntos_frecuencias = defaultdict(int)

    # ── 1. Patrones Históricos ─────────────────────────────────────────────────
    patrones_info = []
    res_pat = buscar_patrones_similares(loteria, fecha_referencia, fecha_inicio, fecha_fin, min_similitud=0)
    if 'error' not in res_pat:
        horarios_ref = res_pat.get('horarios_referencia', [])
        for p in [x for x in res_pat.get('patrones_similares', []) if x['aciertos'] >= 2]:
            hist = obtener_resultados_dia(p['fecha'], loteria)
            if not hist:
                continue
            hs_ord = ordenar_horarios(list(hist.keys()))
            siguiente_horario = None
            horario_anterior = None
            for i, h in enumerate(hs_ord):
                if h not in horarios_ref:
                    siguiente_horario = h
                    if i > 0:
                        horario_anterior = hs_ord[i - 1]
                    break
            if siguiente_horario and siguiente_horario in hist:
                ani = hist[siguiente_horario]
                puntos[ani] += 10
                puntos_patrones[ani] += 10
                detalles[ani].append('Patrones Históricos: +10')
                patrones_info.append({
                    'fecha_patron': p['fecha'],
                    'animalito_futuro': ani,
                    'horario_futuro': siguiente_horario,
                    'horario_anterior': horario_anterior,
                    'aciertos': p['aciertos'],
                    'similitud': p['similitud']
                })

    # ── 2. Bonus Seguimiento ───────────────────────────────────────────────────
    if patrones_info:
        ref_dia = obtener_resultados_dia(fecha_referencia, loteria)
        if ref_dia:
            for pi in patrones_info:
                h_ant = pi.get('horario_anterior')
                if h_ant and h_ant in ref_dia:
                    hist_pi = obtener_resultados_dia(pi['fecha_patron'], loteria)
                    if hist_pi and h_ant in hist_pi:
                        if hist_pi[h_ant] == ref_dia[h_ant]:
                            puntos[pi['animalito_futuro']] += 3
                            detalles[pi['animalito_futuro']].append('Bonus Seguimiento: +3')

    # ── 3. Multiloterías ──────────────────────────────────────────────────────
    otros = [l for l in loterias if l != loteria]
    res_ml = buscar_patrones_multiloterias(loteria, fecha_referencia, otros, fecha_inicio, fecha_fin, min_similitud=0)
    if 'error' not in res_ml:
        horarios_ref_norm = [normalizar_horario_ml(h) for h in res_ml.get('horarios_referencia', [])]
        for p in [x for x in res_ml.get('patrones_multiloterias', []) if x['aciertos'] >= 2]:
            hist_cmp = obtener_resultados_dia(p['fecha_comparada'], p['loteria_comparada'])
            if not hist_cmp:
                continue
            for hc in ordenar_horarios(list(hist_cmp.keys())):
                if normalizar_horario_ml(hc) not in horarios_ref_norm:
                    ani = hist_cmp[hc]
                    puntos[ani] += 5
                    detalles[ani].append('Multiloterías: +5')
                    break

    # ── 4. Frecuencias (top 5 + empates) ─────────────────────────────────────
    ref_dia = obtener_resultados_dia(fecha_referencia, loteria)
    ultimo_ani = None
    if ref_dia:
        hs = ordenar_horarios(list(ref_dia.keys()))
        if hs:
            ultimo_ani = ref_dia[hs[-1]]
    if ultimo_ani:
        for tipo in ('despues', 'antes'):
            res_f = analizar_frecuencias(loteria, fecha_inicio, fecha_fin, tipo)
            if 'error' not in res_f:
                top_list = res_f['frecuencias'].get(ultimo_ani, [])
                top5 = top_list[:5]
                if len(top5) >= 5:
                    frec_quinto = top5[4]['frecuencia']
                    top_final = [e for e in top_list if e['frecuencia'] >= frec_quinto][:6]
                else:
                    top_final = top5
                for entry in top_final:
                    ani = entry['animalito']
                    puntos[ani] += 10
                    puntos_frecuencias[ani] += 10
                    detalles[ani].append(f'Frecuencias ({tipo}): +10')

    # ── 5. Coincidencias Consecutivas (pares exactos) ─────────────────────────
    if ref_dia and len(ref_dia) >= 2:
        hs_ref = ordenar_horarios(list(ref_dia.keys()))
        pares = []
        for i in range(len(hs_ref) - 1):
            pares.append((ref_dia[hs_ref[i]], ref_dia[hs_ref[i+1]], hs_ref[i], hs_ref[i+1]))
        rows_cmc = _fetchall(
            "SELECT fecha, horario_sorteo, animalito_ganador FROM resultados "
            "WHERE fecha_iso BETWEEN %s AND %s AND fecha != %s AND loteria=%s "
            "ORDER BY fecha_iso, horario_sorteo",
            (fecha_dd_mm_yyyy_a_iso(fecha_inicio), fecha_dd_mm_yyyy_a_iso(fecha_fin),
             fecha_referencia, loteria)
        )
        if rows_cmc:
            por_dia_cmc = defaultdict(list)
            for r in rows_cmc:
                por_dia_cmc[r['fecha']].append((r['horario_sorteo'], r['animalito_ganador']))
            for a1, a2, h1_ref, h2_ref in pares:
                for fecha_c, res_dia_c in por_dia_cmc.items():
                    res_ord = sorted(res_dia_c, key=lambda x: convertir_horario_a_minutos(x[0]))
                    for i in range(len(res_ord) - 1):
                        if (res_ord[i][1] == a1 and res_ord[i+1][1] == a2
                                and res_ord[i][0] == h1_ref and res_ord[i+1][0] == h2_ref):
                            if i + 2 < len(res_ord):
                                ani_sig = res_ord[i+2][1]
                                puntos[ani_sig] += 10
                                detalles[ani_sig].append('Coincidencias Consecutivas: +10')
                            break

    # ── 6. Bonus Doble Fuente (Patrones + Frecuencias) ────────────────────────
    for ani in list(puntos.keys()):
        if puntos_patrones.get(ani, 0) > 0 and puntos_frecuencias.get(ani, 0) > 0:
            puntos[ani] += 20
            detalles[ani].append('Bonus Doble Fuente: +20')

    pronosticos = []
    for ani, pts in puntos.items():
        if ani in animalitos:
            pronosticos.append({
                'numero': ani, 'animalito': animalitos[ani],
                'puntuacion_total': pts,
                'detalles': detalles[ani],
                'fuentes': len(set(d.split(':')[0].strip() for d in detalles[ani]
                                   if not d.startswith('Bonus')))
            })
    pronosticos.sort(key=lambda x: x['puntuacion_total'], reverse=True)
    return {
        'pronosticos': pronosticos,
        'total_animalitos': len(pronosticos),
        'loteria': loteria, 'fecha_referencia': fecha_referencia
    }

# ─── Mantenimiento BD ─────────────────────────────────────────────────────────

def detectar_duplicados():
    rows = _fetchall("""
        SELECT fecha, loteria, horario_sorteo, COUNT(*) AS cantidad
        FROM resultados GROUP BY fecha, loteria, horario_sorteo HAVING COUNT(*) > 1
    """)
    return {
        'total_grupos_duplicados': len(rows),
        'total_registros_duplicados': sum(r['cantidad'] for r in rows)
    }


def eliminar_duplicados():
    conn = get_db_connection()
    if not conn:
        return {'error': 'Sin conexion'}
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM resultados WHERE id NOT IN (
                SELECT MAX(id) FROM resultados GROUP BY fecha, loteria, horario_sorteo
            )
        """)
        eliminados = cur.rowcount
        conn.commit()
        return {'success': True, 'registros_eliminados': eliminados}
    except Exception as e:
        conn.rollback()
        return {'error': str(e)}
    finally:
        conn.close()
