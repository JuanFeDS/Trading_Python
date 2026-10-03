"""Servidor HTTP local: dashboard en vivo con grafico de velas y posiciones abiertas.

La pagina hace polling a /api/velas y /api/posiciones cada pocos segundos
via JS (sin recargar), asi que el grafico y la tabla se actualizan solos.
Sin dependencias nuevas (http.server de la libreria estandar).
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
import MetaTrader5 as mt5

from config.estrategias_vivo import CONFIGURACION
from config.settings import ConfiguracionMetaTrader

PUERTO = 8765
TIMEFRAME = mt5.TIMEFRAME_M5
VELAS_A_MOSTRAR = 120
INTERVALO_ACTUALIZACION_MS = 1000

MAGIC_A_ESTRATEGIA = {magic: nombre for nombre, magic, _ in CONFIGURACION}
SIMBOLOS_ACTIVOS = sorted({simbolo for _, _, simbolo in CONFIGURACION})


def _iniciar_conexion(configuracion: ConfiguracionMetaTrader) -> None:
    argumentos = {
        "login": configuracion.login,
        "password": configuracion.password,
        "server": configuracion.server,
    }
    if configuracion.ruta_terminal:
        argumentos["path"] = configuracion.ruta_terminal

    if not mt5.initialize(**argumentos):
        raise RuntimeError(f"No se pudo conectar a MT5: {mt5.last_error()}")


def _posiciones_json() -> str:
    posiciones = sorted(mt5.positions_get() or [], key=lambda p: p.magic)
    filas = [
        {
            "estrategia": MAGIC_A_ESTRATEGIA.get(p.magic, "desconocida"),
            "simbolo": p.symbol,
            "ticket": p.ticket,
            "tipo": "Compra" if p.type == mt5.ORDER_TYPE_BUY else "Venta",
            "volumen": p.volume,
            "precio_apertura": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": round(p.profit, 2),
        }
        for p in posiciones
    ]
    profit_total = round(sum(fila["profit"] for fila in filas), 2)
    return json.dumps({"posiciones": filas, "profit_total": profit_total})


def _velas_json(simbolo: str) -> str:
    if simbolo not in SIMBOLOS_ACTIVOS or not mt5.symbol_select(simbolo, True):
        return json.dumps([])

    velas = mt5.copy_rates_from_pos(simbolo, TIMEFRAME, 0, VELAS_A_MOSTRAR)
    if velas is None:
        return json.dumps([])

    datos = [
        {
            "time": int(vela["time"]),
            "open": float(vela["open"]),
            "high": float(vela["high"]),
            "low": float(vela["low"]),
            "close": float(vela["close"]),
        }
        for vela in velas
    ]
    return json.dumps(datos)


def _digitos_por_simbolo() -> dict:
    digitos = {}
    for simbolo in SIMBOLOS_ACTIVOS:
        info = mt5.symbol_info(simbolo)
        digitos[simbolo] = info.digits if info else 5
    return digitos


def _pagina_html() -> str:
    botones_simbolos = "".join(f'<button class="tab" data-simbolo="{s}">{s}</button>' for s in SIMBOLOS_ACTIVOS)
    simbolo_inicial = SIMBOLOS_ACTIVOS[0]
    digitos_json = json.dumps(_digitos_por_simbolo())

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Dashboard en vivo</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
  body {{ font-family: system-ui, sans-serif; background:#0d1117; color:#e6edf3; padding:1.5rem; margin:0; }}
  h1 {{ font-size:1.3rem; margin:0 0 0.3rem 0; }}
  .nota {{ color:#8b949e; font-size:0.85rem; margin:0 0 1rem 0; }}
  .tabs {{ display:flex; gap:0.5rem; margin-bottom:0.8rem; }}
  .tab {{ background:#161b22; color:#e6edf3; border:1px solid #30363d; border-radius:6px; padding:0.4rem 0.9rem; cursor:pointer; font-size:0.9rem; }}
  .tab.activo {{ background:#1f6feb; border-color:#1f6feb; }}
  #grafico {{ border:1px solid #30363d; border-radius:8px; }}
  table {{ border-collapse: collapse; width:100%; margin-top:1.5rem; }}
  th, td {{ padding:0.5rem 0.8rem; border-bottom:1px solid #30363d; text-align:left; }}
  th {{ color:#8b949e; font-weight:600; font-size:0.8rem; text-transform:uppercase; }}
  tbody tr {{ cursor:pointer; }}
  tbody tr:hover {{ background:#161b22; }}
  tbody tr.seleccionada {{ background:#1f2937; }}
  .total {{ margin-top:1rem; font-size:1.1rem; }}
</style>
</head>
<body>
  <h1>Dashboard en vivo</h1>
  <p class="nota">Se actualiza solo cada {INTERVALO_ACTUALIZACION_MS // 1000} segundos, sin recargar.</p>

  <div class="tabs">{botones_simbolos}</div>
  <div id="grafico"></div>

  <table>
    <thead><tr><th>Estrategia</th><th>Simbolo</th><th>Ticket</th><th>Tipo</th><th>Volumen</th><th>Precio apertura</th><th>Profit</th></tr></thead>
    <tbody id="cuerpo-tabla"></tbody>
  </table>
  <p class="total">Profit total: <span id="profit-total">0.00</span> USD</p>

<script>
const INTERVALO_MS = {INTERVALO_ACTUALIZACION_MS};
const DIGITOS_POR_SIMBOLO = {digitos_json};
let simboloActual = "{simbolo_inicial}";
let ultimasPosiciones = [];
let ticketSeleccionado = null;
let lineasPrecio = [];

function aplicarPrecisionPrecio(simbolo) {{
  const digitos = DIGITOS_POR_SIMBOLO[simbolo] ?? 5;
  serieVelas.applyOptions({{
    priceFormat: {{ type: 'price', precision: digitos, minMove: 1 / (10 ** digitos) }},
  }});
}}

const grafico = LightweightCharts.createChart(document.getElementById('grafico'), {{
  width: document.getElementById('grafico').clientWidth,
  height: 400,
  layout: {{ background: {{ color: '#0d1117' }}, textColor: '#e6edf3' }},
  grid: {{ vertLines: {{ color: '#21262d' }}, horzLines: {{ color: '#21262d' }} }},
  timeScale: {{ timeVisible: true, secondsVisible: false }},
}});
const serieVelas = grafico.addCandlestickSeries({{
  upColor: '#3fb950', downColor: '#f85149', borderVisible: false,
  wickUpColor: '#3fb950', wickDownColor: '#f85149',
  lastValueVisible: false, priceLineVisible: false,
}});
aplicarPrecisionPrecio(simboloActual);

window.addEventListener('resize', () => {{
  grafico.applyOptions({{ width: document.getElementById('grafico').clientWidth }});
}});

async function actualizarVelas() {{
  const respuesta = await fetch(`/api/velas?simbolo=${{encodeURIComponent(simboloActual)}}`);
  const velas = await respuesta.json();
  serieVelas.setData(velas);
}}

function limpiarLineasPrecio() {{
  lineasPrecio.forEach(linea => serieVelas.removePriceLine(linea));
  lineasPrecio = [];
}}

function dibujarLineasPosicion(posicion) {{
  limpiarLineasPrecio();
  lineasPrecio.push(serieVelas.createPriceLine({{
    price: posicion.precio_apertura, color: '#e3b341', lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: 'Entrada',
  }}));
  if (posicion.sl) {{
    lineasPrecio.push(serieVelas.createPriceLine({{
      price: posicion.sl, color: '#f85149', lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: 'SL',
    }}));
  }}
  if (posicion.tp) {{
    lineasPrecio.push(serieVelas.createPriceLine({{
      price: posicion.tp, color: '#3fb950', lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true, title: 'TP',
    }}));
  }}
}}

async function seleccionarSimbolo(simbolo) {{
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('activo', b.dataset.simbolo === simbolo));
  simboloActual = simbolo;
  aplicarPrecisionPrecio(simbolo);
  await actualizarVelas();
}}

async function seleccionarPosicion(ticket) {{
  const posicion = ultimasPosiciones.find(p => p.ticket === ticket);
  if (!posicion) return;
  ticketSeleccionado = ticket;

  if (posicion.simbolo !== simboloActual) {{
    await seleccionarSimbolo(posicion.simbolo);
  }}
  dibujarLineasPosicion(posicion);
  actualizarPosiciones();
}}

async function actualizarPosiciones() {{
  const respuesta = await fetch('/api/posiciones');
  const datos = await respuesta.json();
  ultimasPosiciones = datos.posiciones;
  const cuerpo = document.getElementById('cuerpo-tabla');

  if (datos.posiciones.length === 0) {{
    cuerpo.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#8b949e">Sin posiciones abiertas</td></tr>';
  }} else {{
    cuerpo.innerHTML = datos.posiciones.map(p => {{
      const color = p.profit >= 0 ? '#3fb950' : '#f85149';
      const seleccionada = p.ticket === ticketSeleccionado ? ' seleccionada' : '';
      return `<tr data-ticket="${{p.ticket}}" class="${{seleccionada}}">
        <td>${{p.estrategia}}</td><td>${{p.simbolo}}</td><td>${{p.ticket}}</td>
        <td>${{p.tipo}}</td><td>${{p.volumen}}</td><td>${{p.precio_apertura.toFixed(5)}}</td>
        <td style="color:${{color}}">${{p.profit.toFixed(2)}}</td>
      </tr>`;
    }}).join('');

    cuerpo.querySelectorAll('tr').forEach(fila => {{
      fila.addEventListener('click', () => seleccionarPosicion(Number(fila.dataset.ticket)));
    }});
  }}

  const total = document.getElementById('profit-total');
  total.textContent = datos.profit_total.toFixed(2);
  total.style.color = datos.profit_total >= 0 ? '#3fb950' : '#f85149';

  if (ticketSeleccionado !== null && !datos.posiciones.some(p => p.ticket === ticketSeleccionado)) {{
    ticketSeleccionado = null;
    limpiarLineasPrecio();
  }}
}}

document.querySelectorAll('.tab').forEach(boton => {{
  if (boton.dataset.simbolo === simboloActual) boton.classList.add('activo');
  boton.addEventListener('click', () => seleccionarSimbolo(boton.dataset.simbolo));
}});

actualizarVelas();
actualizarPosiciones();
setInterval(actualizarVelas, INTERVALO_MS);
setInterval(actualizarPosiciones, INTERVALO_MS);
</script>
</body>
</html>"""


class ManejadorDashboard(BaseHTTPRequestHandler):
    def do_GET(self):
        ruta = urlparse(self.path)

        if ruta.path == "/":
            self._responder_html(_pagina_html())
        elif ruta.path == "/api/posiciones":
            self._responder_json(_posiciones_json())
        elif ruta.path == "/api/velas":
            parametros = parse_qs(ruta.query)
            simbolo = parametros.get("simbolo", [SIMBOLOS_ACTIVOS[0]])[0]
            self._responder_json(_velas_json(simbolo))
        else:
            self.send_response(404)
            self.end_headers()

    def _responder_html(self, contenido: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(contenido.encode("utf-8"))

    def _responder_json(self, contenido: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(contenido.encode("utf-8"))

    def log_message(self, formato, *args):
        pass


def ejecutar():
    load_dotenv()
    configuracion = ConfiguracionMetaTrader()
    _iniciar_conexion(configuracion)

    print(f"Dashboard en http://localhost:{PUERTO}  (Ctrl+C para detener)")
    servidor = HTTPServer(("localhost", PUERTO), ManejadorDashboard)
    try:
        servidor.serve_forever()
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    ejecutar()
