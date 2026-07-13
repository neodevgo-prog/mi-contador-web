from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

# Palabras comunes en español que no aportan valor al análisis SEO
STOPWORDS = {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "para", "por", "con", "y", "o", "u", "que", "es", "son", "se", "un", "su", "sus", "al", "lo"}

# Listas básicas para detectar el tono (análisis de sentimiento simple)
PALABRAS_POSITIVAS = {"bueno", "excelente", "gran", "mejor", "perfecto", "maravilloso", "feliz", "alegre", "éxito", "positivo", "fácil", "gracias", "amor", "útil"}
PALABRAS_NEGATIVAS = {"malo", "peor", "error", "fallo", "difícil", "triste", "problema", "negativo", "horrible", "pésimo", "odio", "nunca", "jamás", "perder"}

def analizar_texto(texto):
    if not texto.strip():
        return None

    palabras_lista = texto.split()
    total_palabras = len(palabras_lista)
    if total_palabras == 0:
        return None

    # 1. Conteos Básicos
    caracteres_con_espacio = len(texto)
    caracteres_sin_espacio = len(texto.replace(" ", "").replace("\n", "").replace("\r", ""))
    oraciones = len([s for s in re.split(r'[.!?]+', texto) if s.strip()])
    parrafos = len([p for p in texto.split('\n') if p.strip()])

    # 2. Tiempos Estimados
    segundos_lectura = int((total_palabras / 200) * 60)
    segundos_habla = int((total_palabras / 130) * 60)

    # 3. Densidad de Palabras Clave
    texto_limpio = re.sub(r'[^\w\s]', '', texto.lower())
    palabras_limpias = [p for p in texto_limpio.split() if p not in STOPWORDS and len(p) > 2]
    contador_palabras = Counter(palabras_limpias)
    top_3 = contador_palabras.most_common(3)
    
    palabras_clave = []
    for palabra, freq in top_3:
        porcentaje = (freq / total_palabras) * 100
        palabras_clave.append({"palabra": palabra, "frecuencia": freq, "densidad": round(porcentaje, 1)})

    # 4. Longitud promedio
    total_letras = sum(len(p) for p in palabras_lista)
    promedio_longitud = round(total_letras / total_palabras, 1)

    # 5. Detector de Tono / Sentimiento
    palabras_minusculas = texto_limpio.split()
    positivas = sum(1 for p in palabras_minusculas if p in PALABRAS_POSITIVAS)
    negativas = sum(1 for p in palabras_minusculas if p in PALABRAS_NEGATIVAS)
    
    if positivas > negativas:
        tono = "Positivo 😊"
    elif negativas > positivas:
        tono = "Negativo 😔"
    else:
        tono = "Neutral 😐"

    # 6. Contador de Sílabas Estimado
    total_silabas = 0
    for pal in palabras_minusculas:
        silabas_palabra = len(re.findall(r'[aeiouáéíóúü]+', pal))
        total_silabas += silabas_palabra if silabas_palabra > 0 else 1

    return {
        "caracteres_con_espacio": caracteres_con_espacio,
        "caracteres_sin_espacio": caracteres_sin_espacio,
        "total_palabras": total_palabras,
        "oraciones": oraciones if oraciones > 0 else 1,
        "parrafos": parrafos if parrafos > 0 else 1,
        "segundos_lectura": segundos_lectura,
        "segundos_habla": segundos_habla,
        "palabras_clave": palabras_clave,
        "promedio_longitud": promedio_longitud,
        "tono": tono,
        "total_silabas": total_silabas
    }

@app.route("/", methods=["GET", "POST"])
def home():
    texto_ingresado = ""
    resultados = None

    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        accion = request.form.get("accion", "")

        # Lógica del Limpiador de Texto rápido
        if accion == "mayusculas":
            texto_ingresado = texto_ingresado.upper()
        elif accion == "minusculas":
            texto_ingresado = texto_ingresado.lower()
        elif accion == "limpiar_espacios":
            texto_ingresado = " ".join(texto_ingresado.split())

        resultados = analizar_texto(texto_ingresado)

    return render_template("index.html", texto=texto_ingresado, res=resultados)

if __name__ == "__main__":
    app.run(debug=True)
