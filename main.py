#!/usr/bin/env python3

import os
import subprocess
import io
import re

import flask
import base58
import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import lxml.html


app = flask.Flask(__name__)


GNUJDB_KEY_REGEX = r"^[0-9A-HJ-NP-Za-km-z]{10}$"
GNUJDB_KEY_REGEX_COMPILED = re.compile(GNUJDB_KEY_REGEX)


def gen_key():
    ret = ""
    while not GNUJDB_KEY_REGEX_COMPILED.match(ret):
        ret = base58.b58encode(os.getrandom(7)).decode()
    return ret


def zbuduj_linie(opis):
    ret = []
    aktualna_opis = ""
    slowa = opis.split(" ")
    for slowo in slowa:
        if aktualna_opis:
            aktualna_opis += " "
        if len(aktualna_opis) + len(slowo) > 16:
            ret.append(aktualna_opis)
            aktualna_opis = ""
        if aktualna_opis:
            aktualna_opis += " "
        aktualna_opis += slowo
    ret.append(aktualna_opis)
    return "\n".join(ret)


def dopisz_do_gnujdb(k, opis, wlasnosc):
    s = requests.Session()
    url = "https://g.hs-ldz.pl/" + k
    html = s.get(url).text
    h = lxml.html.fromstring(html)
    csrf_token = h.xpath('//input [@name="csrfmiddlewaretoken"]/@value')[0]
    s.post(
        url,
        data={
            "csrfmiddlewaretoken": csrf_token,
            "tytul": opis,
            "wlasnosc": wlasnosc,
        },
    )


def generuj_png(k, opis, wlasnosc):
    qr = qrcode.make("https://g.hs-ldz.pl/" + k, box_size=3)
    img = Image.new("RGB", (500, 150), color="white")
    draw = ImageDraw.Draw(img)
    myFont = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 42
    )
    draw.text((0, 0), zbuduj_linie(opis), fill=(0, 0, 0), font=myFont)
    img.paste(qr, (390, 0))
    captionFont = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16
    )

    draw.text((390, 100), k, fill=(0, 0, 0), font=captionFont)
    if wlasnosc:
        draw.text(
            (390, 120), "wł. " + wlasnosc, fill=(0, 0, 0), font=captionFont
        )
    bio = io.BytesIO()
    img.save(bio, format="png")
    return bio.getvalue()


def generuj_i_drukuj(opis, wlasnosc, kopii):
    k = gen_key()
    png_b = generuj_png(k, opis, wlasnosc)
    path = "out/" + k + ".png"
    with open(path, "wb") as f:
        f.write(png_b)
    for i in range(kopii + 1):
        subprocess.check_call(
            """brother_ql  -m QL-800 -p /dev/usb/lp0 print -l 50 """ + path,
            shell=True,
        )
    dopisz_do_gnujdb(k, opis, wlasnosc)
    return path


@app.route("/drukuj", methods=["POST"])
def drukuj():
    opis = flask.request.form["opis"]
    wlasnosc = flask.request.form["wlasnosc"]
    kopii = int(flask.request.form.get("kopii", 1))
    path = generuj_i_drukuj(opis, wlasnosc, kopii)
    return flask.send_file(path, mimetype="image/png")


@app.route("/", methods=["POST", "GET"])
def podglad():
    if flask.request.method == "POST":
        opis = flask.request.form["opis"]
        wlasnosc = flask.request.form["wlasnosc"]
        png_b = generuj_png(gen_key(), opis, wlasnosc)
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
            data.append('wlasnosc', document.getElementById("wlasnosc").value);
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
            <label for="wlasnosc">Własność: </label>
            <input id="wlasnosc" name="wlasnosc" type="text"
                placeholder="nieznany"
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
    app.run(host="0.0.0.0")
