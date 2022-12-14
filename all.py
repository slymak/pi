#!/usr/bin/python3
from ina219 import INA219
#from ina219 import DeviceRangeError
import time
import datetime
import logging
logging.basicConfig(format='%(asctime)s - %(message)s',filename='logall.log')
from board import SCL, SDA
import busio
from oled_text import OledText
i2c = busio.I2C(SCL, SDA)
oled = OledText(i2c, 128, 64)

import sys
import board
from barbudor_ina3221.lite import INA3221
i2c_bus = board.I2C()
ina3221 = INA3221(i2c_bus)

import matplotlib.pyplot as plt

grid_on = True
grid_off = False
SHUNT_OHMS = 0.1


import RPi.GPIO as GPIO
pinrele1 = 16           #vout
pinrele3 = 13           #bat1
pinrele2 = 20           #bat2 mala bila
pinrele4 = 21           #vin
pinregulv= 12
pinred = 26
pinwhite = 19

#reley
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(pinrele1, GPIO.OUT)
GPIO.output(pinrele1, GPIO.HIGH)
GPIO.setup(pinrele2, GPIO.OUT)
GPIO.output(pinrele2, GPIO.HIGH)
GPIO.setup(pinrele3, GPIO.OUT)
GPIO.output(pinrele3, GPIO.HIGH)
GPIO.setup(pinrele4, GPIO.OUT)
GPIO.output(pinrele4, GPIO.HIGH)
# PWM regulace
GPIO.setup(pinregulv, GPIO.OUT)
regulacev = GPIO.PWM(pinregulv,9000)
#LEDky
GPIO.setup(pinred, GPIO.OUT)
redpwm = GPIO.PWM(pinred, 60)
redpwm.start(0)
GPIO.setup(pinwhite, GPIO.OUT)
whitepwm = GPIO.PWM(pinwhite, 60)



def read_ina():
    ina3221.enable_channel(1)
    ina3221.enable_channel(2)
    ina3221.enable_channel(3)

    vin = float("{:.2f}".format(ina3221.bus_voltage(1)))
    ain = float("{:.2f}".format(ina3221.current(1) * 1000)) 
    vbat1 = float("{:.2f}".format(ina3221.bus_voltage(2)))
    vbat2 = float("{:.2f}".format(ina3221.bus_voltage(3)))

    ina2 = INA219(SHUNT_OHMS,3, address=0x44)
    ina2.configure()
    
    #display values    
    vinoled = 'vin: ',vin
    oled.text(vinoled, 1)
    vbat1oled = "vbat1 ",vbat1
    oled.text(vbat1oled,2)
    vbat2oled = "vbat2 ",vbat2
    oled.text(vbat2oled,3)
    vout = float("{:.2f}".format(ina2.voltage()))
    voutoled = 'vout ',vout
    oled.text(voutoled, 4)
    aout = float("{:.2f}".format(ina2.current()))
    aoutoled = "aout: ", aout
    oled.text(aoutoled, 5)
    print(f"----vbat1 dole {vbat1} vbat2 bila {vbat2} vin: {vin} vout: {vout} ain: {ain} aout: {aout}")
    
    #collect reley status
    status = GPIO.input(pinrele3)
    if status:
        rbat1 = 0
    else:
        rbat1 = 1
    status = GPIO.input(pinrele2)
    if status:
        rbat2 = 0
    else:
        rbat2 = 1
    status = GPIO.input(pinrele1)
    if status:
        rout = 0
    else:
        rout = 1
    status = GPIO.input(pinrele4)
    if status:
        rin = 0
    else:
        rin = 1
    #print(f"   RELE bat1 {rbat1} bat2 {rbat2} in {rin} out {rout}")

    #grid check 
    if baterry == "horni":
        vbat = vbat2
    elif baterry == "dolni":
        vbat = vbat1
    if vin < vbat:      #dojde stava
        grid_on = False
        grid_off = True
#        print(f"grid NENI  off ma {grid_off} on ma {grid_on}")
    else:
        grid_on = True
        grid_off = False
#        print(f"grid off ma {grid_off} on ma {grid_on}")

    
    ina = dict()
    ina['vout'] = vout
    ina['vin'] = vin
    ina['vbat'] = vbat
    ina['vbat1'] = vbat1
    ina['vbat2'] = vbat2
    ina['aout'] = aout
    ina['ain'] = ain
    ina['grid_on'] = grid_on
    ina['grid_off'] = grid_off
    return ina
    
######################################
def charging(baterry, pinrelebat, pinrelebat2, maxvbat, maxain):
    start_charg = time.time()
    regulacev.start(0)
    GPIO.output(pinrele1, GPIO.HIGH)
    GPIO.output(pinrelebat, GPIO.LOW)
    GPIO.output(pinrelebat2, GPIO.HIGH)
    GPIO.output(pinrele4, GPIO.LOW)
        
    read_ina()
    ina = read_ina()
    xcycle = 1
    x = [1]
    y = [ina['vbat']]
    
    #loop till 
    while ina['vbat'] < maxvbat  and ina['vin'] > ina['vbat']:
        read_ina()
        ina = read_ina()
            
        print(f"{xcycle} charging xcycle baterry {baterry} Vbat = {ina['vbat']}, Vin = {ina['vin']}  Ain {ina['ain']}")
        xcycle += 1
        x.append(xcycle)
        y.append(ina['vbat'])	
        #PWM regulation
        if ina['ain'] < maxain:
            vykon = 100
            regulacev.ChangeDutyCycle(vykon)
            print("PWM regulation is: ", vykon)
            redpwm.ChangeFrequency(vykon/100)
            time.sleep(6)
        else:
            vykon = 60
            regulacev.ChangeDutyCycle(vykon)
            print("regulacev is ", vykon)
            redpwm.ChangeFrequency(vykon/100)
            time.sleep(14)

    #creating plot
    dt = datetime.datetime.now()
    datum = dt.strftime("%y%m%d-%H:%M")
    end_charg = (start_charg - time.time())/60
    logging.warning(f" baterry {baterry} charged in {end_charg} minut")
    plt.plot(x,y)
    plt.xlabel('time period  6s')
    plt.ylabel('voltage')
    plt.title(f"charging baterry {baterry} took {xcycle} period")
    plt.savefig(f"charge_{baterry}_{datum}.png")   
    plt.clf()
    print (*x)
    print (*y)
    x = []
    y = []
    
    GPIO.output(pinrelebat, GPIO.HIGH)
    GPIO.output(pinrelebat2, GPIO.LOW)
    GPIO.output(pinrele4, GPIO.HIGH)
    GPIO.output(pinrele1, GPIO.HIGH)

######################################
def discharging(baterry, pinrelebat, pinrelebat2, minvbat):
    start_discharg = time.time()
    GPIO.output(pinrele1, GPIO.LOW)
    GPIO.output(pinrelebat2, GPIO.LOW)
    GPIO.output(pinrelebat, GPIO.HIGH)
    GPIO.output(pinrele4, GPIO.HIGH)

    read_ina()
    ina = read_ina()
    xcycle = 1
    x = [1]
    y = [ina['vbat']]

    while ina['vbat'] > minvbat  and ina['vin'] > ina['vbat']:
        read_ina()
        ina = read_ina()
        print(f"{xcycle} DIScharging xcycle baterry {baterry} Vbat = {ina['vbat']}, Vin = {ina['vin']}  Ain {ina['ain']}")
        xcycle += 1
        x.append(xcycle)
        y.append(ina['vbat'])	
        time.sleep(6)
        
    dt = datetime.datetime.now()
    datum = dt.strftime("%y%m%d-%H:%M")
    end_discharg = (start_discharg - time.time())/60    
    logging.warning(f" baterry {baterry} DIScharged in {end_discharg} minutes")
    
    #creating plot
    plt.figure
    plt.plot(x,y)
    #for i in range(len(x)):
    #    plt.annotate(str(y[i]), xy=(x[i], y[i]))
    plt.xlabel('time period 6s')
    plt.ylabel('voltage')
    plt.title(f"discharging baterry {baterry} took {xcycle} period")
    plt.savefig(f"discharge_{baterry}_{datum}.png")
    plt.clf()
    print (*x, sep = ", ")
    print (*y, sep = ", ")
    x = []
    y = []
    
    GPIO.output(pinrele1, GPIO.HIGH)
    GPIO.output(pinrelebat2, GPIO.HIGH)
    GPIO.output(pinrelebat, GPIO.HIGH)
    GPIO.output(pinrele4, GPIO.HIGH)
    
#------------ main ------------------
try:
    cycle = 1
    while cycle < 5:
        baterry = "horni"
        read_ina()
        ina = read_ina()
        print(f"{cycle} CYCLE begining vin {ina['vin']} vbat1 {ina['vbat1']} vbat2 {ina['vbat2']}")

#grid is on ----------------------
        while ina['grid_on'] and cycle < 5:
            if ina['grid_off'] == True:
                break
            if (cycle % 2) == 0:        
                # dolni baterka
                baterry = "dolni"
                maxvbat = 12.05
                maxain = 730
                pinrelebat = pinrele3
                pinrelebat2 = pinrele2
                minvbat = 8.5
            else:
                # horni baterka
                baterry = "horni"
                maxvbat = 16.1
                maxain = 230
                pinrelebat = pinrele2
                pinrelebat2 = pinrele3
                minvbat = 9.1

            
            # charging ---------------------------------
            charging(baterry, pinrelebat, pinrelebat2, maxvbat, maxain)
            
            read_ina()
            ina = read_ina()
            if ina['grid_off'] == True:
                break
            time.sleep(4)
            
            # discharging ------------------------------
            discharging(baterry, pinrelebat, pinrelebat2, minvbat)

            read_ina()
            ina = read_ina()
            if ina['grid_off'] == True:
                break
            cycle += 1
            time.sleep(2)
            print(f"{cycle} cycle for baterry {baterry} VYBITO ")            
            
# grid off waiting for grid    
        while ina['grid_off']:
            print(f"         no input grid ")
            time.sleep(11)
            
            read_ina()
            ina = read_ina()
            time.sleep(4)
            if ina['grid_off'] == True:
                break


except KeyboardInterrupt:
    print("intentionaly interrupted ")
    regulacev.stop()
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pinrele4, GPIO.OUT)
    GPIO.output(pinrele4, GPIO.HIGH)
    GPIO.setup(pinrele2, GPIO.OUT)
    GPIO.output(pinrele2, GPIO.LOW)
    GPIO.setup(pinrele3, GPIO.OUT)
    GPIO.output(pinrele3, GPIO.HIGH)
    GPIO.setup(pinrele1, GPIO.OUT)
    GPIO.output(pinrele1, GPIO.HIGH)

else:
    print(f" charging / discharging period {cycle} is done")

