#!/usr/bin/env python

import sys
import getopt
import struct
import binascii
import pexpect
import paho.mqtt.client as mqtt

KEYADD = [0, 244, 229, 214, 163, 178, 163, 178, 193, 244, 229, 214, 163, 178, 193, 244, 229, 214, 163, 178]
KEYXOR = [0, 43,  60,  77,  94,  111, 247, 232, 217, 202, 187, 172, 157, 142, 127, 94,  111, 247, 232, 217]

MODES = [ 'OFF', 'FAST', 'SLOW', 'WARM', 'COOL', 'RED', 'GREEN', 'BLUE', 'WHITE', 'COLOR' ]
COMMAND = {
  'OFF':	[0x00],
  'FAST':	[0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01],
  'SLOW':	[0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02],
  'WARM':	[0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03],
  'COOL':	[0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04],
  'RED':	[0x01, 0x60, 0x00, 0x00],
  'GREEN':	[0x01, 0x00, 0x60, 0x00],
  'BLUE':	[0x01, 0x00, 0x00, 0x60],
  'WHITE':	[0x01],
  'COLOR':	[0x01]
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

def sendcmd(interface,address,mode,values):
  # interface = string of interface, ie: 'hci0'
  # address = string of mac address, ie: 'D0:39:72:E8:98:1F'
  # mode = string of mode name, ie: 'WHITE'
  # value = optional parameters for colors

  # print command
  print mode, values
  cmd = COMMAND[mode] + values
  enc = encrypt(cmd)
  hex = binascii.hexlify(struct.pack('B'*len(enc), *enc))
  cmd = 'char-write-cmd 25 {}'.format(hex)

  # execute with gatttool
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
  con.expect('\[LE\]>')
  con.sendline('exit')
  con.close()

def scale(val, src, dst):
  return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

def rgb2scale(color):
  # scale 8-bit rgb color to range 0..99
  r = int( scale(color[0], (0.0,255.0), (0.0,99.0)) )
  g = int( scale(color[1], (0.0,255.0), (0.0,99.0)) )
  b = int( scale(color[2], (0.0,255.0), (0.0,99.0)) )
  return r,g,b

def hex2scale(value):
  try:
    r = int(value[0:2],16)
    g = int(value[2:4],16)
    b = int(value[4:6],16)
  except:
    r, g, b = 255, 255, 255
  color = []
  color.append(r)
  color.append(g)
  color.append(b)
  return rgb2scale(color)

def validate(params):
  # default to white
  mode = 'WHITE'
  if params:
    m = params.pop(0)
    try:
      index = MODES.index(m)
      mode = m  
    except:
      return [ 'ERROR','Invalid mode: '+m ]

  values = []
  if mode == 'WHITE':
    try:
      values.append(params[0])
    except:
      values.append(60)
    values.append(values[0])
    values.append(values[0])

  if mode == 'COLOR':
    try:
      values.append(params[0])
      values.append(params[1])
      values.append(params[2])
    except:
      return [ 'ERROR','Incorrect number of arguments' ]

  for i,v in enumerate(values):
    try:
      val = int(v)
      if val > 99:
        val = 99
      if val < 0:
        val = 0
      values[i] = val
    except:
      return [ 'ERROR','Paramaters out of range' ]

  ret = [ mode ]
  ret.extend(values[:])
  return ret


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
  print "Connected with result code " + str(rc)
  client.subscribe(TOPIC)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
  params = []
  p = str(msg.payload).upper()
  print msg.topic + " " + p

  # Android MQTT Dashboard slider
  # sends a single number as text
  if p.isdigit():
    params.append('WHITE')
    params.extend([int(p)] * 3)

  # Android MQTT Dashboard color picker
  # Hex sends #RRGGBB
  elif p[0] == '#':
    params.append('COLOR')
    params.extend(hex2scale(p[1:]))

  # Android MQTT Dashboard color picker
  # RGB sends RGB(R,G,B)
  elif p[0:4] == 'RGB(':
    params.append('COLOR')
    colors = p[4:]
    colors = colors.strip(')')
    params.extend(rgb2scale([int(i) for i in colors.split(',')]))

  # anything needs validation
  else:
    params = validate(p.split(' '))

  print params
  mode = params.pop(0)
  if mode != 'ERROR':
    sendcmd(interface,address,mode,params)
  else:
    print mode,params[0]


interface = 'hci0'
address = 'D0:39:72:E8:98:1F'

TOPIC = 'test/lumen'
BROKER = 'iot.eclipse.org'
PORT = 1883

options, params = getopt.getopt(sys.argv[1:], 'i:a:', ['interface=','address='])
for opt, arg in options:
  if opt in ('-i', '--interface'):
    interface = arg
  elif opt in ('-a', '--address'):
    address = arg

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a manual interface.
client.loop_forever()


