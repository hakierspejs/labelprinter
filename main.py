#!/usr/bin/env python3

import subprocess
import io
import random

import flask
import qrcode
from PIL import Image, ImageDraw, ImageFont


app = flask.Flask(__name__)


FONT = ImageFont.truetype(
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 42
)


def zbuduj_linie(opis, max_znakow_na_linie):
    ret = []
    aktualna_opis = ""
    slowa = opis.split(" ")
    for slowo in slowa:
        if aktualna_opis:
            aktualna_opis += " "
        if len(aktualna_opis) + len(slowo) > max_znakow_na_linie:
            ret.append(aktualna_opis)
            aktualna_opis = ""
        if aktualna_opis:
            aktualna_opis += " "
        aktualna_opis += slowo
    ret.append(aktualna_opis)
    return "\n".join(ret)


def img_jako_png(img):
    bio = io.BytesIO()
    img.save(bio, format="png")
    return bio.getvalue()


def generuj_png(opis, url):
    linie = zbuduj_linie(opis, 24)

    text_start_ypos = 450 if url else 10
    ysize = text_start_ypos + (50 * len(linie.split("\n")))

    img = Image.new("RGB", (500, ysize), color="white")
    draw = ImageDraw.Draw(img)

    if url:
        qr = qrcode.make(url, box_size=3)
        qr = qr.resize((500, 500), Image.ANTIALIAS)
        img.paste(qr, (0, -20))

    draw.text((10, text_start_ypos), linie, fill=(0, 0, 0), font=FONT)

    return img_jako_png(img)


def generuj_i_drukuj(opis, url, kopii):
    k = str(random.random())
    png_b = generuj_png(opis, url)
    path = "out/" + k + ".png"
    with open(path, "wb") as f:
        f.write(png_b)
    for i in range(kopii + 1):
        subprocess.check_call(
            """brother_ql  -m QL-800 -p /dev/usb/lp0 print -l 50 """ + path,
            shell=True,
        )
    return path


@app.route("/drukuj", methods=["POST"])
def drukuj():
    opis = flask.request.form["opis"]
    url = flask.request.form["url"]
    kopii = int(flask.request.form.get("kopii", 1))
    path = generuj_i_drukuj(opis, url, kopii)
    return flask.send_file(path, mimetype="image/png")


@app.route("/", methods=["POST", "GET"])
def podglad():
    if flask.request.method == "POST":
        opis = flask.request.form["opis"]
        url = flask.request.form["url"]
        png_b = generuj_png(opis, url)
        response = flask.make_response(png_b)
        response.headers["Content-Type"] = "image_png"
        return response
    else:
        return """
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <body onload="przerysujObrazek()">
        <script>
        function przerysujObrazek() {
            var xhr = new XMLHttpRequest();
            xhr.responseType = 'arraybuffer';
            xhr.onreadystatechange = function() {
                var arr = new Uint8Array(this.response);
                var raw = String.fromCharCode.apply(null,arr);
                var b64=btoa(raw);
                var dataURL="data:image/jpeg;base64,"+b64;
                document.getElementById("wygenerowany_obraz").src = dataURL;
            };
            xhr.open('POST', '/', true);
            var data = new FormData();
            opis = document.getElementById("opis").value;
            if (opis) {
                data.append('opis', document.getElementById("opis").value);
            } else {
                data.append('opis', "Przykładowy opis rzeczy");
            }
            data.append('url', document.getElementById("url").value);
            xhr.send(data)
        }
        </script>
            <form method="post" action="/drukuj">
            <label for="kopii">Kopii: </label>
            <input id="kopii" name="kopii" type="number"
                min="1" max="10" minlegth="1" value="1" style="width: 4em;"
            >
            <label for="opis">Tytuł: </label>
            <input id="opis" name="opis" type="text"
                onchange="przerysujObrazek();"
                onpaste="this.onchange();"
                oninput="this.onchange();"
                placeholder="Przykładowy opis rzeczy"
            >
            <label for="url">URL: </label>
            <input id="url" name="url" type="text"
                placeholder="pusty = brak QR"
                onchange="przerysujObrazek();"
                onpaste="this.onchange();"
                oninput="this.onchange();"
            >
            <input type="submit" value="Drukuj">
            </form>
            <img id="wygenerowany_obraz"
                style="border: 1px dotted; max-width: 100%">
        """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
