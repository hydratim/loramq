from lora_mq import LoRaMQ
import config

from machine import Pin, ADC
from time import sleep
import struct

lora = LoRaMQ(config)

def receive():
    while lora.rq_length()>0:
        print(lora.receive())

lora.attach_callback(receive)
lora.start()
adc=ADC()
adc_c = adc.channel(pin=Pin.exp_board.G5.id(), attn=ADC.ATTN_11DB) # Pycom Expansion Board G5 goes to Pycom LoPy Pin 13
while True:
    millivolts = adc_c.voltage()
    print(millivolts)
    b_data = struct.pack("!BH", 13, millivolts)
    print(b_data)
    lora.send(b_data)
    sleep(5)
