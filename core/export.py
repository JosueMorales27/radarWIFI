# -*- coding: utf-8 -*-
"""
export - reportes de escaneos en CSV / JSON / HTML (estilo Kali, oscuro).

Todo se genera como string (el server decide el nombre y el Content-Type).
"""
import io
import csv
import json
import html


def to_json(networks: list, meta: dict = None) -> str:
    return json.dumps({"meta": meta or {}, "networks": networks},
                      ensure_ascii=False, indent=2)


def to_csv(networks: list) -> str:
    buf = io.StringIO()
    cols = ["ssid", "bssid", "vendor", "signal", "rssi", "channel",
            "band", "auth", "enc", "open"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for n in networks:
        row = dict(n)
        row["open"] = "SI" if n.get("open") else "no"
        w.writerow(row)
    return buf.getvalue()


_HTML_TMPL = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>radarWIFI PRO - reporte</title>
<style>
  body{{background:#0a0e0a;color:#c7ffcf;font-family:Consolas,'Courier New',monospace;margin:0;padding:28px}}
  h1{{color:#39ff14;text-shadow:0 0 8px #39ff14;border-bottom:1px solid #1f3d1f;padding-bottom:10px}}
  .meta{{color:#6aa06a;margin:6px 0 22px}}
  table{{border-collapse:collapse;width:100%;font-size:13px}}
  th,td{{border:1px solid #1f3d1f;padding:7px 9px;text-align:left}}
  th{{background:#0f1a0f;color:#39ff14;position:sticky;top:0}}
  tr:nth-child(even){{background:#0c120c}}
  .open{{color:#ff4d4d;font-weight:bold}}
  .strong{{color:#39ff14}} .weak{{color:#3a7bd5}}
  .foot{{margin-top:22px;color:#4d7a4d;font-size:12px}}
</style></head><body>
<h1>&#128225; radarWIFI PRO &mdash; reporte de redes</h1>
<div class="meta">{meta}</div>
<table><thead><tr>
<th>SSID</th><th>BSSID</th><th>Fabricante</th><th>Senal</th><th>RSSI</th>
<th>Canal</th><th>Banda</th><th>Seguridad</th></tr></thead><tbody>
{rows}
</tbody></table>
<div class="foot">Generado 100% localmente por radarWIFI PRO. Ningun dato salio de tu equipo.</div>
</body></html>"""


def to_html(networks: list, meta: dict = None) -> str:
    meta = meta or {}
    meta_str = " &middot; ".join("{}: {}".format(html.escape(str(k)), html.escape(str(v)))
                                 for k, v in meta.items())
    rows = []
    for n in networks:
        sig = n.get("signal", 0) or 0
        cls = "strong" if sig >= 60 else ("weak" if sig < 35 else "")
        auth = html.escape(str(n.get("auth", "?")))
        auth_cell = '<span class="open">ABIERTA &#9888;</span>' if n.get("open") else auth
        rows.append(
            "<tr><td>{ssid}</td><td>{bssid}</td><td>{vendor}</td>"
            "<td class='{cls}'>{sig}%</td><td>{rssi}</td><td>{ch}</td>"
            "<td>{band}</td><td>{auth}</td></tr>".format(
                ssid=html.escape(str(n.get("ssid", "?"))),
                bssid=html.escape(str(n.get("bssid", "?"))),
                vendor=html.escape(str(n.get("vendor", "?"))),
                cls=cls, sig=sig, rssi=n.get("rssi", "?"),
                ch=n.get("channel", "?"), band=html.escape(str(n.get("band", "?"))),
                auth=auth_cell))
    return _HTML_TMPL.format(meta=meta_str, rows="\n".join(rows))


def render(fmt: str, networks: list, meta: dict = None):
    """Devuelve (texto, content_type, filename_sugerido)."""
    fmt = (fmt or "json").lower()
    if fmt == "csv":
        return to_csv(networks), "text/csv; charset=utf-8", "radarwifi_scan.csv"
    if fmt == "html":
        return to_html(networks, meta), "text/html; charset=utf-8", "radarwifi_report.html"
    return to_json(networks, meta), "application/json; charset=utf-8", "radarwifi_scan.json"
