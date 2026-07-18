import os
import re
import io
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, Response
)

app = Flask(__name__)
# Clave de seguridad estricta para evitar errores 500 con las alertas flash en Render
app.secret_key = os.environ.get("SECRET_KEY", "textmind_secure_production_key_2026_seo")

# --- Sesiones en el servidor (no en cookie) ---
# Por defecto Flask guarda la sesión entera en una cookie del navegador, con un
# límite de ~4KB. Para guardar un historial de varios análisis y el estado
# Premium de forma fiable, usamos Flask-Session con almacenamiento en disco.
try:
    from flask_session import Session
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session_data")
    app.config["SESSION_PERMANENT"] = False
    Session(app)
except Exception as e:
    print(f"[TextMind] Aviso: Flask-Session no disponible ({e}). "
          f"Usando sesiones de cookie por defecto (con límite de tamaño).")

# --- Dominio público de la app (para SEO, sitemap y redirecciones de Stripe) ---
DOMINIO = os.environ.get("DOMINIO", "https://mi-contador-web-g2eh.onrender.com")

# --- Configuración de Stripe (pagos reales del Plan Premium) ---
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
stripe_disponible = False
try:
    import stripe
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
        stripe_disponible = True
except Exception as e:
    print(f"[TextMind] Aviso: la librería stripe no está disponible ({e}).")

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


def guardar_en_historial(texto, resultados):
    """Guarda un resumen del análisis en el historial de la sesión (últimos 5)."""
    historial = session.get("historial", [])
    texto_limpio = texto.strip()
    resumen = texto_limpio[:80] + ("…" if len(texto_limpio) > 80 else "")
    historial.insert(0, {
        "resumen": resumen,
        "palabras": resultados["total_palabras"],
        "tono": resultados["tono"],
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })
    session["historial"] = historial[:5]


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
        else:
            # Guardamos el texto (recortado) para poder exportarlo a PDF luego
            session["ultimo_texto"] = texto_ingresado[:5000]
            guardar_en_historial(texto_ingresado, resultados)

            if accion == "morfologia":
                if nlp is None:
                    flash("El análisis morfológico no está disponible ahora mismo. Inténtalo más tarde.", "info")
                else:
                    morfologia = analizar_morfologia(texto_ingresado)

    return render_template(
        "index.html",
        res=resultados,
        texto_previo=texto_ingresado,
        morfologia=morfologia,
        es_premium=session.get("premium", False),
    )


# RUTA HISTORIAL (real, ya no es un mensaje falso)
@app.route("/historial")
def historial():
    return render_template("historial.html", historial=session.get("historial", []))


# RUTA PREMIUM: inicia el pago real con Stripe si está configurado
@app.route("/premium", methods=["GET", "POST"])
def premium():
    if request.method == "GET":
        # Si alguien llega aquí directamente (sin pasar por el formulario con la
        # casilla de aceptación), lo mandamos de vuelta al inicio.
        flash("Para activar el Plan Premium, marca la casilla de aceptación y pulsa el botón desde la página principal.", "info")
        return redirect(url_for("index"))

    if not request.form.get("acepta_renuncia"):
        flash("Debes aceptar la renuncia al derecho de desistimiento de 14 días para continuar con el pago del contenido digital.", "premium")
        return redirect(url_for("index"))

    if session.get("premium"):
        flash("Ya tienes el Plan Premium activo. ¡Gracias por tu apoyo! 🎉", "premium")
        return redirect(url_for("index"))

    if stripe_disponible and STRIPE_PRICE_ID:
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
                mode="payment",
                success_url=DOMINIO + "/premium/exito?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=DOMINIO + "/premium/cancelado",
            )
            # Registro mínimo del consentimiento para tener constancia (queda en los
            # logs de Render). Si más adelante añades base de datos, aquí es donde
            # guardarías esto de forma permanente junto con el ID de la sesión.
            print(f"[TextMind] Consentimiento de renuncia aceptado — IP: {request.remote_addr} — "
                  f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} — sesión: {checkout_session.id}")
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            print(f"[TextMind] Error creando la sesión de Stripe: {e}")
            flash("No se pudo iniciar el pago ahora mismo. Inténtalo más tarde.", "premium")
            return redirect(url_for("index"))

    # Fallback si aún no se han configurado las claves de Stripe
    flash("El Plan Premium estará disponible muy pronto. Estamos terminando de configurar los pagos.", "premium")
    return redirect(url_for("index"))


@app.route("/premium/exito")
def premium_exito():
    session_id = request.args.get("session_id")
    if stripe_disponible and session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == "paid":
                session["premium"] = True
                flash("¡Pago recibido! Ya tienes acceso Premium: exportación a PDF y más funciones.", "premium")
            else:
                flash("Todavía no hemos podido confirmar el pago. Si el problema persiste, contacta con soporte.", "info")
        except Exception as e:
            print(f"[TextMind] Error verificando el pago de Stripe: {e}")
            flash("No hemos podido verificar el pago. Si se realizó el cargo, contacta con soporte.", "info")
    return redirect(url_for("index"))


@app.route("/premium/cancelado")
def premium_cancelado():
    flash("Has cancelado el proceso de pago. Puedes intentarlo cuando quieras.", "info")
    return redirect(url_for("index"))


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Endpoint para eventos de Stripe (útil sobre todo si en el futuro añades
    suscripciones recurrentes en vez de pago único). Requiere configurar
    STRIPE_WEBHOOK_SECRET con el valor que te da el panel de Stripe."""
    if not stripe_disponible:
        return "", 200

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        if webhook_secret:
            stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        # Aquí podrías registrar el evento en una base de datos si más adelante
        # añades cuentas de usuario persistentes.
    except Exception as e:
        print(f"[TextMind] Webhook de Stripe inválido: {e}")
        return "", 400

    return "", 200


# RUTA EXPORTAR PDF (función Premium real)
@app.route("/exportar-pdf")
def exportar_pdf():
    if not session.get("premium"):
        flash("Exportar a PDF es una función Premium. Actívala para descargar tus análisis.", "premium")
        return redirect(url_for("index"))

    texto = session.get("ultimo_texto", "")
    resultados = analizar_texto_inteligente(texto)
    if not resultados:
        flash("Primero analiza un texto para poder exportarlo.", "info")
        return redirect(url_for("index"))

    try:
        from fpdf import FPDF
    except Exception as e:
        print(f"[TextMind] fpdf2 no disponible: {e}")
        flash("La exportación a PDF no está disponible ahora mismo.", "info")
        return redirect(url_for("index"))

    def limpiar(txt):
        # Las fuentes base de fpdf2 solo soportan latin-1 (sin emojis)
        return txt.encode("latin-1", errors="ignore").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Informe TextMind", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, datetime.now().strftime("Generado el %d/%m/%Y a las %H:%M"), ln=True)
    pdf.ln(6)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Métricas", ln=True)
    pdf.set_font("Helvetica", "", 11)

    filas = [
        ("Tono del texto", limpiar(resultados["tono"])),
        ("Palabras", str(resultados["total_palabras"])),
        ("Palabras únicas", str(resultados["palabras_unicas"])),
        ("Diversidad léxica", f"{resultados['diversidad_lexica']}%"),
        ("Caracteres (con espacios)", str(resultados["total_caracteres_con"])),
        ("Caracteres (sin espacios)", str(resultados["total_caracteres_sin"])),
        ("Frases", str(resultados["total_frases"])),
        ("Párrafos", str(resultados["total_parrafos"])),
        ("Tiempo de lectura", f"{resultados['tiempo_lectura']} seg"),
        ("Tiempo hablado", f"{resultados['tiempo_habla']} seg"),
        ("Palabra clave principal", f"{limpiar(resultados['palabra_clave'])} (x{resultados['palabra_clave_veces']})"),
    ]
    for etiqueta, valor in filas:
        pdf.cell(70, 8, etiqueta, border=0)
        pdf.cell(0, 8, valor, border=0, ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Texto analizado", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, limpiar(texto[:3000]))

    pdf_bytes = bytes(pdf.output())
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="textmind_informe.pdf",
        mimetype="application/pdf",
    )


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
    elif tipo == "densidad":
        flash("Análisis de Densidad: Función en desarrollo para la siguiente actualización.", "info")
    return redirect(url_for("index"))


# RUTAS LEGALES (necesarias si usas Analytics/anuncios en la UE)
@app.route("/privacidad")
def privacidad():
    return render_template("privacidad.html")


@app.route("/cookies")
def cookies():
    return render_template("cookies.html")


# --- SEO técnico ---
@app.route("/robots.txt")
def robots_txt():
    contenido = f"""User-agent: *
Allow: /

Sitemap: {DOMINIO}/sitemap.xml
"""
    return Response(contenido, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    paginas = ["/", "/privacidad", "/cookies"]
    urls = "".join(
        f"<url><loc>{DOMINIO}{p}</loc></url>" for p in paginas
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>' \
          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
    return Response(xml, mimetype="application/xml")


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=puerto)