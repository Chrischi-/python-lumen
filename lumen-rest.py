#!/usr/bin/env python

import sys
import struct
import binascii
import pexpect

from flask import Flask, render_template, redirect, request
app = Flask(__name__)

KEYADD = [0, 244, 229, 214, 163, 178, 163, 178, 193, 244, 229, 214, 163, 178, 193, 244, 229, 214, 163, 178]
KEYXOR = [0, 43,  60,  77,  94,  111, 247, 232, 217, 202, 187, 172, 157, 142, 127, 94,  111, 247, 232, 217]

MODES = [ 'OFF', 'FAST', 'SLOW', 'WARM', 'COOL', 'RED', 'GREEN', 'BLUE', 'WHITE', 'COLOR' ]
MODE = {
  'OFF': {
	'CMD':  [0x00],
	'DESC': 'Turn off Lumen strip',
  },
  'FAST': {
	'CMD':  [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01],
	'DESC': 'Lumen strip cycles through colors quickly',
  },
  'SLOW': {
	'CMD':  [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02],
	'DESC': 'Lumen strip cycles through colors slowly',
  },
  'WARM': {
	'CMD':  [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03],
	'DESC': 'Lumen strip cycles through <b>warm</b> temperature colors',
  },
  'COOL': {
	'CMD':  [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04],
	'DESC': 'Lumen strip cycles through <b>cool</b> temperature colors',
  },
  'RED': {
	'CMD':  [0x01, 0x60, 0x00, 0x00],
	'DESC': 'Turns Lumen strip red',
  },
  'GREEN': {
	'CMD':  [0x01, 0x00, 0x60, 0x00],
	'DESC': 'Turns Lumen strip green',
  },
  'BLUE': {
	'CMD':  [0x01, 0x00, 0x00, 0x60],
	'DESC': 'Turns Lumen strip blue',
  },
  'WHITE': {
	'CMD':  [0x01],
	'DESC': 'Turns Lumen strip white, parameters: <i>?percent=value</i>',
	'OPTS': { 'percent':60 }
  },
  'COLOR': {
	'CMD':  [0x01],
	'DESC': 'Turns Lumen strip any color, parameters: <i>?r=value&g=value&b=value</i>',
	'OPTS': { 'r':99, 'g':55, 'b':5 }
  }
}

def encrypt(command):
  # commands are 20 bytes after encryption
  data = [0] * 20
  c = 0
  i = len(data) - 1
  while i >= 0:
    try:
      data[i] = command[i]
    except IndexError:
      pass
    val = data[i] + KEYADD[i] + c
    c,data[i] = divmod(val, 256)
    data[i] ^= KEYXOR[i]
    i -= 1

  # reset first byte
  data[0] = 0x01 & command[0]
  return data

@app.route('/')
def menu():
  return redirect('/lumen/menu')

@app.route('/lumen/<m>')
def lumen(m):
  interface = 'hci0'
  address = 'D0:39:72:E8:98:1F'
  mode = m.upper()

  if mode == 'INFO' or mode == 'MENU':
    return render_template('menu.html', status=mode, message='Available modes:', items=MODES, info=MODE)

  try:
    index = MODES.index(mode)
  except:
    message = 'Invalid mode: {}'.format(m)
    return render_template('menu.html', status='Error', message=message, items=MODES, info=MODE)

  values = []
  if mode == 'WHITE':
    try:
      values.append(request.args['percent'])
    except:
      values.append(60)
    values.append(values[0])
    values.append(values[0])

  if mode == 'COLOR':
    try:
      values.append(request.args['r'])
      values.append(request.args['g'])
      values.append(request.args['b'])
    except:
      message = 'Color requires three RGB parameters in range 0-99'
      message += '<p>color<i>?r=value&g=value&b=value</i>'
      return render_template('error.html', message=message)

  for i,v in enumerate(values):
    try:
      val = int(v)
      if val > 99:
        val = 99
      if val < 0:
        val = 0
      values[i] = val
    except:
      message = 'Parameters are integers in range 0-99'
      return render_template('error.html', message=message)

  raw = mode + ' ' + ''.join(str(values))
  cmd = MODE[mode]['CMD'] + values
  enc = encrypt(cmd)
  hex = binascii.hexlify(struct.pack('B'*len(enc), *enc))
  cmd = 'char-write-cmd 25 {}'.format(hex)

  con = pexpect.spawn('gatttool -I -i ' + interface + ' -b ' + address)
  con.expect('\[LE\]>')
  con.sendline('connect')
  con.expect('successful')
  con.sendline('char-write-cmd 25 08610766a7680f5a183e5e7a3e3cbeaa8a214b6b')
  con.expect('\[LE\]>')
  con.sendline('char-read-hnd 28')
  con.expect('\[LE\]>')
  con.sendline('char-write-cmd 25 07dfd99bfddd545a183e5e7a3e3cbeaa8a214b6b')
  con.expect('\[LE\]>')
  con.sendline('char-read-hnd 28')
  con.expect('\[LE\]>')
  con.sendline(cmd)
  con.expect('\[LE\]>')
  con.sendline('disconnect')
  con.close()

  message = 'Success'
  return render_template('success.html', message=message, raw=raw, enc=hex, cmd=cmd)


if __name__ == '__main__':
  app.run(debug=True, port=8000, host='0.0.0.0')

