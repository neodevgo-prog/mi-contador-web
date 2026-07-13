import os
from flask import Flask, render_template, request

app = Flask(__name__)

def analizar_texto_inteligente(texto):
    """Calcula métricas de texto y SEO para el informe premium."""
    if not texto or not texto.strip():
        return None
        
    # Cálculos básicos de caracteres y palabras
    total_palabras = len(texto.split())
    total_caracteres_con = len(texto)
    total_caracteres_sin = len(texto.replace(" ", ""))
    
    # Cálculo aproximado de la longitud promedio de palabra
    if total_palabras > 0:
        promedio_longitud = round(total_caracteres_sin / total_palabras, 1)
    else:
        promedio_longitud = 0
        
    # Estimación de tiempos (Promedios: lectura 200 ppm / habla 150 ppm)
    tiempo_lectura = max(1, round((total_palabras / 200) * 60))
    tiempo_habla = max(1, round((total_palabras / 150) * 60))
    
    # Análisis básico de tono (Simulado por longitud de frases o palabras clave)
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

@app.route("/", methods=["GET", "POST"])
def index():
    resultados = None
    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        resultados = analizar_texto_inteligente(texto_ingresado)
        
    # Pasamos de forma segura la variable 'res' que el HTML espera leer
    return render_template("index.html", res=resultados)

if __name__ == "__main__":
    # Configuración de puerto dinámica obligatoria para Render
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)
