#!/usr/bin/env python3

import os
import subprocess

import flask
import base58
import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import lxml.html


app = flask.Flask(__name__)


def zbuduj_linie(line):
    ret = []
    aktualna_linia = ''
    slowa = line.split(' ')
    for slowo in slowa:
        if aktualna_linia:
            aktualna_linia += ' '
        if len(aktualna_linia) + len(slowo) > 16:
            ret.append(aktualna_linia)
            aktualna_linia = ''
        if aktualna_linia:
            aktualna_linia += ' '
        aktualna_linia += slowo
    ret.append(aktualna_linia)
    return '\n'.join(ret)


def gen_key():
    return base58.b58encode(os.getrandom(7)).decode()


def dopisz_do_gnujdb(k, opis):
    s = requests.Session()
    url = "https://g.hs-ldz.pl/" + k
    html = s.get(url).text
    h = lxml.html.fromstring(html)
    csrf_token = h.xpath('//input [@name="csrfmiddlewaretoken"]/@value')[0]
    s.post(url, data={'csrfmiddlewaretoken': csrf_token, 'tytul': opis})


def generuj(line):
    k = gen_key()
    qr = qrcode.make('https://g.hs-ldz.pl/' + k, box_size=3)

    img = Image.new('RGB', (500, 150), color='white')
    draw = ImageDraw.Draw(img)
    myFont = ImageFont.truetype(
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 42)
    draw.text((0, 0), zbuduj_linie(line),
              fill=(0, 0, 0), font=myFont)
    img.paste(qr, (390, 0))
    captionFont = ImageFont.truetype(
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 16)

    draw.text((390, 100), k,
              fill=(0, 0, 0), font=captionFont)

    path = 'out/' + k + ".png"
    img.save(path)
    subprocess.check_call(
        '''brother_ql  -m QL-800 -p /dev/usb/lp0 print -l 50 ''' + path, shell=True)
    dopisz_do_gnujdb(k, line)
    return path


@app.route('/drukuj', methods=['POST'])
def drukuj():
    line = flask.request.form['linia']
    path = generuj(line)
    return flask.send_file(path, mimetype='image/png')


@app.route('/')
def index():
    return '''<form method="post" action="/drukuj"><input name="linia"></form>'''


if __name__ == '__main__':
    app.run(host='0.0.0.0')
