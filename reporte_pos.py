"""Reporte POS Vendedoras — ventas del POS de Alegra separadas por vendedora, en PDF.

No lleva credenciales de Alegra: pide los datos a la función de Supabase
`pos-reporte-vendedoras`, que es la que guarda la llave de Alegra. Aquí solo va la
anon key pública de Supabase.
"""
import collections
import html
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from tkinter import messagebox, ttk

APP_VERSION = "1.0.0"
APP_NOMBRE = "Reporte POS Vendedoras"
REPO_RELEASES = "sistemasvilmora/reporte-pos-vendedoras"   # repo público solo con releases
SUPABASE_URL = "https://odurfgozvbyxlormjool.supabase.co"
SUPABASE_ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9kdXJmZ296dmJ5eGxvcm1qb29sIiwi"
                 "cm9sZSI6ImFub24iLCJpYXQiOjE3NzczNDI4OTYsImV4cCI6MjA5MjkxODg5Nn0.k1s68t8fBmk2ECWuRDGTXN8MXlRbdqrnb7y4f5SqDOg")
CARPETA = os.path.join(os.path.expanduser("~"), "Documents", "Reportes POS")

METODOS = {"cash": "Efectivo", "transfer": "Transferencia", "debit-card": "Débito", "credit-card": "Crédito"}
ORDEN = ["Efectivo", "Transferencia", "Débito", "Crédito", "Otro"]
SIN_VEND = "Sin vendedora asignada"


def pesos(v):
    return "$" + f"{round(v):,}".replace(",", ".")


# ---------------------------------------------------------------- datos
def traer(desde, hasta):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/functions/v1/pos-reporte-vendedoras",
        data=json.dumps({"desde": desde, "hasta": hasta}).encode(),
        headers={"Authorization": f"Bearer {SUPABASE_ANON}", "apikey": SUPABASE_ANON,
                 "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error")
        except Exception:
            msg = None
        raise RuntimeError(msg or f"Error {e.code} del servidor")
    if d.get("error"):
        raise RuntimeError(d["error"])
    return d


def armar(d):
    """Agrupa por vendedora; el método de pago sale de los pagos ligados a cada factura."""
    por_fac = collections.defaultdict(list)
    base = 0
    for p in d["pagos"]:
        if p.get("nota") == "Apertura de turno":
            base += p["monto"]
        for f in p["facturas"]:
            por_fac[f["id"]].append((METODOS.get(p["metodo"], "Otro"), f["monto"]))
    grupos = collections.OrderedDict()
    for f in sorted(d["facturas"], key=lambda x: x["fecha_hora"]):
        f["pagos"] = por_fac.get(f["id"], [])
        grupos.setdefault(f["vendedora"] or SIN_VEND, []).append(f)
    orden = sorted(grupos, key=lambda v: (v == SIN_VEND, v))
    return [(v, grupos[v]) for v in orden], base


def resumen(facturas):
    r = collections.Counter()
    for f in facturas:
        for m, monto in f["pagos"]:
            r[m] += monto
    total = sum(f["total"] for f in facturas)
    cobrado = sum(r.values())
    return total, cobrado, r


# ---------------------------------------------------------------- PDF
def generar_pdf(d, contado, ruta):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    azul = colors.HexColor("#2f5d8a")
    gris = colors.HexColor("#5b6475")
    st = {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=19),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=azul, spaceBefore=10),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=8.5, textColor=gris, leading=11),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=8.5, leading=11),
        "prod": ParagraphStyle("prod", fontName="Helvetica", fontSize=7.5, leading=9.5),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=8.5, leading=11.5, leftIndent=8, bulletIndent=0),
    }
    grupos, base = armar(d)
    todas = [f for _, L in grupos for f in L]
    rango = d["desde"] if d["desde"] == d["hasta"] else f"{d['desde']} a {d['hasta']}"
    el = [Paragraph("Ventas por vendedora · POS Alegra", st["h1"]),
          Paragraph(f"{rango} · {len(todas)} ventas · generado {dt.datetime.now():%Y-%m-%d %H:%M} · {APP_NOMBRE} v{APP_VERSION}", st["sub"]),
          Spacer(1, 6)]
    if not todas:
        el.append(Paragraph("No hay ventas de POS en esas fechas.", st["p"]))
        SimpleDocTemplate(ruta, pagesize=letter).build(el)
        return

    filas = [["Vendedora", "Ventas"] + ORDEN[:4] + ["Total cobrado"]]
    tot = collections.Counter()
    hay_otro = False
    for v, L in grupos:
        _, cobrado, r = resumen(L)
        tot.update(r)
        hay_otro |= bool(r.get("Otro"))
        filas.append([Paragraph(html.escape(v), st["p"]), str(len(L))] + [pesos(r[k]) for k in ORDEN[:4]] + [pesos(cobrado)])
    filas.append(["TOTAL", str(len(todas))] + [pesos(tot[k]) for k in ORDEN[:4]] + [pesos(sum(tot.values()))])
    t = Table(filas, colWidths=[52 * mm, 14 * mm, 24 * mm, 26 * mm, 22 * mm, 22 * mm, 28 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), azul), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8.5),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eef3f9")), ("LINEABOVE", (0, -1), (-1, -1), 1, azul),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.HexColor("#e2e6ee")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    el.append(t)

    # Cuadre de efectivo y cosas para revisar
    notas = []
    efectivo = tot["Efectivo"]
    if base or contado is not None:
        esperado = base + efectivo
        txt = f"Efectivo esperado en caja: base {pesos(base)} + ventas en efectivo {pesos(efectivo)} = <b>{pesos(esperado)}</b>."
        if contado is not None:
            dif = contado - esperado
            estado = "cuadra" if abs(dif) < 1 else ("sobran" if dif > 0 else "faltan")
            txt += f" Contado: {pesos(contado)} → <b>{estado}{'' if estado == 'cuadra' else ' ' + pesos(abs(dif))}</b>."
        notas.append(txt)
    for f in todas:
        if f["saldo"] > 1:
            notas.append(f"<b>{f['numero']}</b> ({html.escape(f['vendedora'] or SIN_VEND)}, {f['fecha_hora'][11:16]}): total {pesos(f['total'])}, "
                         f"cobrado {pesos(f['pagado'])} → <b>saldo de {pesos(f['saldo'])} sin pagar</b>.")
    sv = dict(grupos).get(SIN_VEND)
    if sv:
        notas.append(f"<b>{len(sv)} ventas sin vendedora</b> ({', '.join(f['numero'] for f in sv)}) por {pesos(sum(f['total'] for f in sv))}: "
                     "en el POS no se escogió vendedora.")
    if hay_otro:
        notas.append("Hay pagos con un método distinto a efectivo/transferencia/débito/crédito; cuentan en el total pero no en esas columnas.")
    if notas:
        el.append(Paragraph("Para revisar", st["h2"]))
        el += [Paragraph(n, st["li"], bulletText="•") for n in notas]

    # Detalle por vendedora
    for v, L in grupos:
        total, cobrado, _ = resumen(L)
        el.append(Paragraph(html.escape(v), st["h2"]))
        el.append(Paragraph(f"{len(L)} ventas · facturado {pesos(total)} · cobrado {pesos(cobrado)}", st["sub"]))
        el.append(Spacer(1, 3))
        filas = [["Fecha", "Documento", "Cliente / productos", "Pago", "Total", "Cobrado"]]
        resaltar = []
        for f in L:
            prods = "<br/>".join(
                f"{i['cantidad']:g} × {html.escape(i['nombre'])}" + (f" <i>(-{i['descuento_pct']:g}%)</i>" if i["descuento_pct"] else "")
                for i in f["items"])
            fecha = f["fecha_hora"][5:16].replace("-", "/") if d["desde"] != d["hasta"] else f["fecha_hora"][11:16]
            filas.append([fecha, f["numero"], Paragraph(f"<b>{html.escape(f['cliente'])}</b><br/>{prods}", st["prod"]),
                          ", ".join(sorted({m for m, _ in f["pagos"]})) or "—", pesos(f["total"]), pesos(f["pagado"])])
            if f["saldo"] > 1:
                resaltar.append(len(filas) - 1)
        t = Table(filas, colWidths=[18 * mm, 20 * mm, 82 * mm, 24 * mm, 22 * mm, 22 * mm], repeatRows=1)
        estilo = [
            ("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("BACKGROUND", (0, 0), (-1, 0), azul), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e2e6ee")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
        estilo += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fff4e0")) for i in resaltar]
        t.setStyle(TableStyle(estilo))
        el.append(t)

    SimpleDocTemplate(ruta, pagesize=letter, leftMargin=12 * mm, rightMargin=12 * mm,
                      topMargin=12 * mm, bottomMargin=12 * mm, title="Ventas por vendedora",
                      author=APP_NOMBRE).build(el)


# ---------------------------------------------------------------- actualización
def version_tupla(s):
    try:
        return tuple(int(x) for x in s.lstrip("v").split("."))
    except ValueError:
        return (0,)


def ultima_version():
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO_RELEASES}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json", "User-Agent": "reporte-pos"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())["tag_name"]


def actualizar():
    """Corre de nuevo el instalador (baja el .exe nuevo, cierra este y lo reemplaza)."""
    cmd = (f"Start-Sleep 2; irm https://github.com/{REPO_RELEASES}/releases/latest/download/instalar.ps1 | iex")
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    os._exit(0)


# ---------------------------------------------------------------- ventana
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NOMBRE} v{APP_VERSION}")
        self.resizable(False, False)
        f = ttk.Frame(self, padding=16)
        f.grid()
        hoy = dt.date.today().isoformat()
        ttk.Label(f, text="Ventas del POS por vendedora", font=("Segoe UI", 13, "bold")).grid(columnspan=2, sticky="w")
        ttk.Label(f, text="Fechas en formato AAAA-MM-DD. Para un turno, pon el mismo día en las dos.",
                  foreground="#5b6475").grid(columnspan=2, sticky="w", pady=(0, 10))
        self.desde = tk.StringVar(value=hoy)
        self.hasta = tk.StringVar(value=hoy)
        self.contado = tk.StringVar()
        for i, (txt, var) in enumerate([("Desde", self.desde), ("Hasta", self.hasta),
                                        ("Efectivo contado (opcional)", self.contado)], start=2):
            ttk.Label(f, text=txt).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(f, textvariable=var, width=16).grid(row=i, column=1, sticky="w", pady=3)
        b = ttk.Frame(f)
        b.grid(row=5, columnspan=2, sticky="w", pady=(12, 0))
        self.boton = ttk.Button(b, text="Generar PDF", command=self.generar)
        self.boton.pack(side="left")
        ttk.Button(b, text="Abrir carpeta", command=lambda: os.startfile(self._carpeta())).pack(side="left", padx=6)
        self.btn_act = ttk.Button(b, text="Actualizar", command=self.confirmar_actualizar)
        self.estado = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.estado, foreground="#2f5d8a", wraplength=360).grid(row=6, columnspan=2, sticky="w", pady=(10, 0))
        self.nueva = None
        threading.Thread(target=self.revisar_version, daemon=True).start()

    def _carpeta(self):
        os.makedirs(CARPETA, exist_ok=True)
        return CARPETA

    def revisar_version(self):
        try:
            tag = ultima_version()
            if version_tupla(tag) > version_tupla(APP_VERSION):
                self.nueva = tag
                self.after(0, lambda: (self.btn_act.pack(side="left"), self.estado.set(f"Hay una versión nueva ({tag}).")))
        except Exception:
            pass

    def confirmar_actualizar(self):
        if messagebox.askyesno(APP_NOMBRE, f"¿Instalar la versión {self.nueva}? El programa se cierra y se vuelve a abrir."):
            actualizar()

    def generar(self):
        desde, hasta = self.desde.get().strip(), self.hasta.get().strip()
        try:
            a, b = dt.date.fromisoformat(desde), dt.date.fromisoformat(hasta)
            assert a <= b and (b - a).days <= 31
        except Exception:
            messagebox.showerror(APP_NOMBRE, "Revisa las fechas: formato AAAA-MM-DD, 'desde' antes de 'hasta' y máximo 31 días.")
            return
        c = self.contado.get().strip().replace("$", "").replace(".", "").replace(",", "")
        contado = None
        if c:
            if not c.isdigit():
                messagebox.showerror(APP_NOMBRE, "El efectivo contado debe ser un número (ej. 986200).")
                return
            contado = int(c)
        self.boton.state(["disabled"])
        self.estado.set("Consultando Alegra… (puede tardar hasta un minuto)")
        threading.Thread(target=self._trabajo, args=(desde, hasta, contado), daemon=True).start()

    def _trabajo(self, desde, hasta, contado):
        try:
            d = traer(desde, hasta)
            nombre = f"ventas_vendedoras_{desde}" + ("" if desde == hasta else f"_a_{hasta}") + f"_{dt.datetime.now():%H%M%S}.pdf"
            ruta = os.path.join(self._carpeta(), nombre)
            generar_pdf(d, contado, ruta)
            self.after(0, lambda: self.estado.set(f"Listo: {len(d['facturas'])} ventas. PDF en {ruta}"))
            os.startfile(ruta)
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: (self.estado.set(""), messagebox.showerror(APP_NOMBRE, f"No se pudo generar el reporte:\n{msg}")))
        finally:
            self.after(0, lambda: self.boton.state(["!disabled"]))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--cli":      # para pruebas: reporte_pos.py --cli DESDE [HASTA] [CONTADO]
        dd = sys.argv[2]
        hh = sys.argv[3] if len(sys.argv) > 3 else dd
        cc = int(sys.argv[4]) if len(sys.argv) > 4 else None
        out = os.path.abspath(f"prueba_{dd}.pdf")
        generar_pdf(traer(dd, hh), cc, out)
        print(out)
    else:
        App().mainloop()
