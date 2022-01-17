#!/usr/bin/env python3

import os
import subprocess
import io

import flask
import base58
import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import lxml.html


app = flask.Flask(__name__)


def zbuduj_linie(line):
    ret = []
    aktualna_linia = ""
    slowa = line.split(" ")
    for slowo in slowa:
        if aktualna_linia:
            aktualna_linia += " "
        if len(aktualna_linia) + len(slowo) > 16:
            ret.append(aktualna_linia)
            aktualna_linia = ""
        if aktualna_linia:
            aktualna_linia += " "
        aktualna_linia += slowo
    ret.append(aktualna_linia)
    return "\n".join(ret)


def gen_key():
    return base58.b58encode(os.getrandom(7)).decode()


def dopisz_do_gnujdb(k, opis):
    s = requests.Session()
    url = "https://g.hs-ldz.pl/" + k
    html = s.get(url).text
    h = lxml.html.fromstring(html)
    csrf_token = h.xpath('//input [@name="csrfmiddlewaretoken"]/@value')[0]
    s.post(url, data={"csrfmiddlewaretoken": csrf_token, "tytul": opis})


def generuj_png(k, line):
    qr = qrcode.make("https://g.hs-ldz.pl/" + k, box_size=3)
    img = Image.new("RGB", (500, 150), color="white")
    draw = ImageDraw.Draw(img)
    myFont = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 42
    )
    draw.text((0, 0), zbuduj_linie(line), fill=(0, 0, 0), font=myFont)
    img.paste(qr, (390, 0))
    captionFont = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16
    )

    draw.text((390, 100), k, fill=(0, 0, 0), font=captionFont)
    bio = io.BytesIO()
    img.save(bio, format="png")
    return bio.getvalue()


def generuj(line):
    k = gen_key()
    png_b = generuj_png(k, line)
    path = "out/" + k + ".png"
    with open(path, "wb") as f:
        f.write(png_b)
    subprocess.check_call(
        """brother_ql  -m QL-800 -p /dev/usb/lp0 print -l 50 """ + path,
        shell=True,
    )
    dopisz_do_gnujdb(k, line)
    return path


@app.route("/podglad", methods=["POST", "GET"])
def podglad():
    if flask.request.method == "POST":
        line = flask.request.form["linia"]
        png_b = generuj_png("XXXXX", line)
        response = flask.make_response(png_b)
        response.headers["Content-Type"] = "image_png"
        return response
    else:
        return """
        <script>
        function linesChanged() {
            var xhr = new XMLHttpRequest();
            xhr.responseType = 'arraybuffer';
            xhr.onreadystatechange = function() {
                var arr = new Uint8Array(this.response);
                var raw = String.fromCharCode.apply(null,arr);
                var b64=btoa(raw);
                var dataURL="data:image/jpeg;base64,"+b64;
                document.getElementById("elo").src = dataURL;
            };
            xhr.open('POST', '/podglad', true);
            var data = new FormData();
            data.append('linia', document.getElementById("linia").value);
            xhr.send(data)
        }
        </script>
            <form method="post" action="/podglad">
            <input id="linia" name="linia" type="text"
                onchange="linesChanged();"
                onpaste="this.onchange();"
                oninput="this.onchange();"
            ></form>
            <img id="elo">
        """


@app.route("/drukuj", methods=["POST"])
def drukuj():
    line = flask.request.form["linia"]
    path = generuj(line)
    return flask.send_file(path, mimetype="image/png")


@app.route("/")
def index():
    return (
        """<form method="post" action="/drukuj"><input name="linia"></form>"""
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0")
