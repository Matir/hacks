EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L RF_Module:ESP32-WROOM-32D U2
U 1 1 6067F170
P 5450 3650
F 0 "U2" H 5000 5050 50  0000 C CNN
F 1 "ESP32-WROOM-32D" H 5950 5050 50  0000 C CNN
F 2 "RF_Module:ESP32-WROOM-32" H 5450 2150 50  0001 C CNN
F 3 "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_esp32-wroom-32u_datasheet_en.pdf" H 5150 3700 50  0001 C CNN
	1    5450 3650
	1    0    0    -1  
$EndComp
Wire Wire Line
	6050 2550 6350 2550
Wire Wire Line
	6050 2750 6350 2750
Text Label 6350 2550 2    50   ~ 0
TXD
Text Label 6350 2750 2    50   ~ 0
RXD
$Comp
L power:GND #PWR012
U 1 1 6067FA35
P 5450 5150
F 0 "#PWR012" H 5450 4900 50  0001 C CNN
F 1 "GND" H 5455 4977 50  0000 C CNN
F 2 "" H 5450 5150 50  0001 C CNN
F 3 "" H 5450 5150 50  0001 C CNN
	1    5450 5150
	1    0    0    -1  
$EndComp
Wire Wire Line
	5450 5050 5450 5150
$Comp
L power:+3V3 #PWR011
U 1 1 6068021C
P 5450 2150
F 0 "#PWR011" H 5450 2000 50  0001 C CNN
F 1 "+3V3" H 5465 2323 50  0000 C CNN
F 2 "" H 5450 2150 50  0001 C CNN
F 3 "" H 5450 2150 50  0001 C CNN
	1    5450 2150
	1    0    0    -1  
$EndComp
Wire Wire Line
	5450 2150 5450 2250
$Comp
L power:+3V3 #PWR010
U 1 1 6068043A
P 4500 2100
F 0 "#PWR010" H 4500 1950 50  0001 C CNN
F 1 "+3V3" H 4515 2273 50  0000 C CNN
F 2 "" H 4500 2100 50  0001 C CNN
F 3 "" H 4500 2100 50  0001 C CNN
	1    4500 2100
	1    0    0    -1  
$EndComp
$Comp
L Switch:SW_Push SW2
U 1 1 6068140E
P 6550 2450
F 0 "SW2" H 6550 2735 50  0000 C CNN
F 1 "SW_Push" H 6550 2644 50  0000 C CNN
F 2 "Button_Switch_SMD:SW_Push_1P1T_NO_Vertical_Wuerth_434133025816" H 6550 2650 50  0001 C CNN
F 3 "~" H 6550 2650 50  0001 C CNN
	1    6550 2450
	1    0    0    -1  
$EndComp
Wire Wire Line
	6350 2450 6050 2450
$Comp
L power:GND #PWR013
U 1 1 606819F8
P 6750 2450
F 0 "#PWR013" H 6750 2200 50  0001 C CNN
F 1 "GND" H 6755 2277 50  0000 C CNN
F 2 "" H 6750 2450 50  0001 C CNN
F 3 "" H 6750 2450 50  0001 C CNN
	1    6750 2450
	1    0    0    -1  
$EndComp
$Comp
L Regulator_Linear:AP2112K-3.3 U1
U 1 1 60686217
P 2600 1750
F 0 "U1" H 2600 2092 50  0000 C CNN
F 1 "AP2112K-3.3" H 2750 2000 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23-5" H 2600 2075 50  0001 C CNN
F 3 "https://www.diodes.com/assets/Datasheets/AP2112.pdf" H 2600 1850 50  0001 C CNN
	1    2600 1750
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C1
U 1 1 60686BDC
P 1950 1750
F 0 "C1" H 2042 1796 50  0000 L CNN
F 1 "1u" H 2042 1705 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1950 1750 50  0001 C CNN
F 3 "~" H 1950 1750 50  0001 C CNN
	1    1950 1750
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C2
U 1 1 60686DB4
P 3200 1750
F 0 "C2" H 3292 1796 50  0000 L CNN
F 1 "1u" H 3292 1705 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 3200 1750 50  0001 C CNN
F 3 "~" H 3200 1750 50  0001 C CNN
	1    3200 1750
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR06
U 1 1 6068753C
P 2600 2250
F 0 "#PWR06" H 2600 2000 50  0001 C CNN
F 1 "GND" H 2605 2077 50  0000 C CNN
F 2 "" H 2600 2250 50  0001 C CNN
F 3 "" H 2600 2250 50  0001 C CNN
	1    2600 2250
	1    0    0    -1  
$EndComp
$Comp
L power:+3V3 #PWR08
U 1 1 60687A52
P 3200 1500
F 0 "#PWR08" H 3200 1350 50  0001 C CNN
F 1 "+3V3" H 3215 1673 50  0000 C CNN
F 2 "" H 3200 1500 50  0001 C CNN
F 3 "" H 3200 1500 50  0001 C CNN
	1    3200 1500
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR05
U 1 1 60687E1A
P 1950 1500
F 0 "#PWR05" H 1950 1350 50  0001 C CNN
F 1 "+5V" H 1965 1673 50  0000 C CNN
F 2 "" H 1950 1500 50  0001 C CNN
F 3 "" H 1950 1500 50  0001 C CNN
	1    1950 1500
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 1500 1950 1650
Wire Wire Line
	2300 1650 2150 1650
Connection ~ 1950 1650
Wire Wire Line
	2900 1650 3200 1650
Wire Wire Line
	3200 1650 3200 1500
Connection ~ 3200 1650
$Comp
L Connector:TestPoint TP3
U 1 1 606891D9
P 3400 1550
F 0 "TP3" H 3458 1668 50  0000 L CNN
F 1 "TP3v3" H 3458 1577 50  0000 L CNN
F 2 "TestPoint:TestPoint_Loop_D1.80mm_Drill1.0mm_Beaded" H 3600 1550 50  0001 C CNN
F 3 "~" H 3600 1550 50  0001 C CNN
	1    3400 1550
	1    0    0    -1  
$EndComp
$Comp
L Connector:TestPoint TP1
U 1 1 60689496
P 2150 1550
F 0 "TP1" H 2208 1668 50  0000 L CNN
F 1 "TP5V" H 2208 1577 50  0000 L CNN
F 2 "TestPoint:TestPoint_Pad_D1.0mm" H 2350 1550 50  0001 C CNN
F 3 "~" H 2350 1550 50  0001 C CNN
	1    2150 1550
	1    0    0    -1  
$EndComp
$Comp
L Connector:TestPoint TP2
U 1 1 6068995D
P 2750 2200
F 0 "TP2" H 2808 2318 50  0000 L CNN
F 1 "TPGND" H 2808 2227 50  0000 L CNN
F 2 "TestPoint:TestPoint_Loop_D1.80mm_Drill1.0mm_Beaded" H 2950 2200 50  0001 C CNN
F 3 "~" H 2950 2200 50  0001 C CNN
	1    2750 2200
	1    0    0    -1  
$EndComp
Wire Wire Line
	2750 2200 2750 2250
Wire Wire Line
	2750 2250 2600 2250
Wire Wire Line
	2600 2250 2600 2050
Connection ~ 2600 2250
Wire Wire Line
	2750 2250 3200 2250
Wire Wire Line
	3200 2250 3200 1850
Connection ~ 2750 2250
Wire Wire Line
	2600 2250 1950 2250
Wire Wire Line
	1950 2250 1950 1850
Wire Wire Line
	2150 1550 2150 1650
Connection ~ 2150 1650
Wire Wire Line
	2150 1650 1950 1650
Wire Wire Line
	2300 1750 2150 1750
Wire Wire Line
	2150 1750 2150 1650
Wire Wire Line
	3400 1550 3400 1650
Wire Wire Line
	3400 1650 3200 1650
$Comp
L Device:R_Small R1
U 1 1 6068E9BD
P 4500 2300
F 0 "R1" H 4559 2346 50  0000 L CNN
F 1 "10k" H 4559 2255 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 4500 2300 50  0001 C CNN
F 3 "~" H 4500 2300 50  0001 C CNN
	1    4500 2300
	1    0    0    -1  
$EndComp
Wire Wire Line
	4500 2100 4500 2200
Wire Wire Line
	4500 2450 4500 2400
Wire Wire Line
	4500 2450 4850 2450
$Comp
L Switch:SW_Push SW1
U 1 1 6068FBA6
P 4200 2450
F 0 "SW1" H 4200 2735 50  0000 C CNN
F 1 "SW_Push" H 4200 2644 50  0000 C CNN
F 2 "Button_Switch_SMD:SW_Push_1P1T_NO_Vertical_Wuerth_434133025816" H 4200 2650 50  0001 C CNN
F 3 "~" H 4200 2650 50  0001 C CNN
	1    4200 2450
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR09
U 1 1 606900A4
P 4000 2450
F 0 "#PWR09" H 4000 2200 50  0001 C CNN
F 1 "GND" H 4005 2277 50  0000 C CNN
F 2 "" H 4000 2450 50  0001 C CNN
F 3 "" H 4000 2450 50  0001 C CNN
	1    4000 2450
	1    0    0    -1  
$EndComp
Wire Wire Line
	4400 2450 4500 2450
Connection ~ 4500 2450
NoConn ~ 4850 2650
NoConn ~ 4850 2750
Wire Wire Line
	6050 4350 6400 4350
Wire Wire Line
	6050 3650 6400 3650
Wire Wire Line
	6050 3750 6400 3750
Text Label 6400 4350 2    50   ~ 0
CH1
Text Label 6400 3650 2    50   ~ 0
CH2
Text Label 6400 3750 2    50   ~ 0
CH3
Wire Wire Line
	6050 3250 6400 3250
Text Label 6400 3050 2    50   ~ 0
MTDI
Wire Wire Line
	6050 3150 6400 3150
Text Label 6400 3150 2    50   ~ 0
MTCK
Wire Wire Line
	6400 3050 6050 3050
Text Label 6400 3250 2    50   ~ 0
MTMS
Wire Wire Line
	6050 3350 6400 3350
Text Label 6400 3350 2    50   ~ 0
MTDO
NoConn ~ 6050 2650
NoConn ~ 6050 2850
NoConn ~ 6050 2950
NoConn ~ 6050 3450
NoConn ~ 4850 3650
NoConn ~ 4850 3750
NoConn ~ 4850 3850
NoConn ~ 4850 3950
NoConn ~ 4850 4050
NoConn ~ 4850 4150
NoConn ~ 6050 3850
NoConn ~ 6050 3950
NoConn ~ 6050 4050
NoConn ~ 6050 4150
NoConn ~ 6050 4250
NoConn ~ 6050 4450
NoConn ~ 6050 4550
NoConn ~ 6050 4650
NoConn ~ 6050 4750
$Comp
L Connector:Screw_Terminal_01x02 J1
U 1 1 606A6268
P 1050 2900
F 0 "J1" H 968 3117 50  0000 C CNN
F 1 "Screw_Terminal_01x02" H 968 3026 50  0000 C CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 1050 2900 50  0001 C CNN
F 3 "~" H 1050 2900 50  0001 C CNN
	1    1050 2900
	-1   0    0    -1  
$EndComp
$Comp
L power:GND #PWR02
U 1 1 606A7252
P 1350 3000
F 0 "#PWR02" H 1350 2750 50  0001 C CNN
F 1 "GND" H 1355 2827 50  0000 C CNN
F 2 "" H 1350 3000 50  0001 C CNN
F 3 "" H 1350 3000 50  0001 C CNN
	1    1350 3000
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR01
U 1 1 606A79F3
P 1350 2900
F 0 "#PWR01" H 1350 2750 50  0001 C CNN
F 1 "+5V" H 1365 3073 50  0000 C CNN
F 2 "" H 1350 2900 50  0001 C CNN
F 3 "" H 1350 2900 50  0001 C CNN
	1    1350 2900
	1    0    0    -1  
$EndComp
Wire Wire Line
	1350 2900 1250 2900
Wire Wire Line
	1250 3000 1350 3000
$Comp
L Connector:Barrel_Jack_Switch J2
U 1 1 606A951C
P 1100 3550
F 0 "J2" H 1157 3867 50  0000 C CNN
F 1 "Barrel_Jack_Switch" H 1157 3776 50  0000 C CNN
F 2 "Connector_BarrelJack:BarrelJack_Horizontal" H 1150 3510 50  0001 C CNN
F 3 "~" H 1150 3510 50  0001 C CNN
	1    1100 3550
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR03
U 1 1 606A9DD0
P 1600 3450
F 0 "#PWR03" H 1600 3300 50  0001 C CNN
F 1 "+5V" H 1615 3623 50  0000 C CNN
F 2 "" H 1600 3450 50  0001 C CNN
F 3 "" H 1600 3450 50  0001 C CNN
	1    1600 3450
	1    0    0    -1  
$EndComp
Wire Wire Line
	1600 3450 1400 3450
$Comp
L power:GND #PWR04
U 1 1 606AAC73
P 1600 3650
F 0 "#PWR04" H 1600 3400 50  0001 C CNN
F 1 "GND" H 1605 3477 50  0000 C CNN
F 2 "" H 1600 3650 50  0001 C CNN
F 3 "" H 1600 3650 50  0001 C CNN
	1    1600 3650
	1    0    0    -1  
$EndComp
Wire Wire Line
	1600 3650 1400 3650
NoConn ~ 1400 3550
$Comp
L Connector_Generic:Conn_01x03 J3
U 1 1 606B0924
P 3500 3250
F 0 "J3" H 3580 3292 50  0000 L CNN
F 1 "Conn_01x03" H 3580 3201 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Horizontal" H 3500 3250 50  0001 C CNN
F 3 "~" H 3500 3250 50  0001 C CNN
	1    3500 3250
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR07
U 1 1 606B2B44
P 3100 3150
F 0 "#PWR07" H 3100 2900 50  0001 C CNN
F 1 "GND" V 3105 3022 50  0000 R CNN
F 2 "" H 3100 3150 50  0001 C CNN
F 3 "" H 3100 3150 50  0001 C CNN
	1    3100 3150
	0    1    1    0   
$EndComp
Wire Wire Line
	3100 3150 3300 3150
Wire Wire Line
	3300 3250 3050 3250
Wire Wire Line
	3050 3350 3300 3350
Text Label 3050 3250 0    50   ~ 0
TXD
Text Label 3050 3350 0    50   ~ 0
RXD
$Comp
L Device:Q_NMOS_GSD Q1
U 1 1 606B717F
P 8500 2100
F 0 "Q1" H 8705 2146 50  0000 L CNN
F 1 "NX3008NBK" H 8705 2055 50  0000 L CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8700 2200 50  0001 C CNN
F 3 "~" H 8500 2100 50  0001 C CNN
	1    8500 2100
	1    0    0    -1  
$EndComp
$Comp
L Device:Q_PMOS_GSD Q4
U 1 1 606B8466
P 8600 1350
F 0 "Q4" V 8942 1350 50  0000 C CNN
F 1 "PMV33UPE" V 8851 1350 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8800 1450 50  0001 C CNN
F 3 "~" H 8600 1350 50  0001 C CNN
	1    8600 1350
	0    1    -1   0   
$EndComp
$Comp
L Device:R_Small R5
U 1 1 606B9AD6
P 8250 1400
F 0 "R5" H 8309 1446 50  0000 L CNN
F 1 "1k" H 8309 1355 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 1400 50  0001 C CNN
F 3 "~" H 8250 1400 50  0001 C CNN
	1    8250 1400
	1    0    0    -1  
$EndComp
$Comp
L Device:R_Small R6
U 1 1 606B9EEC
P 8250 2350
F 0 "R6" H 8309 2396 50  0000 L CNN
F 1 "100k" H 8309 2305 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 2350 50  0001 C CNN
F 3 "~" H 8250 2350 50  0001 C CNN
	1    8250 2350
	1    0    0    -1  
$EndComp
Wire Wire Line
	8600 1550 8250 1550
Wire Wire Line
	8250 1550 8250 1500
Wire Wire Line
	8400 1250 8250 1250
Wire Wire Line
	8250 1250 8250 1300
Wire Wire Line
	8600 1550 8600 1900
Connection ~ 8600 1550
Wire Wire Line
	8300 2100 8250 2100
Wire Wire Line
	8250 2100 8250 2250
Wire Wire Line
	8600 2300 8600 2500
Wire Wire Line
	8600 2500 8250 2500
Wire Wire Line
	8250 2500 8250 2450
$Comp
L power:GND #PWR017
U 1 1 606BEA52
P 8600 2500
F 0 "#PWR017" H 8600 2250 50  0001 C CNN
F 1 "GND" H 8605 2327 50  0000 C CNN
F 2 "" H 8600 2500 50  0001 C CNN
F 3 "" H 8600 2500 50  0001 C CNN
	1    8600 2500
	1    0    0    -1  
$EndComp
Connection ~ 8600 2500
$Comp
L power:+5V #PWR014
U 1 1 606BF2C2
P 8100 1250
F 0 "#PWR014" H 8100 1100 50  0001 C CNN
F 1 "+5V" H 8115 1423 50  0000 C CNN
F 2 "" H 8100 1250 50  0001 C CNN
F 3 "" H 8100 1250 50  0001 C CNN
	1    8100 1250
	1    0    0    -1  
$EndComp
Wire Wire Line
	8100 1250 8250 1250
Connection ~ 8250 1250
Wire Wire Line
	8800 1250 9100 1250
Text Label 9100 1250 2    50   ~ 0
OUT1
$Comp
L Device:R_Small R2
U 1 1 606C356A
P 8100 2100
F 0 "R2" V 7904 2100 50  0000 C CNN
F 1 "100" V 7995 2100 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8100 2100 50  0001 C CNN
F 3 "~" H 8100 2100 50  0001 C CNN
	1    8100 2100
	0    1    1    0   
$EndComp
Wire Wire Line
	8200 2100 8250 2100
Connection ~ 8250 2100
Wire Wire Line
	8000 2100 7750 2100
Text Label 7750 2100 0    50   ~ 0
CH1
$Comp
L Device:Q_NMOS_GSD Q2
U 1 1 606CA477
P 8500 3950
F 0 "Q2" H 8705 3996 50  0000 L CNN
F 1 "NX3008NBK" H 8705 3905 50  0000 L CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8700 4050 50  0001 C CNN
F 3 "~" H 8500 3950 50  0001 C CNN
	1    8500 3950
	1    0    0    -1  
$EndComp
$Comp
L Device:Q_PMOS_GSD Q5
U 1 1 606CA47D
P 8600 3200
F 0 "Q5" V 8942 3200 50  0000 C CNN
F 1 "PMV33UPE" V 8851 3200 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8800 3300 50  0001 C CNN
F 3 "~" H 8600 3200 50  0001 C CNN
	1    8600 3200
	0    1    -1   0   
$EndComp
$Comp
L Device:R_Small R7
U 1 1 606CA483
P 8250 3250
F 0 "R7" H 8309 3296 50  0000 L CNN
F 1 "1k" H 8309 3205 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 3250 50  0001 C CNN
F 3 "~" H 8250 3250 50  0001 C CNN
	1    8250 3250
	1    0    0    -1  
$EndComp
$Comp
L Device:R_Small R8
U 1 1 606CA489
P 8250 4200
F 0 "R8" H 8309 4246 50  0000 L CNN
F 1 "100k" H 8309 4155 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 4200 50  0001 C CNN
F 3 "~" H 8250 4200 50  0001 C CNN
	1    8250 4200
	1    0    0    -1  
$EndComp
Wire Wire Line
	8600 3400 8250 3400
Wire Wire Line
	8250 3400 8250 3350
Wire Wire Line
	8400 3100 8250 3100
Wire Wire Line
	8250 3100 8250 3150
Wire Wire Line
	8600 3400 8600 3750
Connection ~ 8600 3400
Wire Wire Line
	8300 3950 8250 3950
Wire Wire Line
	8250 3950 8250 4100
Wire Wire Line
	8600 4150 8600 4350
Wire Wire Line
	8600 4350 8250 4350
Wire Wire Line
	8250 4350 8250 4300
$Comp
L power:GND #PWR018
U 1 1 606CA49A
P 8600 4350
F 0 "#PWR018" H 8600 4100 50  0001 C CNN
F 1 "GND" H 8605 4177 50  0000 C CNN
F 2 "" H 8600 4350 50  0001 C CNN
F 3 "" H 8600 4350 50  0001 C CNN
	1    8600 4350
	1    0    0    -1  
$EndComp
Connection ~ 8600 4350
$Comp
L power:+5V #PWR015
U 1 1 606CA4A1
P 8100 3100
F 0 "#PWR015" H 8100 2950 50  0001 C CNN
F 1 "+5V" H 8115 3273 50  0000 C CNN
F 2 "" H 8100 3100 50  0001 C CNN
F 3 "" H 8100 3100 50  0001 C CNN
	1    8100 3100
	1    0    0    -1  
$EndComp
Wire Wire Line
	8100 3100 8250 3100
Connection ~ 8250 3100
Wire Wire Line
	8800 3100 9100 3100
Text Label 9100 3100 2    50   ~ 0
OUT2
$Comp
L Device:R_Small R3
U 1 1 606CA4AB
P 8100 3950
F 0 "R3" V 7904 3950 50  0000 C CNN
F 1 "100" V 7995 3950 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8100 3950 50  0001 C CNN
F 3 "~" H 8100 3950 50  0001 C CNN
	1    8100 3950
	0    1    1    0   
$EndComp
Wire Wire Line
	8200 3950 8250 3950
Connection ~ 8250 3950
Wire Wire Line
	8000 3950 7750 3950
Text Label 7750 3950 0    50   ~ 0
CH2
$Comp
L Device:Q_NMOS_GSD Q3
U 1 1 606CDCDB
P 8500 5800
F 0 "Q3" H 8705 5846 50  0000 L CNN
F 1 "NX3008NBK" H 8705 5755 50  0000 L CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8700 5900 50  0001 C CNN
F 3 "~" H 8500 5800 50  0001 C CNN
	1    8500 5800
	1    0    0    -1  
$EndComp
$Comp
L Device:Q_PMOS_GSD Q6
U 1 1 606CDCE1
P 8600 5050
F 0 "Q6" V 8942 5050 50  0000 C CNN
F 1 "PMV33UPE" V 8851 5050 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23" H 8800 5150 50  0001 C CNN
F 3 "~" H 8600 5050 50  0001 C CNN
	1    8600 5050
	0    1    -1   0   
$EndComp
$Comp
L Device:R_Small R9
U 1 1 606CDCE7
P 8250 5100
F 0 "R9" H 8309 5146 50  0000 L CNN
F 1 "1k" H 8309 5055 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 5100 50  0001 C CNN
F 3 "~" H 8250 5100 50  0001 C CNN
	1    8250 5100
	1    0    0    -1  
$EndComp
$Comp
L Device:R_Small R10
U 1 1 606CDCED
P 8250 6050
F 0 "R10" H 8309 6096 50  0000 L CNN
F 1 "100k" H 8309 6005 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8250 6050 50  0001 C CNN
F 3 "~" H 8250 6050 50  0001 C CNN
	1    8250 6050
	1    0    0    -1  
$EndComp
Wire Wire Line
	8600 5250 8250 5250
Wire Wire Line
	8250 5250 8250 5200
Wire Wire Line
	8400 4950 8250 4950
Wire Wire Line
	8250 4950 8250 5000
Wire Wire Line
	8600 5250 8600 5600
Connection ~ 8600 5250
Wire Wire Line
	8300 5800 8250 5800
Wire Wire Line
	8250 5800 8250 5950
Wire Wire Line
	8600 6000 8600 6200
Wire Wire Line
	8600 6200 8250 6200
Wire Wire Line
	8250 6200 8250 6150
$Comp
L power:GND #PWR019
U 1 1 606CDCFE
P 8600 6200
F 0 "#PWR019" H 8600 5950 50  0001 C CNN
F 1 "GND" H 8605 6027 50  0000 C CNN
F 2 "" H 8600 6200 50  0001 C CNN
F 3 "" H 8600 6200 50  0001 C CNN
	1    8600 6200
	1    0    0    -1  
$EndComp
Connection ~ 8600 6200
$Comp
L power:+5V #PWR016
U 1 1 606CDD05
P 8100 4950
F 0 "#PWR016" H 8100 4800 50  0001 C CNN
F 1 "+5V" H 8115 5123 50  0000 C CNN
F 2 "" H 8100 4950 50  0001 C CNN
F 3 "" H 8100 4950 50  0001 C CNN
	1    8100 4950
	1    0    0    -1  
$EndComp
Wire Wire Line
	8100 4950 8250 4950
Connection ~ 8250 4950
Wire Wire Line
	8800 4950 9100 4950
Text Label 9100 4950 2    50   ~ 0
OUT3
$Comp
L Device:R_Small R4
U 1 1 606CDD0F
P 8100 5800
F 0 "R4" V 7904 5800 50  0000 C CNN
F 1 "100" V 7995 5800 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 8100 5800 50  0001 C CNN
F 3 "~" H 8100 5800 50  0001 C CNN
	1    8100 5800
	0    1    1    0   
$EndComp
Wire Wire Line
	8200 5800 8250 5800
Connection ~ 8250 5800
Wire Wire Line
	8000 5800 7750 5800
Text Label 7750 5800 0    50   ~ 0
CH3
$Comp
L Connector:Screw_Terminal_01x02 J4
U 1 1 606D20BC
P 9300 1250
F 0 "J4" H 9380 1242 50  0000 L CNN
F 1 "Screw_Terminal_01x02" H 9380 1151 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 9300 1250 50  0001 C CNN
F 3 "~" H 9300 1250 50  0001 C CNN
	1    9300 1250
	1    0    0    -1  
$EndComp
$Comp
L Connector:Screw_Terminal_01x02 J5
U 1 1 606D334B
P 9300 3100
F 0 "J5" H 9380 3092 50  0000 L CNN
F 1 "Screw_Terminal_01x02" H 9380 3001 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 9300 3100 50  0001 C CNN
F 3 "~" H 9300 3100 50  0001 C CNN
	1    9300 3100
	1    0    0    -1  
$EndComp
$Comp
L Connector:Screw_Terminal_01x02 J6
U 1 1 606D3D9C
P 9300 4950
F 0 "J6" H 9380 4942 50  0000 L CNN
F 1 "Screw_Terminal_01x02" H 9380 4851 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 9300 4950 50  0001 C CNN
F 3 "~" H 9300 4950 50  0001 C CNN
	1    9300 4950
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR020
U 1 1 606D5EF1
P 9100 1350
F 0 "#PWR020" H 9100 1100 50  0001 C CNN
F 1 "GND" H 9105 1177 50  0000 C CNN
F 2 "" H 9100 1350 50  0001 C CNN
F 3 "" H 9100 1350 50  0001 C CNN
	1    9100 1350
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR021
U 1 1 606D766A
P 9100 3200
F 0 "#PWR021" H 9100 2950 50  0001 C CNN
F 1 "GND" H 9105 3027 50  0000 C CNN
F 2 "" H 9100 3200 50  0001 C CNN
F 3 "" H 9100 3200 50  0001 C CNN
	1    9100 3200
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR022
U 1 1 606D858A
P 9100 5050
F 0 "#PWR022" H 9100 4800 50  0001 C CNN
F 1 "GND" H 9105 4877 50  0000 C CNN
F 2 "" H 9100 5050 50  0001 C CNN
F 3 "" H 9100 5050 50  0001 C CNN
	1    9100 5050
	1    0    0    -1  
$EndComp
Text Label 4850 2450 2    50   ~ 0
~RST
$Comp
L power:PWR_FLAG #FLG0101
U 1 1 606EF47B
P 1950 3450
F 0 "#FLG0101" H 1950 3525 50  0001 C CNN
F 1 "PWR_FLAG" H 1950 3623 50  0000 C CNN
F 2 "" H 1950 3450 50  0001 C CNN
F 3 "~" H 1950 3450 50  0001 C CNN
	1    1950 3450
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 3450 1600 3450
Connection ~ 1600 3450
$Comp
L power:PWR_FLAG #FLG0102
U 1 1 606F1C9E
P 1950 3650
F 0 "#FLG0102" H 1950 3725 50  0001 C CNN
F 1 "PWR_FLAG" H 1950 3823 50  0000 C CNN
F 2 "" H 1950 3650 50  0001 C CNN
F 3 "~" H 1950 3650 50  0001 C CNN
	1    1950 3650
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 3650 1600 3650
Connection ~ 1600 3650
$Comp
L Device:C_Small C3
U 1 1 606F6A37
P 5850 1300
F 0 "C3" H 5942 1346 50  0000 L CNN
F 1 "0.1u" H 5942 1255 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 5850 1300 50  0001 C CNN
F 3 "~" H 5850 1300 50  0001 C CNN
	1    5850 1300
	1    0    0    -1  
$EndComp
$Comp
L power:+3V3 #PWR024
U 1 1 606F7688
P 5850 1200
F 0 "#PWR024" H 5850 1050 50  0001 C CNN
F 1 "+3V3" H 5865 1373 50  0000 C CNN
F 2 "" H 5850 1200 50  0001 C CNN
F 3 "" H 5850 1200 50  0001 C CNN
	1    5850 1200
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR025
U 1 1 606F7FFF
P 5850 1400
F 0 "#PWR025" H 5850 1150 50  0001 C CNN
F 1 "GND" H 5855 1227 50  0000 C CNN
F 2 "" H 5850 1400 50  0001 C CNN
F 3 "" H 5850 1400 50  0001 C CNN
	1    5850 1400
	1    0    0    -1  
$EndComp
NoConn ~ 6400 3050
NoConn ~ 6400 3150
NoConn ~ 6400 3250
NoConn ~ 6400 3350
NoConn ~ 6050 3550
$EndSCHEMATC
