import os
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# Clave necesaria para que funcione el sistema de alertas (flash) sin dar error
app.secret_key = os.environ.get("SECRET_KEY", "textmind_secret_premium_key_123")

def analizar_texto_inteligente(texto):
    """Calcula métricas de texto y SEO para el informe premium."""
    if not texto or not texto.strip():
        return None
        
    total_palabras = len(texto.split())
    total_caracteres_con = len(texto)
    total_caracteres_sin = len(texto.replace(" ", ""))
    
    if total_palabras > 0:
        promedio_longitud = round(total_caracteres_sin / total_palabras, 1)
    else:
        promedio_longitud = 0
        
    tiempo_lectura = max(1, round((total_palabras / 200) * 60))
    tiempo_habla = max(1, round((total_palabras / 150) * 60))
    
    if total_palabras < 5:
        tono = "Corto o Directo 💬"
    elif promedio_longitud > 5.5:
        tono = "Formal / Académico 🎓"
    else:
        tono = "Neutral 😐"
        
    return {
        "total_palabras": total_palabras,
        "total_caracteres_con": total_caracteres_con,
        "total_caracteres_sin": total_caracteres_sin,
        "promedio_longitud": promedio_longitud,
        "tiempo_lectura": tiempo_lectura,
        "tiempo_habla": tiempo_habla,
        "tono": tono
    }

# RUTA 1: Vista Principal
@app.route("/", methods=["GET", "POST"])
def index():
    resultados = None
    texto_ingresado = ""
    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        resultados = analizar_texto_inteligente(texto_ingresado)
        
    return render_template("index.html", res=resultados, texto_previo=texto_ingresado)

# RUTA 2: Botón Premium
@app.route("/premium")
def premium():
    flash("¡Gracias por tu interés! El sistema de pagos (Stripe/PayPal) se activará en la Fase 2.", "premium")
    return redirect(url_for("index"))

# RUTA 3: Botón API Key
@app.route("/api-key")
def api_key():
    flash("Tu solicitud de API Key ha sido registrada. Recibirás un correo con tus credenciales pronto.", "api")
    return redirect(url_for("index"))

# RUTA 4: Botones de Documentación e Historial
@app.route("/info/<tipo>")
def info_paginas(tipo):
    if tipo == "docs":
        flash("Manual de TextMind v1.0: Pega texto en la caja central y pulsa Analizar para obtener métricas SEO en tiempo real.", "info")
    elif tipo == "historial":
        flash("Historial: Como usuario gratuito, solo almacenamos tu último análisis en la sesión local.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)
