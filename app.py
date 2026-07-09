from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def contador():
    num_palabras = 0
    num_caracteres = 0
    texto_ingresado = ""
    
    # Si el usuario hace clic en el botón de la web, procesamos el texto
    if request.method == "POST":
        texto_ingresado = request.form.get("texto", "")
        num_palabras = len(texto_ingresado.split())
        num_caracteres = len(texto_ingresado)
        
    return render_template("index.html", palabras=num_palabras, caracteres=num_caracteres, texto=texto_ingresado)

if __name__ == "__main__":
    app.run(debug=True)
