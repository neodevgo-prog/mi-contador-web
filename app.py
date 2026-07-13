from flask import Flask, render_template, request

app = Flask(__name__)

def analizar_texto(texto):
    if not texto.strip():
        return None
    palabras = texto.split()
    
    # Análisis simple de tono
    texto_minusculas = texto.lower()
    if "bueno" in texto_minusculas or "excelente" in texto_minusculas or "feliz" in texto_minusculas:
        tono = "Positivo 😊"
    elif "malo" in texto_minusculas or "triste" in texto_minusculas or "error" in texto_minusculas:
        tono = "Negativo 😔"
    else:
        tono = "Neutral 😐"

    return {
        "total_palabras": len(palabras),
        "caracteres_con_espacio": len(texto),
        "tono": tono
    }

@app.route("/", methods=["GET", "POST"])
def home():
    texto_ingresado = ""
    resultados = None
    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        resultados = analizar_texto(texto_ingresado)
    return render_template("index.html", texto=texto_ingresado, res=resultados)

if __name__ == "__main__":
    app.run(debug=True)
