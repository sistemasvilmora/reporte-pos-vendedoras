# Reporte POS Vendedoras

Programa de Windows que saca las ventas del POS de Alegra (Minimarket) **separadas por vendedora** y las deja en un PDF: resumen por forma de pago, cuadre de efectivo (base + efectivo vs. contado), facturas con saldo pendiente, ventas sin vendedora y el detalle de cada venta con sus productos.

## Instalar (un solo comando)

Abrir **PowerShell** y pegar:

```powershell
irm https://github.com/sistemasvilmora/reporte-pos-vendedoras/releases/latest/download/instalar.ps1 | iex
```

Queda en `%LOCALAPPDATA%\ReportePOSVendedoras`, con acceso directo en el Escritorio y en el menú Inicio. El mismo comando sirve para actualizar. El programa también avisa solo cuando hay versión nueva (botón **Actualizar**).

## Uso

1. Poner las fechas (para un turno, el mismo día en *Desde* y *Hasta*).
2. Opcional: el efectivo contado en caja, para que el PDF diga si sobra o falta.
3. **Generar PDF**. Se guarda en `Documentos\Reportes POS` y se abre solo.

## Cómo funciona (seguridad)

- El programa **no lleva la llave de Alegra**. Llama a la función de Supabase `pos-reporte-vendedoras` (proyecto `odurfgozvbyxlormjool`) con la anon key pública de Supabase; la función es la que tiene `ALEGRA_EMAIL` / `ALEGRA_API_KEY` como secretos y solo lee.
- La función trae las facturas con `originApp = POS` del rango y los pagos del rango (forma de pago por factura y la "Apertura de turno" = base de caja). Máximo 31 días.
- La vendedora es el campo *Vendedor* de la factura en Alegra. Si en el POS no se escoge vendedora, la venta sale en "Sin vendedora asignada".

## Archivos

| Archivo | Qué es |
|---|---|
| `reporte_pos.py` | Todo el programa (Tkinter + reportlab). `python reporte_pos.py --cli 2026-11-21` genera un PDF de prueba sin ventana. |
| `instalar.ps1` | Instalador/actualizador (se publica como archivo del release). |
| `publicar.ps1` | Sube el tag `vX.Y.Z`; GitHub Actions compila y publica. |
| `.github/workflows/release.yml` | Compila el `.exe` en Windows y crea el release con `instalar.ps1`. |

## Publicar una versión

1. Subir `APP_VERSION` en `reporte_pos.py` y hacer commit.
2. `.\publicar.ps1` (o `git tag vX.Y.Z && git push origin vX.Y.Z`). En ~3 min el release está listo.
