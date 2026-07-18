import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# Clave de seguridad estricta para evitar errores 500 con las alertas flash en Render
app.secret_key = os.environ.get("SECRET_KEY", "textmind_secure_production_key_2026_seo")

# --- Carga del modelo de spaCy para el análisis morfológico ---
# Se carga UNA sola vez al arrancar el servidor (no en cada petición), porque
# cargar el modelo tarda unos segundos y consume memoria.
nlp = None
try:
    import spacy
    nlp = spacy.load("es_core_news_sm")
except Exception as e:
    print(f"[TextMind] Aviso: no se pudo cargar el modelo de spaCy ({e}). "
          f"El análisis morfológico quedará desactivado.")

# Traducciones de las categorías gramaticales (POS) de spaCy al español
ETIQUETAS_POS = {
    "NOUN": "Sustantivo", "PROPN": "Nombre Propio", "VERB": "Verbo", "AUX": "Verbo Auxiliar",
    "ADJ": "Adjetivo", "ADV": "Adverbio", "PRON": "Pronombre", "DET": "Determinante",
    "ADP": "Preposición", "CCONJ": "Conjunción", "SCONJ": "Conjunción", "NUM": "Número",
    "INTJ": "Interjección", "SYM": "Símbolo", "X": "Otro",
}

# Traducciones de los rasgos morfológicos y sus valores, organizadas por rasgo
# para evitar ambigüedades (p. ej. "Imp" significa "Imperfecto" en Tense pero
# "Imperativo" en Mood).
CLAVES_RASGOS = {
    "Gender": "Género", "Number": "Número", "Tense": "Tiempo", "Mood": "Modo",
    "Person": "Persona", "VerbForm": "Forma Verbal", "PronType": "Tipo",
    "Case": "Caso", "Degree": "Grado", "NumType": "Tipo Numeral",
    "Definite": "Definido", "Polarity": "Polaridad",
}

VALORES_RASGOS = {
    "Gender": {"Masc": "Masculino", "Fem": "Femenino"},
    "Number": {"Sing": "Singular", "Plur": "Plural"},
    "Tense": {"Pres": "Presente", "Past": "Pasado", "Fut": "Futuro", "Imp": "Imperfecto", "Pqp": "Pluscuamperfecto"},
    "Mood": {"Ind": "Indicativo", "Sub": "Subjuntivo", "Imp": "Imperativo", "Cnd": "Condicional"},
    "Person": {"1": "1ª", "2": "2ª", "3": "3ª"},
    "VerbForm": {"Fin": "Conjugado", "Inf": "Infinitivo", "Ger": "Gerundio", "Part": "Participio"},
    "PronType": {"Prs": "Personal", "Dem": "Demostrativo", "Ind": "Indefinido", "Int": "Interrogativo",
                 "Rel": "Relativo", "Art": "Artículo"},
    "Case": {"Nom": "Nominativo", "Acc": "Acusativo", "Dat": "Dativo"},
    "Degree": {"Cmp": "Comparativo", "Sup": "Superlativo", "Pos": "Positivo"},
    "Definite": {"Def": "Definido", "Ind": "Indefinido"},
}


def traducir_rasgos(rasgos):
    """Convierte los rasgos morfológicos de spaCy (en inglés/código UD) a español legible."""
    resultado = {}
    for clave, valor in rasgos.items():
        clave_es = CLAVES_RASGOS.get(clave, clave)
        valor_es = VALORES_RASGOS.get(clave, {}).get(valor, valor)
        resultado[clave_es] = valor_es
    return resultado


def analizar_morfologia(texto):
    """Analiza cada palabra del texto: categoría gramatical, lema y rasgos morfológicos."""
    if nlp is None or not texto or not texto.strip():
        return None

    doc = nlp(texto)

    palabras_analizadas = []
    for token in doc:
        if token.pos_ in ("SPACE", "PUNCT"):
            continue
        rasgos = traducir_rasgos(token.morph.to_dict())
        palabras_analizadas.append({
            "palabra": token.text,
            "lema": token.lemma_,
            "categoria": ETIQUETAS_POS.get(token.pos_, token.pos_),
            "rasgos": rasgos,
        })

    oraciones = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return {
        "palabras": palabras_analizadas,
        "num_oraciones": len(oraciones),
        "oraciones": oraciones,
    }


def analizar_texto_inteligente(texto):
    """Calcula métricas de texto y SEO para el informe premium."""
    if not texto or not texto.strip():
        return None

    palabras = texto.split()
    total_palabras = len(palabras)
    total_caracteres_con = len(texto)
    total_caracteres_sin = len(texto.replace(" ", ""))

    promedio_longitud = round(total_caracteres_sin / total_palabras, 1) if total_palabras > 0 else 0

    tiempo_lectura = max(1, round((total_palabras / 200) * 60))
    tiempo_habla = max(1, round((total_palabras / 150) * 60))

    # --- Métricas nuevas ---
    # Frases: se dividen por . ! ? seguidos de espacio o fin de texto
    frases = [f for f in re.split(r'[.!?]+', texto) if f.strip()]
    total_frases = len(frases)

    # Párrafos: separados por líneas en blanco
    parrafos = [p for p in texto.split("\n") if p.strip()]
    total_parrafos = max(1, len(parrafos))

    # Palabras únicas (sin distinguir mayúsculas/minúsculas, sin signos de puntuación)
    palabras_normalizadas = [re.sub(r'[^\wáéíóúñü]', '', w.lower()) for w in palabras]
    palabras_normalizadas = [w for w in palabras_normalizadas if w]
    palabras_unicas = len(set(palabras_normalizadas))
    diversidad_lexica = round((palabras_unicas / total_palabras) * 100, 1) if total_palabras > 0 else 0

    # Palabra clave más repetida (ignorando palabras muy cortas/vacías comunes)
    stopwords = {"de", "la", "el", "en", "y", "a", "que", "los", "las", "un", "una",
                 "con", "por", "para", "se", "es", "del", "al", "su", "lo", "como"}
    conteo = {}
    for w in palabras_normalizadas:
        if w not in stopwords and len(w) > 2:
            conteo[w] = conteo.get(w, 0) + 1
    palabra_clave = max(conteo, key=conteo.get) if conteo else "--"
    palabra_clave_veces = conteo.get(palabra_clave, 0)

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
        "tono": tono,
        "total_frases": total_frases,
        "total_parrafos": total_parrafos,
        "palabras_unicas": palabras_unicas,
        "diversidad_lexica": diversidad_lexica,
        "palabra_clave": palabra_clave,
        "palabra_clave_veces": palabra_clave_veces,
    }


# RUTA MAIN
@app.route("/", methods=["GET", "POST"])
def index():
    resultados = None
    morfologia = None
    texto_ingresado = ""

    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        accion = request.form.get("accion", "basico")
        resultados = analizar_texto_inteligente(texto_ingresado)

        if resultados is None:
            flash("Escribe algo de texto antes de analizar.", "info")
        elif accion == "morfologia":
            if nlp is None:
                flash("El análisis morfológico no está disponible ahora mismo. Inténtalo más tarde.", "info")
            else:
                morfologia = analizar_morfologia(texto_ingresado)

    return render_template("index.html", res=resultados, texto_previo=texto_ingresado, morfologia=morfologia)


# RUTA PREMIUM
@app.route("/premium")
def premium():
    flash("¡Gracias por tu interés! El sistema de pagos (Stripe/PayPal) se activará en la Fase 2.", "premium")
    return redirect(url_for("index"))


# RUTA API KEY
@app.route("/api-key")
def api_key():
    flash("Tu solicitud de API Key ha sido registrada. Recibirás un correo con tus credenciales pronto.", "api")
    return redirect(url_for("index"))


# RUTA HERRAMIENTAS EXTRAS
@app.route("/info/<tipo>")
def info_paginas(tipo):
    if tipo == "docs":
        flash("Manual de TextMind v1.0: Pega texto en la caja central y pulsa Analizar para obtener métricas SEO en tiempo real.", "info")
    elif tipo == "historial":
        flash("Historial: Como usuario gratuito, solo almacenamos tu último análisis en la sesión local.", "info")
    elif tipo == "pdf":
        flash("Feature Premium: La generación de archivos PDF reales requiere la activación de una suscripción.", "premium")
    elif tipo == "densidad":
        flash("Análisis de Densidad: Función en desarrollo para la siguiente actualización.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)
