#!/usr/bin/env python

import sys
import getopt
import struct
import binascii
import pexpect

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

#for mode in MODES:
#  cmd = COMMAND[mode]
#  enc = encrypt(cmd)
#  c = binascii.hexlify(struct.pack('B'*len(enc), *enc))
#  print mode
#  print 'char-write-cmd 25 {}'.format(c)

interface = 'hci0'
address = 'D0:39:72:E8:98:1F'
mode = 'WHITE'

options, params = getopt.getopt(sys.argv[1:], 'i:a:', ['interface=','address='])
for opt, arg in options:
  if opt in ('-i', '--interface'):
    interface = arg
  elif opt in ('-a', '--address'):
    address = arg

if params:
  mode = params.pop(0).upper()

try:
  index = MODES.index(mode)
except:
  print "Error: Invalid mode: {}".format(mode)
  sys.exit(1)

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
    print "Error: Color requires three values in range 0-99"
    sys.exit(1)

for i,v in enumerate(values):
  try:
    val = int(v)
    if val > 99:
      val = 99
    if val < 0:
      val = 0
    values[i] = val
  except:
    print "Error: values are integers in range 0-99"
    sys.exit(1)

print mode, values
cmd = COMMAND[mode] + values
print cmd
enc = encrypt(cmd)
hex = binascii.hexlify(struct.pack('B'*len(enc), *enc))
print hex
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
con.expect('\[LE\]>')
con.sendline('exit')
con.close()

