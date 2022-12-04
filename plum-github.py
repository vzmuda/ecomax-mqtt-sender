# remade from 
# Analizator EcoNet
# (C) 2020 Tomasz Król https://github.com/twkrol/econetanalyze
# Gwarancji żadnej nie daję. Ale można korzystać do woli i modyfikować wg potrzeb
# you have to installed paho mqtt client  / pip install paho-mqtt / pip3 install paho-mqtt

import functools
import math
import socket
import struct
import sys
import os
import paho.mqtt.client as mqtt 
from random import randrange, uniform
import time

#########################################################################
# PARAMETRY ANALIZY
#########################################################################
# needed thing - use your mqtt address, username and password
# aby czytać z portu szeregowego doinstaluj bibliotekę pyserial i odkomentuj poniższy import
#import serial

# import parsera ramek sterowników EcoSter (również EcoTouch) z pliku ecoster.py
#import ecoster

# import parsera ramek sterownika EcoMax860p z pliku ecomax860p.py
# jeśli masz inny sterownik - napisz do niego swoją bibliotekę wzorując się na poniższej i podmień import np. import ecomax350 as ecomax
# jednocześnie może być zaimportowana tylko jedna biblioteka o nazwie lub aliasie ecomax
#import ecomax860p as ecomax


#ŹRÓDŁO DANYCH
#odkomentuj odpowiednią linię SOURCE=  aby czytać dane z pliku, strumienia sieciowego lub portu szeregowego

mqttBroker ="YOUR_MQTT_ADDRESS" 

client = mqtt.Client("Temperature_Inside")
client.username_pw_set("USERNAME", "PASSWORD")
client.connect(mqttBroker)

# SOURCE = 'FILE'
filePATH = "raw.txt"

SOURCE = 'STREAM'
streamIP = 'RS485-LAN  IP ADDRESS'
streamPORT = 8234

#SOURCE = 'SERIAL'
serialPORT = "COM8"
serialBAUDRATE = 115200



#########################################################################
# START ANALIZY
#########################################################################

#stałe
RAMKA_START = 0x68
RAMKA_STOP = 0x16
NADAWCA_ECONET = 0x56
NADAWCA_ECOMAX = 0x45         #piec pelletowy
NADAWCA_ECOSTER = 0x51        #panel dotykowy
NADAWCA_TYP_ECONET = 0x30
# ODBIORCA_BROADCAST = 0x00

#typy ramek
# RAMKA_ALARM = 0xBD
RAMKA_INFO_STEROWNIKA = 0x08
RAMKA_INFO_PANELU = 0x89

try:
  SOURCE
except:
  print("Nie wybrano źródła danych! Popraw konfigurację na początku tego pliku.")
  exit()

if SOURCE == 'FILE':
  f = open(filePATH, 'rb')
  #print (f"Plik {filePATH} został otwarty")

elif SOURCE == 'STREAM':
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((streamIP, streamPORT))
  #print (f"Port {streamPORT} pod adresem {streamIP} został otwarty")

elif SOURCE == 'SERIAL':
  ser = serial.Serial(serialPORT, serialBAUDRATE)
  ser.bytesize = serial.EIGHTBITS
  ser.parity = serial.PARITY_NONE
  ser.stopbits = serial.STOPBITS_ONE
  ser.open()
  #print (f"Port {serialPORT} został otwarty")

else:
  print("Nieznany typ źródła danych. Popraw konfigurację na początku tego pliku.")
  exit()


bajtCzytany = 0 # bajt aktualnie przetwarzany
bajtPoprzedni = 0
ramka = []

#mapa ramki
START_BYTE = 0              #[0]
ROZMIAR_RAMKI_SHORT = 1     #[1,2]
ADRES_ODBIORCY_BYTE = 3     #[3]
ADRES_NADAWCY_BYTE = 4      #[4]
TYP_NADAWCY_BYTE = 5        #[5]
WERSJA_ECONET_BYTE = 6      #[6]
TYP_RAMKI = 7               #[7]
CRC_BYTE = -2               #[przedostatni bajt]
MESSAGE_START = 7           #od-do [7:-2]


while True:
  #pobieramy 1 bajt, z pliku, sieci lub portu szeregowego

  if SOURCE == 'FILE':
    chunk = f.read(1)
    if len(chunk) == 0:
      break
  elif SOURCE == 'STREAM':
    chunk = s.recv(1)
  elif SOURCE == 'SERIAL':
    chunk = ser.read(1)

  bajtCzytany = ord(chunk)

  #badamy czy to początek nowej ramki
  if bajtCzytany == RAMKA_START and bajtPoprzedni == RAMKA_STOP:

    #zaczęła się nowa ramka wiec zebrane do tej pory dane do analizy, jesli jakieś są
    if len(ramka) > 0:
  
      #badanie sumy kontrolnej CRC
      ramkaCRC = ramka[-2]
      myCRC = functools.reduce(lambda x,y: x^y, ramka[:-2])

      #analizujemy ramkę tylko jak CRC się zgadza
      if myCRC == ramkaCRC:

        #zawartość ramki w hex dla czytelniejszego kodu i prezentacji
        ramkaHEX = [f'{ramka[i]:02X}' for i in range(0, len(ramka))]
        
        #wyciągamy z ramki właściwy message
        message = ramka[MESSAGE_START:CRC_BYTE]
        messageHEX = ramkaHEX[MESSAGE_START:CRC_BYTE]

        #dane diagnostyczne ramki
        if len(message) > 1:
          #print("")
          #print(f"== [ramka] [Typ: 0x{ramka[TYP_RAMKI]:02X}] [Długość:{len(ramka)}] [Nadawca: 0x{ramka[ADRES_NADAWCY_BYTE]:02X}] [Odbiorca: 0x{ramka[ADRES_ODBIORCY_BYTE]:02X}] [CRC:0x{ramkaCRC:02X}] ==")
         
          #zawartość ramki w ASCII
           #if True:
            # tekst = ''
             #for i in range(7, len(ramka)-2):
              # if ramka[i] > 32 and ramka[i] < 127:
               #  tekst += chr(ramka[i])
            # print(tekst)

          #Zawartość ramki w HEX i DEC
          rowsize=12
          for row in range(math.ceil(len(message)/rowsize)):
            od = row*rowsize
            do = od+rowsize if len(message) >= od+rowsize else len(message)
            #print(f"{od:03d}-{do-1:03d} \t{' '.join(messageHEX[od:do])}", end='')
            #print('   ' * ((od+rowsize)-do), end='')
            #print(f" \t{message[od:do]}")


        #Analiza komunikatu ze sterownika pokojowego ECOTouch
   #     if ramka[ADRES_NADAWCY_BYTE] == NADAWCA_ECOSTER:
   #       ecoster.parseFrame(message)

        #Analiza komunikatu ze sterownika pieca EcoMax
  #      if ramka[ADRES_NADAWCY_BYTE] == NADAWCA_ECOMAX: 
   #       parseFrame(message)
   #     def parseFrame(message):
        if message[0] == 0x08:
          parseFrame08(message)
        def parseFrame08(message):
      #mapa komunikatu stanu ze sterownika pieco EcoMax860P Lazar SmartFire
      # typ ramki = 0x08          #[0]
          OPERATING_STATUS_byte = 1   #[33] pravda
          PUMP_STATUS_byte = 2        #[2]moje pro test
          TEMP_CWU_float = 42         #[74-77] voda v bojleru pravda
          TEMP_FEEDER_float = 46      #[78-81] teplota hořáku
          TEMP_CO_float = 50          #[82-85] teplota kotle
          TEMP_WEATHER_float = 58     #[90-93] teplota venkovní
          TEMP_EXHAUST_float = 62     #[94-97] teplota zpátečky
          TEMP_MIXER_float = 54      #[106-109] teplota 4cestný ventil
          TEMP_CWU_SET_byte = 146     #[146] lub #29
          TEMP_CO_SET_byte = 148      #[148]
          FAN_LEVEL_byte=179         #[189] pravda
          FUEL_LEVEL_byte=156        #[156 pravda!]
          boilerPowerKW_FLOAT=180     #[180] výkon kotle
          fuelStream=184 # spotřeba paliva
          LAMBDA_LEVEL_float=226      #[226-229]
          OXYGEN_float = 230          #[230-233]
          POWER100_TIME_short = 235   #[235-236]
          POWER50_TIME_short = 237    #[237-238]
          POWER30_TIME_short = 239    #[239-240]
          FEEDER_TIME_short = 241     #[241-242]
          IGNITIONS_short = 243       #[243-244]

          OPERATION_STATUSES = {0:'Vypnuti', 1:'Zapalování', 2:'Stabilizace', 3:'Práce', 4:'Útlum', 5:'Vyhasínání', 6:'POSTÓJ', 7:'Vyhasniutí na požadavek', 9:'ALARM', 10:'ROZSZCZELNIENIE'}
         
          #print("")
          #entity_id = "input_number.plum_stav_kotle"
          #value = OPERATING_STATUS_BYTE
          #if entity_id is not None:
          #  service_data = {"entity_id": entity_id, "value": value}
          #  hass.services.call("input_number", "set_value", service_data, False)

          #Stan pieca [33]
          print(f"Stav kotle: {OPERATION_STATUSES[message[OPERATING_STATUS_byte]] if message[OPERATING_STATUS_byte] in OPERATION_STATUSES else str(message[OPERATING_STATUS_byte]) }")

          #Stav čerpadel [2] 1 ventilátor,2 podavač,4 čerpadlo kotle,8 čerpadlo tuv,16 čerpadlo mix, 128 něco

          print(f"CZ stav čerpadel: {message[PUMP_STATUS_byte]}")
          a = message[PUMP_STATUS_byte]
          print(a)

          # odečítání 128

          b = 128
          if a >= b:
            print("odečítám 128 kvůli něčeho")
            a = a - b
          else:
            print(" číslo 128 nebylo obsaženo")
    
          # odečítání 16
          b = 16
          if a >= b:
            print("čerpadlo mix zapnuto")
            a = a - b
          else:
            print("čerpadlo mix vypnuto")

          # odečítání 8
          b = 8
          if a >= b:
            print("čerpadlo bojler zapnuto")
            a = a - b
          else:
            print("čerpadlo bojler vypnuto")

            # odečítání 4
          b = 4
          if a >= b:
            print("čerpadlo kotel zapnuto")
            a = a - b
          else:
            print("čerpadlo kotel vypnuto")

          # odečítání 2
          b = 2
          if a >= b:
            print("podavač uhlí zapnutý")
            a = a - b
          else:
            print("podavač uhlí vypnutý")

          # odečítání 1
          b = 1
          if a >= b:
            print("ventilátor zapnutý")
            a = a - b
          else:
            print("ventilátor vypnutý")
    
          #Poziom paliwa [156]
          print(f"CZ stav paliva: {message[FUEL_LEVEL_byte]}%")

          #Poziom paliwa [156]
          spotrebapaliva = struct.unpack("f", bytes(message[fuelStream:fuelStream+4]))[0]
          print(f"Spotřeba paliva: {spotrebapaliva:.1f} kg/h")

          #Poziom paliwa [189]
          print(f"CZ výkon ventilátoru : {message[FAN_LEVEL_byte]}%")

          #Temperatura CWU [74-77]
          tempCWU = struct.unpack("f", bytes(message[TEMP_CWU_float:TEMP_CWU_float+4]))[0]
          print(f"Teplota vody v bojleru: {tempCWU:.1f}")

          #Temperatura CO [82-85]
          tempCO = struct.unpack("f", bytes(message[TEMP_CO_float:TEMP_CO_float+4]))[0]
          print(f"Teplota topné vody: {tempCO:.1f}")

          #Temperatura pogodowa
          tempPogodowa= struct.unpack("f", bytes(message[TEMP_WEATHER_float:TEMP_WEATHER_float+4]))[0]
          print(f"Teplota venkovní: {tempPogodowa:.1f}")

          #Temperatura spalin
          tempSpalin = struct.unpack("f", bytes(message[TEMP_EXHAUST_float:TEMP_EXHAUST_float+4]))[0]
          print(f"Teplota zpátečky: {tempSpalin:.1f}")

          #Temperatura podajnika
          tempPodajnika = struct.unpack("f", bytes(message[TEMP_FEEDER_float:TEMP_FEEDER_float+4]))[0]
          print(f"Teplota hořáku: {tempPodajnika:.1f}")

          #Tlen
          #tlen = struct.unpack("f", bytes(message[OXYGEN_float:OXYGEN_float+4]))[0]
          #print(f"Tlen: {tlen:.1f}%")

          #Temperatura mieszacza
          tempMieszacza = struct.unpack("f", bytes(message[TEMP_MIXER_float:TEMP_MIXER_float+4]))[0]
          print(f"Teplota 4cestný ventil: {tempMieszacza:.1f}")

          #Moc kotła
          moc = struct.unpack("f", bytes(message[boilerPowerKW_FLOAT:boilerPowerKW_FLOAT+4]))[0]
          print(f"Výkon kotle: {moc:.1f} kW")

          #LambdaSet
          #lambdaLevel = struct.unpack("f", bytes(message[160:160+4]))[0]
          #print(f"Lambda: {lambdaLevel:.1f}")

          #4wayvalve?
          zawor = (message[174])
          print(f"4cestný ventil: {zawor:d}%")

          # mqqt send
          client.publish("PLUM", "OPERATING_STATUS_byte;" + str(message[OPERATING_STATUS_byte]) + ";PUMP_STATUS_byte;" + str(message[PUMP_STATUS_byte]) + ";FUEL_LEVEL_byte;" + str(message[FUEL_LEVEL_byte]) + ";spotrebapaliva;" + str(spotrebapaliva) + ";FAN_LEVEL_byte;" +str(message[FAN_LEVEL_byte]) + ";tempCWU;" +str(tempCWU) + ";tempCO;" + str(tempCO) + ";tempPogodowa;" + str(tempPogodowa) + ";tempSpalin;" + str(tempSpalin) + ";tempPodajnika;" + str(tempPodajnika) + ";tempMieszacza;" + str(tempMieszacza) + ";moc;" +str(moc) + ";zawor;" + str(zawor) + ";" )
          print("Just published " + str(OPERATING_STATUS_byte) + " to topic TEMPERATURE")
          time.sleep(5)


    #ramka przeanalizowana, można wyczyścić i aktualny bajt zostanie wpisany już do nowej (poniżej)
    ramka = []


  #dodajemy przeczytany bajt do bieżącej ramki
  ramka.append(bajtCzytany)  

  #zapamiętujemy ostatni bajt żeby zdekodować zakończenie ramki
  bajtPoprzedni = bajtCzytany
