/* ─── Utility ──────────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const fmt = d => d ? new Date(d + 'T12:00:00').toLocaleDateString('es-VE') : '';
const isoToLocal = iso => iso ? iso.split('-').reverse().join('/') : '';
const localToIso = local => local ? local.split('/').reverse().join('-') : '';
const dateInputToLocal = v => v ? v.split('-').reverse().join('/') : '';
const localToDateInput = v => v ? v.split('/').reverse().join('-') : '';



function showToast(msg, type = 'info') {
    const t = $('toast');
    t.textContent = msg;
    t.className = `show ${type}`;
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.className = '', 3000);
}

function setStatus(id, msg) {
    const el = $(id);
    if (el) el.textContent = msg;
}

async function fetchApi(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

async function postApi(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

function showModal(id) { $(id).style.display = 'flex'; }
function hideModal(id) { $(id).style.display = 'none'; }

/* ─── Clear a tbody ────────────────────────────────────────────────────────── */
function clearTable(id) { $(id).innerHTML = ''; }

function addRow(tbodyId, cells, cls = '') {
    const tr = document.createElement('tr');
    if (cls) tr.className = cls;
    tr.innerHTML = cells.map(c => `<td>${c ?? ''}</td>`).join('');
    $(tbodyId).appendChild(tr);
    return tr;
}

/* ─── Date defaults ────────────────────────────────────────────────────────── */
function today() { return new Date().toISOString().slice(0, 10); }
function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d.toISOString().slice(0, 10);
}

/* ════════════ RESULTADOS ════════════ */
async function cargarResultados() {
    const fi = dateInputToLocal($('r_fi').value);
    const ff = dateInputToLocal($('r_ff').value);
    const lot = $('r_lot').value;
    const hor = $('r_hor').value;
    clearTable('bodyResultados');
    try {
        const data = await fetchApi(`/api/resultados?fecha_inicio=${fi}&fecha_fin=${ff}&loteria=${lot}&horario=${hor}`);
        $('badgeCount').textContent = `${data.total} registros`;
        data.resultados.forEach(r => {
            addRow('bodyResultados', [r.fecha, r.loteria, r.horario_sorteo,
            `<span class="badge-blue">${r.animalito_ganador}</span>`, r.animalito_nombre]);
        });
        if (!data.resultados.length) showToast('Sin resultados para ese filtro', 'info');
    } catch (e) { showToast('Error al cargar resultados: ' + e.message, 'error'); }
}

function limpiarFiltrosResultados() {
    $('r_fi').value = daysAgo(7);
    $('r_ff').value = today();
    $('r_lot').value = 'TODAS';
    $('r_hor').value = 'TODOS';
    cargarResultados();
}

function exportarCSV() {
    const rows = [...$('tblResultados').querySelectorAll('tbody tr')];
    if (!rows.length) { showToast('Sin datos', 'info'); return; }
    const headers = [...$('tblResultados').querySelectorAll('thead th')].map(t => t.textContent.replace(/[^\w\s]/g, '').trim());
    const csv = [headers.join(','),
    ...rows.map(r => [...r.cells].map(c => `"${c.textContent.trim()}"`).join(','))
    ].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `resultados_${today()}.csv`;
    a.click();
    showToast('CSV exportado', 'success');
}

/* ─── Scraping modal ─── */
async function iniciarScraping() {
    const fi = dateInputToLocal($('sc_fi').value);
    const ff = dateInputToLocal($('sc_ff').value);
    const loterias = [...document.querySelectorAll('.sc-check:checked')].map(c => c.value);
    if (!loterias.length) { showToast('Selecciona al menos una lotería', 'error'); return; }
    setStatus('statusScraping', 'Iniciando scraping... (puede tardar varios minutos)');
    try {
        const data = await postApi('/api/scraping', { fecha_inicio: fi, fecha_fin: ff, loterias });
        setStatus('statusScraping', data.error ? 'Error: ' + data.error : `Completado. ${data.total_resultados} resultados cargados.`);
        if (!data.error) { showToast('Scraping completado', 'success'); cargarResultados(); }
    } catch (e) { setStatus('statusScraping', 'Error: ' + e.message); showToast('Error en scraping', 'error'); }
}

/* ─── Auto-scraping toggle ─── */
$('toggleAutoScraping').addEventListener('change', async function () {
    const data = await postApi('/api/auto-scraping', { activo: this.checked });
    showToast(data.activo ? 'Auto-Scraping activado' : 'Auto-Scraping desactivado', 'info');
});
setInterval(async () => {
    const data = await fetchApi('/api/auto-scraping/status');
    $('lastUpdate').textContent = data.ultima_actualizacion;
}, 30000);

/* ════════════ PATRONES HISTÓRICOS ════════════ */
async function cargarReferencia(prefix) {
    const lot = $(prefix + '_lot').value;
    const fecha = dateInputToLocal($(prefix + '_ref').value);
    const tbodyId = prefix === 'p' ? 'bodyPRef' : 'bodyARef';
    clearTable(tbodyId);
    try {
        const data = await fetchApi(`/api/patrones/referencia?loteria=${encodeURIComponent(lot)}&fecha=${fecha}`);
        data.resultados.forEach(r => {
            addRow(tbodyId, [r.horario, `<span class="badge-blue">${r.codigo}</span>`, r.nombre]);
        });
        if (prefix === 'p') setStatus('statusPatrones', `${data.resultados.length} resultados de referencia cargados.`);
        else setStatus('statusAnimales', `${data.resultados.length} resultados de referencia cargados.`);
    } catch (e) { showToast('Error cargando referencia: ' + e.message, 'error'); }
}

async function buscarPatrones() {
    const lot = $('p_lot').value;
    const fr = dateInputToLocal($('p_ref').value);
    const fi = dateInputToLocal($('p_fi').value);
    const ff = dateInputToLocal($('p_ff').value);
    const sim = $('p_sim').value;
    setStatus('statusPatrones', 'Buscando patrones...');
    clearTable('bodyPDias'); clearTable('bodyPDet');
    try {
        const data = await fetchApi(`/api/patrones/similares?loteria=${encodeURIComponent(lot)}&fecha_referencia=${fr}&fecha_inicio=${fi}&fecha_fin=${ff}&min_similitud=${sim}`);
        if (data.error) { setStatus('statusPatrones', data.error); return; }
        const patrones = data.patrones_similares || [];
        // Store for click-detail
        window._patronesData = { patrones, lot, fr, ref: data.resultados_referencia || {}, hRef: data.horarios_referencia || [] };
        patrones.forEach((p, i) => {
            const tr = addRow('bodyPDias', [p.fecha, `<span class="badge-blue">${p.similitud}%</span>`,
            `<span class="badge-green">${p.aciertos}</span>`, p.total_comparaciones, p.total_futuros]);
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => mostrarDetallePatron(i));
        });
        setStatus('statusPatrones', `${patrones.length} patrones encontrados en ${fi} – ${ff}.`);
    } catch (e) { setStatus('statusPatrones', 'Error: ' + e.message); }
}

function mostrarDetallePatron(idx) {
    clearTable('bodyPDet');
    const d = window._patronesData;
    if (!d) return;
    const p = d.patrones[idx];
    const ref = d.ref;
    const hRef = d.hRef;
    (p.resultados_futuros || []).forEach(rf => {
        const isRef = hRef.includes(rf.horario);
        const isAcierto = isRef && ref[rf.horario] === rf.animalito;
        let badge, est;
        if (!isRef) { badge = 'badge-purp'; est = '🔮 FUTURO'; }
        else if (isAcierto) { badge = 'badge-green'; est = '✅ ACIERTO'; }
        else { badge = 'badge-red'; est = '❌ NO ACIERTO'; }
        addRow('bodyPDet', [rf.horario, `<span class="${badge}">${rf.animalito}</span>`, rf.nombre_animalito, est]);
    });
}

async function pronosticarPatrones() {
    const lot = $('p_lot').value;
    const fr = dateInputToLocal($('p_ref').value);
    const fi = dateInputToLocal($('p_fi').value);
    const ff = dateInputToLocal($('p_ff').value);
    const top = $('p_top').value;
    setStatus('statusPatrones', 'Generando pronósticos...');
    clearTable('bodyPPron');
    try {
        const data = await fetchApi(`/api/patrones/pronosticos?loteria=${encodeURIComponent(lot)}&fecha_referencia=${fr}&fecha_inicio=${fi}&fecha_fin=${ff}&top_n=${top}`);
        if (data.error) { setStatus('statusPatrones', data.error); return; }
        (data.pronosticos || []).forEach((p, i) => {
            addRow('bodyPPron', [i + 1, `<span class="badge-blue">${p.numero}</span>`, p.animalito,
            `<span class="badge-amber">${p.puntuacion}</span>`, p.frecuencia]);
        });
        setStatus('statusPatrones', `${data.pronosticos?.length || 0} pronósticos. Mejor similitud: ${data.mejor_similitud}%`);
    } catch (e) { setStatus('statusPatrones', 'Error: ' + e.message); }
}

/* ════════════ PATRONES ANIMALES ════════════ */
async function buscarAnimales() {
    const lot = $('a_lot').value;
    const fr = dateInputToLocal($('a_ref').value);
    const fi = dateInputToLocal($('a_fi').value);
    const ff = dateInputToLocal($('a_ff').value);
    const sim = $('a_sim').value;
    setStatus('statusAnimales', 'Buscando patrones de animales...');
    clearTable('bodyADias'); clearTable('bodyADet');
    await cargarReferencia('a');
    try {
        const data = await fetchApi(`/api/animales/patrones?loteria=${encodeURIComponent(lot)}&fecha_referencia=${fr}&fecha_inicio=${fi}&fecha_fin=${ff}&min_similitud=${sim}`);
        if (data.error) { setStatus('statusAnimales', data.error); return; }
        const patrones = data.patrones_similares || [];
        window._animalesData = { patrones, lot, fr };
        patrones.forEach((p, i) => {
            const tr = addRow('bodyADias', [p.fecha, `<span class="badge-green">${p.aciertos}</span>`,
            `<span class="badge-blue">${p.similitud}%</span>`, p.animales_referencia, p.animales_historicos, p.total_futuros]);
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => mostrarDetalleAnimal(i));
        });
        const max = patrones.length ? Math.max(...patrones.map(p => p.aciertos)) : 0;
        setStatus('statusAnimales', `${patrones.length} patrones encontrados. Máx aciertos: ${max}.`);
    } catch (e) { setStatus('statusAnimales', 'Error: ' + e.message); }
}

function mostrarDetalleAnimal(idx) {
    clearTable('bodyADet');
    const d = window._animalesData;
    if (!d) return;
    const p = d.patrones[idx];
    (p.animales_futuros || []).forEach(af => {
        addRow('bodyADet', ['–', `<span class="badge-blue">${af.animalito}</span>`, af.nombre_animalito,
            '<span class="badge-purp">🔮 FUTURO</span>']);
    });
}

async function pronosticarAnimales() {
    const lot = $('a_lot').value;
    const fr = dateInputToLocal($('a_ref').value);
    const fi = dateInputToLocal($('a_fi').value);
    const ff = dateInputToLocal($('a_ff').value);
    const top = $('a_top').value;
    setStatus('statusAnimales', 'Generando pronósticos mejorados...');
    clearTable('bodyAPron');
    try {
        const data = await fetchApi(`/api/animales/pronosticos?loteria=${encodeURIComponent(lot)}&fecha_referencia=${fr}&fecha_inicio=${fi}&fecha_fin=${ff}&top_n=${top}`);
        if (data.error) { setStatus('statusAnimales', data.error); return; }
        (data.pronosticos || []).forEach((p, i) => {
            addRow('bodyAPron', [i + 1, `<span class="badge-blue">${p.numero}</span>`, p.animalito,
            `<span class="badge-amber">${p.puntuacion}</span>`, p.fechas_aparicion]);
        });
        setStatus('statusAnimales', `${data.pronosticos?.length || 0} pronósticos. Máx aciertos: ${data.max_aciertos}.`);
    } catch (e) { setStatus('statusAnimales', 'Error: ' + e.message); }
}

/* ════════════ MULTILOTERÍAS ════════════ */
async function buscarMultiloterias() {
    const lot = $('ml_lot').value;
    const fr = dateInputToLocal($('ml_ref').value);
    const fi = dateInputToLocal($('ml_fi').value);
    const ff = dateInputToLocal($('ml_ff').value);
    const sim = $('ml_sim').value;
    const lots = [...document.querySelectorAll('.ml-check:checked')].map(c => c.value);
    setStatus('statusML', 'Buscando patrones multiloterías...');
    clearTable('bodyML'); clearTable('bodyMLDet');
    if (!lots.length) { showToast('Selecciona al menos una lotería', 'error'); return; }
    try {
        const params = new URLSearchParams({ loteria: lot, fecha_referencia: fr, fecha_inicio: fi, fecha_fin: ff, min_similitud: sim });
        lots.forEach(l => params.append('loterias', l));
        const data = await fetchApi(`/api/multiloterias?${params}`);
        if (data.error) { setStatus('statusML', data.error); return; }
        const patrones = data.patrones_multiloterias || [];
        window._mlData = { patrones, ref: data.resultados_referencia || {}, hRef: data.horarios_referencia || [] };
        patrones.forEach((p, i) => {
            const tr = addRow('bodyML', [p.loteria_comparada, p.fecha_comparada,
            `<span class="badge-blue">${p.similitud}%</span>`,
            `<span class="badge-green">${p.aciertos}</span>`, p.total_comparaciones]);
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => mostrarDetalleML(i));
        });
        setStatus('statusML', `${patrones.length} patrones multilotería encontrados.`);
    } catch (e) { setStatus('statusML', 'Error: ' + e.message); }
}

function mostrarDetalleML(idx) {
    clearTable('bodyMLDet');
    const d = window._mlData;
    if (!d) return;
    const p = d.patrones[idx];
    const ref = d.ref;
    const hRef = d.hRef;
    (p.resultados_futuros || []).forEach(rf => {
        const isRef = hRef.includes(rf.horario);
        addRow('bodyMLDet', [rf.horario, '—',
        `<span class="badge-purp">${rf.animalito} ${rf.nombre_animalito}</span>`,
        isRef ? '🔮 FUTURO' : '🔮 FUTURO']);
    });
    (p.horarios_referencia || hRef).forEach(h => {
        const refVal = ref[h] || 'N/A';
        addRow('bodyMLDet', [h,
            `${refVal} ${ANIMALITOS[refVal] || ''}`,
            '—', '📊 REF']);
    });
}

/* ════════════ FRECUENCIAS ════════════ */
async function analizarFrecuencias() {
    const lot = $('f_lot').value;
    const fi = dateInputToLocal($('f_fi').value);
    const ff = dateInputToLocal($('f_ff').value);
    const tipo = $('f_tipo').value;
    const topN = Math.min(parseInt($('f_top').value) || 10, 10);
    setStatus('statusFrec', 'Analizando frecuencias...');
    $('tblFrecHead').innerHTML = '';
    $('tblFrecBody').innerHTML = '';
    try {
        const data = await fetchApi(`/api/frecuencias?loteria=${encodeURIComponent(lot)}&fecha_inicio=${fi}&fecha_fin=${ff}&tipo=${tipo}`);
        if (data.error) { setStatus('statusFrec', data.error); return; }
        const frec = data.frecuencias;
        const labels = ['#', 'Referencia', ...Array.from({ length: topN }, (_, i) => i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}°`).flatMap(l => [l, 'Animal', 'Frec'])];
        const headTr = document.createElement('tr');
        labels.forEach((l, ci) => {
            const th = document.createElement('th');
            th.textContent = l;
            th.style.background = ci < 2 ? 'rgba(79,70,229,0.8)' : 'rgba(99,102,241,0.5)';
            th.style.color = '#fff';
            headTr.appendChild(th);
        });
        $('tblFrecHead').appendChild(headTr);
        const animals = Object.keys(frec).sort((a, b) => {
            const na = isNaN(a) ? Infinity : Number(a);
            const nb = isNaN(b) ? Infinity : Number(b);
            return na - nb;
        });
        animals.forEach((ani, ri) => {
            const nombre = ANIMALITOS[ani] || '';
            const top = (frec[ani] || []).slice(0, topN);
            const tr = document.createElement('tr');
            const tdNum = document.createElement('td');
            tdNum.innerHTML = `<span class="badge-blue">${ani}</span>`;
            tr.appendChild(tdNum);
            const tdNom = document.createElement('td');
            tdNom.textContent = nombre;
            tdNom.className = 'frec-ref';
            tr.appendChild(tdNom);
            for (let i = 0; i < topN; i++) {
                const entry = top[i];
                const cells = entry ? [entry.animalito, entry.nombre, entry.frecuencia] : ['', '', ''];
                cells.forEach((v, ci) => {
                    const td = document.createElement('td');
                    td.textContent = v;
                    if (ci === 0 && v) td.innerHTML = `<span class="badge-purp">${v}</span>`;
                    tr.appendChild(td);
                });
            }
            $('tblFrecBody').appendChild(tr);
        });
        const tipoTexto = tipo === 'despues' ? 'DESPUÉS' : 'ANTES';
        setStatus('statusFrec', `${animals.length} animales. Top ${topN} animales ${tipoTexto}.`);
    } catch (e) { setStatus('statusFrec', 'Error: ' + e.message); }
}

/* ════════════ MULTIPRONÓSTICOS ════════════ */
async function generarMultipronosticos() {
    const lot = $('mp_lot').value;
    const fr = dateInputToLocal($('mp_ref').value);
    const fi = dateInputToLocal($('mp_fi').value);
    const ff = dateInputToLocal($('mp_ff').value);
    setStatus('statusMP', 'Generando multipronósticos...');
    clearTable('bodyMP');
    try {
        const data = await fetchApi(`/api/multipronosticos?loteria=${encodeURIComponent(lot)}&fecha_referencia=${fr}&fecha_inicio=${fi}&fecha_fin=${ff}`);
        if (data.error) { setStatus('statusMP', data.error); return; }
        (data.pronosticos || []).forEach((p, i) => {
            const rank = i < 3 ? ['🥇', '🥈', '🥉'][i] : i + 1;
            addRow('bodyMP', [
                rank,
                `<span class="badge-blue">${p.numero}</span>`,
                `<strong>${p.animalito}</strong>`,
                `<span class="badge-amber" style="font-size:14px;font-weight:800">${p.puntuacion_total}</span>`,
                `<span class="badge-purp">${p.fuentes}</span>`,
                `<small style="color:var(--text-muted)">${(p.detalles || []).join(' | ')}</small>`
            ]);
        });
        setStatus('statusMP', `${data.pronosticos?.length || 0} multipronósticos generados para ${lot} – ${fr}.`);
        if (data.pronosticos?.length) showToast(`Top 1: ${data.pronosticos[0].animalito} (${data.pronosticos[0].puntuacion_total} pts)`, 'success');
    } catch (e) { setStatus('statusMP', 'Error: ' + e.message); }
}

/* ════════════ COINCIDENCIAS ════════════ */
async function buscarCoincidencias() {
    const lot = $('c_lot').value;
    const a1 = $('c_a1').value;
    const a2 = $('c_a2').value;
    const fi = dateInputToLocal($('c_fi').value);
    const ff = dateInputToLocal($('c_ff').value);
    if (a1 === a2) { showToast('Los animales deben ser diferentes', 'error'); return; }
    setStatus('statusCoinc', 'Buscando coincidencias...');
    clearTable('bodyCoincFechas'); clearTable('bodyCoincDia');
    try {
        const data = await fetchApi(`/api/coincidencias?loteria=${encodeURIComponent(lot)}&animal1=${a1}&animal2=${a2}&fecha_inicio=${fi}&fecha_fin=${ff}`);
        if (data.error) { setStatus('statusCoinc', data.error); return; }
        window._coincData = { lot, a1, a2, data };
        (data.fechas_coincidentes || []).forEach((c, i) => {
            const tr = addRow('bodyCoincFechas', [c.fecha, c.horario_animal1, c.horario_animal2, c.posicion, c.total_resultados_dia]);
            tr.style.cursor = 'pointer';
            tr.addEventListener('click', () => mostrarDiaCoincidencia(c));
        });
        setStatus('statusCoinc', `${data.total_coincidencias} coincidencias: ${a1}(${data.nombre_animal1}) → ${a2}(${data.nombre_animal2})`);
    } catch (e) { setStatus('statusCoinc', 'Error: ' + e.message); }
}

async function mostrarDiaCoincidencia(coinc) {
    clearTable('bodyCoincDia');
    const lot = $('c_lot').value;
    try {
        const data = await fetchApi(`/api/coincidencias/dia?loteria=${encodeURIComponent(lot)}&fecha=${coinc.fecha}`);
        (data.resultados || []).forEach(r => {
            const isCoinc = r.horario === coinc.horario_animal1 || r.horario === coinc.horario_animal2;
            addRow('bodyCoincDia', [r.horario,
            `<span class="${isCoinc ? 'badge-amber' : 'badge-blue'}">${r.codigo}</span>`,
            r.nombre,
            isCoinc ? '<span class="badge-amber">🟡 COINC.</span>' : '<span style="color:var(--text-muted)">Normal</span>'
            ]);
        });
    } catch (e) { }
}

/* ════════════ CONFIGURACIÓN ════════════ */
async function mostrarEstadisticas() {
    try {
        const data = await fetchApi('/api/estadisticas');
        $('statsGrid').innerHTML = `
      <div class="stat-box"><div class="stat-val">${data.total}</div><div class="stat-lbl">Total Resultados</div></div>
      <div class="stat-box"><div class="stat-val" style="font-size:18px">${data.fecha_min}</div><div class="stat-lbl">Fecha Mínima</div></div>
      <div class="stat-box"><div class="stat-val" style="font-size:18px">${data.fecha_max}</div><div class="stat-lbl">Fecha Máxima</div></div>
    `;
        showToast('Estadísticas cargadas', 'success');
    } catch (e) { showToast('Error: ' + e.message, 'error'); }
}

async function verificarDuplicados() {
    const data = await fetchApi('/api/db/duplicados');
    showToast(`Duplicados: ${data.total_grupos_duplicados} grupos, ${data.total_registros_duplicados} registros`, 'info');
}

async function eliminarDuplicados() {
    if (!confirm('¿Eliminar duplicados?')) return;
    const data = await postApi('/api/db/eliminar-duplicados', {});
    if (data.success) showToast(`${data.registros_eliminados} registros eliminados`, 'success');
    else showToast('Error: ' + data.error, 'error');
}

/* ─── Tab navigation ─── */
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        item.classList.add('active');
        const tab = item.dataset.tab;
        $('tab-' + tab).classList.add('active');
        // Auto-load actions per tab
        if (tab === 'resultados') cargarResultados();
        if (tab === 'configuracion') mostrarEstadisticas();
        if (tab === 'patrones') cargarReferencia('p');
        if (tab === 'animales') cargarReferencia('a');
    });
});

/* ─── Init ─── */
window.addEventListener('DOMContentLoaded', () => {
    cargarResultados();
    mostrarEstadisticas();
});
