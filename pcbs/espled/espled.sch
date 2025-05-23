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
L RF_Module:ESP32-WROOM-32 U2
U 1 1 5E9CEA24
P 4750 3550
F 0 "U2" H 4300 4900 50  0000 C CNN
F 1 "ESP32-WROOM-32" H 5200 4900 50  0000 C CNN
F 2 "RF_Module:ESP32-WROOM-32" H 4750 2050 50  0001 C CNN
F 3 "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf" H 4450 3600 50  0001 C CNN
	1    4750 3550
	1    0    0    -1  
$EndComp
$Comp
L Regulator_Linear:AP2112K-3.3 U1
U 1 1 5E9CF964
P 4750 1150
F 0 "U1" H 4750 1492 50  0000 C CNN
F 1 "AP2112K-3.3" H 4750 1401 50  0000 C CNN
F 2 "Package_TO_SOT_SMD:SOT-23-5" H 4750 1475 50  0001 C CNN
F 3 "https://www.diodes.com/assets/Datasheets/AP2112.pdf" H 4750 1250 50  0001 C CNN
	1    4750 1150
	1    0    0    -1  
$EndComp
$Comp
L Connector:Barrel_Jack_Switch J2
U 1 1 5E9D12C0
P 1300 1150
F 0 "J2" H 1357 1467 50  0000 C CNN
F 1 "Barrel_Jack_Switch" H 1357 1376 50  0000 C CNN
F 2 "Connector_BarrelJack:BarrelJack_Horizontal" H 1350 1110 50  0001 C CNN
F 3 "~" H 1350 1110 50  0001 C CNN
	1    1300 1150
	1    0    0    -1  
$EndComp
$Comp
L Connector:Screw_Terminal_01x02 J1
U 1 1 5E9D1C9D
P 1150 1800
F 0 "J1" H 1068 1475 50  0000 C CNN
F 1 "Screw_Terminal_01x02" H 1068 1566 50  0000 C CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 1150 1800 50  0001 C CNN
F 3 "~" H 1150 1800 50  0001 C CNN
	1    1150 1800
	-1   0    0    1   
$EndComp
$Comp
L power:VCC #PWR08
U 1 1 5E9D21E0
P 2050 900
F 0 "#PWR08" H 2050 750 50  0001 C CNN
F 1 "VCC" H 2067 1073 50  0000 C CNN
F 2 "" H 2050 900 50  0001 C CNN
F 3 "" H 2050 900 50  0001 C CNN
	1    2050 900 
	1    0    0    -1  
$EndComp
Wire Wire Line
	2050 900  2050 1050
Wire Wire Line
	2050 1050 1600 1050
$Comp
L power:GND #PWR09
U 1 1 5E9D2A87
P 2050 1350
F 0 "#PWR09" H 2050 1100 50  0001 C CNN
F 1 "GND" H 2055 1177 50  0000 C CNN
F 2 "" H 2050 1350 50  0001 C CNN
F 3 "" H 2050 1350 50  0001 C CNN
	1    2050 1350
	1    0    0    -1  
$EndComp
Wire Wire Line
	2050 1250 1600 1250
Wire Wire Line
	2050 1350 2050 1250
NoConn ~ 1600 1150
$Comp
L power:VCC #PWR03
U 1 1 5E9D4AB1
P 1800 1700
F 0 "#PWR03" H 1800 1550 50  0001 C CNN
F 1 "VCC" H 1817 1873 50  0000 C CNN
F 2 "" H 1800 1700 50  0001 C CNN
F 3 "" H 1800 1700 50  0001 C CNN
	1    1800 1700
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR04
U 1 1 5E9D4E7F
P 1800 1850
F 0 "#PWR04" H 1800 1600 50  0001 C CNN
F 1 "GND" H 1805 1677 50  0000 C CNN
F 2 "" H 1800 1850 50  0001 C CNN
F 3 "" H 1800 1850 50  0001 C CNN
	1    1800 1850
	1    0    0    -1  
$EndComp
Wire Wire Line
	1350 1800 1800 1800
Wire Wire Line
	1800 1800 1800 1850
Wire Wire Line
	1800 1700 1350 1700
$Comp
L power:VCC #PWR012
U 1 1 5E9D6636
P 3100 900
F 0 "#PWR012" H 3100 750 50  0001 C CNN
F 1 "VCC" H 3117 1073 50  0000 C CNN
F 2 "" H 3100 900 50  0001 C CNN
F 3 "" H 3100 900 50  0001 C CNN
	1    3100 900 
	1    0    0    -1  
$EndComp
Wire Wire Line
	4450 1150 4300 1150
Wire Wire Line
	4300 1150 4300 1050
Connection ~ 4300 1050
Wire Wire Line
	4300 1050 4450 1050
$Comp
L power:GND #PWR013
U 1 1 5E9D6F4F
P 4750 1550
F 0 "#PWR013" H 4750 1300 50  0001 C CNN
F 1 "GND" H 4755 1377 50  0000 C CNN
F 2 "" H 4750 1550 50  0001 C CNN
F 3 "" H 4750 1550 50  0001 C CNN
	1    4750 1550
	1    0    0    -1  
$EndComp
Wire Wire Line
	4750 1550 4750 1500
$Comp
L power:+3V3 #PWR016
U 1 1 5E9D7760
P 5200 900
F 0 "#PWR016" H 5200 750 50  0001 C CNN
F 1 "+3V3" H 5215 1073 50  0000 C CNN
F 2 "" H 5200 900 50  0001 C CNN
F 3 "" H 5200 900 50  0001 C CNN
	1    5200 900 
	1    0    0    -1  
$EndComp
Wire Wire Line
	5200 900  5200 1050
Wire Wire Line
	5200 1050 5050 1050
Wire Wire Line
	5350 2350 5800 2350
Text Label 5800 2350 2    50   ~ 0
BOOTMODE
$Comp
L Device:R_Small R5
U 1 1 5E9DB749
P 6000 2650
F 0 "R5" H 6059 2696 50  0000 L CNN
F 1 "1k" H 6059 2605 50  0000 L CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 6000 2650 50  0001 C CNN
F 3 "~" H 6000 2650 50  0001 C CNN
	1    6000 2650
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR015
U 1 1 5E9DBB48
P 4750 5050
F 0 "#PWR015" H 4750 4800 50  0001 C CNN
F 1 "GND" H 4755 4877 50  0000 C CNN
F 2 "" H 4750 5050 50  0001 C CNN
F 3 "" H 4750 5050 50  0001 C CNN
	1    4750 5050
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR017
U 1 1 5E9DBE99
P 6000 3250
F 0 "#PWR017" H 6000 3000 50  0001 C CNN
F 1 "GND" H 6005 3077 50  0000 C CNN
F 2 "" H 6000 3250 50  0001 C CNN
F 3 "" H 6000 3250 50  0001 C CNN
	1    6000 3250
	1    0    0    -1  
$EndComp
$Comp
L Switch:SW_Push SW1
U 1 1 5E9DD33E
P 1550 2550
F 0 "SW1" H 1550 2835 50  0000 C CNN
F 1 "SW_Push" H 1550 2744 50  0000 C CNN
F 2 "Button_Switch_SMD:SW_SPST_SKQG_WithStem" H 1550 2750 50  0001 C CNN
F 3 "~" H 1550 2750 50  0001 C CNN
	1    1550 2550
	1    0    0    -1  
$EndComp
$Comp
L Switch:SW_Push SW2
U 1 1 5E9DD839
P 1550 3200
F 0 "SW2" H 1550 3485 50  0000 C CNN
F 1 "SW_Push" H 1550 3394 50  0000 C CNN
F 2 "Button_Switch_SMD:SW_SPST_SKQG_WithStem" H 1550 3400 50  0001 C CNN
F 3 "~" H 1550 3400 50  0001 C CNN
	1    1550 3200
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C1
U 1 1 5E9DF870
P 1950 2700
F 0 "C1" H 2042 2746 50  0000 L CNN
F 1 "0.1u" H 2042 2655 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1950 2700 50  0001 C CNN
F 3 "~" H 1950 2700 50  0001 C CNN
	1    1950 2700
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C2
U 1 1 5E9DFCF1
P 1950 3400
F 0 "C2" H 2042 3446 50  0000 L CNN
F 1 "0.1u" H 2042 3355 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 1950 3400 50  0001 C CNN
F 3 "~" H 1950 3400 50  0001 C CNN
	1    1950 3400
	1    0    0    -1  
$EndComp
Wire Wire Line
	1750 3200 1950 3200
Wire Wire Line
	1950 3200 1950 3300
Wire Wire Line
	1950 2600 1950 2550
Wire Wire Line
	1950 2550 1750 2550
$Comp
L power:GND #PWR06
U 1 1 5E9E0865
P 1950 2800
F 0 "#PWR06" H 1950 2550 50  0001 C CNN
F 1 "GND" H 1955 2627 50  0000 C CNN
F 2 "" H 1950 2800 50  0001 C CNN
F 3 "" H 1950 2800 50  0001 C CNN
	1    1950 2800
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR07
U 1 1 5E9E0C1F
P 1950 3500
F 0 "#PWR07" H 1950 3250 50  0001 C CNN
F 1 "GND" H 1955 3327 50  0000 C CNN
F 2 "" H 1950 3500 50  0001 C CNN
F 3 "" H 1950 3500 50  0001 C CNN
	1    1950 3500
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR02
U 1 1 5E9E25B6
P 950 3350
F 0 "#PWR02" H 950 3100 50  0001 C CNN
F 1 "GND" H 955 3177 50  0000 C CNN
F 2 "" H 950 3350 50  0001 C CNN
F 3 "" H 950 3350 50  0001 C CNN
	1    950  3350
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR01
U 1 1 5E9E29A4
P 950 2700
F 0 "#PWR01" H 950 2450 50  0001 C CNN
F 1 "GND" H 955 2527 50  0000 C CNN
F 2 "" H 950 2700 50  0001 C CNN
F 3 "" H 950 2700 50  0001 C CNN
	1    950  2700
	1    0    0    -1  
$EndComp
Wire Wire Line
	950  2700 950  2550
Wire Wire Line
	950  3200 950  3350
Wire Wire Line
	1950 2550 2250 2550
Connection ~ 1950 2550
Wire Wire Line
	1950 3200 2250 3200
Connection ~ 1950 3200
Text Label 2250 2550 2    50   ~ 0
EN
Text Label 2250 3200 2    50   ~ 0
BOOTMODE
Wire Wire Line
	4150 2350 3700 2350
Text Label 3700 2350 0    50   ~ 0
EN
NoConn ~ 4150 2550
NoConn ~ 4150 2650
Wire Wire Line
	5350 2450 5800 2450
Text Label 5800 2450 2    50   ~ 0
TXD
Text Label 5800 2650 2    50   ~ 0
RXD
Wire Wire Line
	4750 4950 4750 5050
$Comp
L power:+3V3 #PWR014
U 1 1 5E9E8DE5
P 4750 2050
F 0 "#PWR014" H 4750 1900 50  0001 C CNN
F 1 "+3V3" H 4765 2223 50  0000 C CNN
F 2 "" H 4750 2050 50  0001 C CNN
F 3 "" H 4750 2050 50  0001 C CNN
	1    4750 2050
	1    0    0    -1  
$EndComp
Wire Wire Line
	4750 2050 4750 2150
$Comp
L Device:C_Small C9
U 1 1 5E9E9C1E
P 4000 1150
F 0 "C9" H 4092 1196 50  0000 L CNN
F 1 "1u" H 4092 1105 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 4000 1150 50  0001 C CNN
F 3 "~" H 4000 1150 50  0001 C CNN
	1    4000 1150
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C10
U 1 1 5E9EA034
P 5200 1150
F 0 "C10" H 5292 1196 50  0000 L CNN
F 1 "1u" H 5292 1105 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 5200 1150 50  0001 C CNN
F 3 "~" H 5200 1150 50  0001 C CNN
	1    5200 1150
	1    0    0    -1  
$EndComp
Connection ~ 5200 1050
Connection ~ 4750 1500
Wire Wire Line
	4750 1500 4750 1450
Wire Wire Line
	5200 1250 5200 1500
Wire Wire Line
	5200 1500 4750 1500
Wire Wire Line
	3100 1050 3100 900 
$Comp
L Device:C_Small C8
U 1 1 5E9F1A8D
P 3700 1150
F 0 "C8" H 3792 1196 50  0000 L CNN
F 1 "10u" H 3792 1105 50  0000 L CNN
F 2 "Capacitor_SMD:C_0805_2012Metric" H 3700 1150 50  0001 C CNN
F 3 "~" H 3700 1150 50  0001 C CNN
	1    3700 1150
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C6
U 1 1 5E9F1E16
P 3400 1150
F 0 "C6" H 3492 1196 50  0000 L CNN
F 1 "10u" H 3492 1105 50  0000 L CNN
F 2 "Capacitor_SMD:C_0805_2012Metric" H 3400 1150 50  0001 C CNN
F 3 "~" H 3400 1150 50  0001 C CNN
	1    3400 1150
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C4
U 1 1 5E9F217A
P 3100 1150
F 0 "C4" H 3192 1196 50  0000 L CNN
F 1 "10u" H 3192 1105 50  0000 L CNN
F 2 "Capacitor_SMD:C_0805_2012Metric" H 3100 1150 50  0001 C CNN
F 3 "~" H 3100 1150 50  0001 C CNN
	1    3100 1150
	1    0    0    -1  
$EndComp
Connection ~ 3100 1050
Connection ~ 3400 1050
Wire Wire Line
	3400 1050 3100 1050
Wire Wire Line
	3400 1050 3700 1050
Connection ~ 3700 1050
Connection ~ 4000 1050
Wire Wire Line
	3700 1050 4000 1050
Wire Wire Line
	4000 1050 4300 1050
Wire Wire Line
	4000 1250 4000 1500
Wire Wire Line
	4000 1500 4750 1500
Wire Wire Line
	4000 1500 3700 1500
Wire Wire Line
	3100 1500 3100 1250
Connection ~ 4000 1500
Wire Wire Line
	3400 1250 3400 1500
Connection ~ 3400 1500
Wire Wire Line
	3400 1500 3100 1500
Wire Wire Line
	3700 1250 3700 1500
Connection ~ 3700 1500
Wire Wire Line
	3700 1500 3400 1500
$Comp
L power:+3V3 #PWR010
U 1 1 5E9FAABD
P 2900 1800
F 0 "#PWR010" H 2900 1650 50  0001 C CNN
F 1 "+3V3" H 2915 1973 50  0000 C CNN
F 2 "" H 2900 1800 50  0001 C CNN
F 3 "" H 2900 1800 50  0001 C CNN
	1    2900 1800
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR011
U 1 1 5E9FB0A9
P 2900 2150
F 0 "#PWR011" H 2900 1900 50  0001 C CNN
F 1 "GND" H 2905 1977 50  0000 C CNN
F 2 "" H 2900 2150 50  0001 C CNN
F 3 "" H 2900 2150 50  0001 C CNN
	1    2900 2150
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C5
U 1 1 5E9FBA70
P 3250 2000
F 0 "C5" H 3342 2046 50  0000 L CNN
F 1 "1u" H 3342 1955 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 3250 2000 50  0001 C CNN
F 3 "~" H 3250 2000 50  0001 C CNN
	1    3250 2000
	1    0    0    -1  
$EndComp
$Comp
L Device:C_Small C7
U 1 1 5E9FBF71
P 3550 2000
F 0 "C7" H 3642 2046 50  0000 L CNN
F 1 "0.1u" H 3642 1955 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 3550 2000 50  0001 C CNN
F 3 "~" H 3550 2000 50  0001 C CNN
	1    3550 2000
	1    0    0    -1  
$EndComp
Wire Wire Line
	2900 2100 2900 2150
$Comp
L Device:C_Small C3
U 1 1 5E9FB4E1
P 2900 2000
F 0 "C3" H 2992 2046 50  0000 L CNN
F 1 "10u" H 2992 1955 50  0000 L CNN
F 2 "Capacitor_SMD:C_0805_2012Metric" H 2900 2000 50  0001 C CNN
F 3 "~" H 2900 2000 50  0001 C CNN
	1    2900 2000
	1    0    0    -1  
$EndComp
Wire Wire Line
	2900 1800 2900 1900
Wire Wire Line
	2900 1900 3250 1900
Connection ~ 2900 1900
Wire Wire Line
	3550 1900 3250 1900
Connection ~ 3250 1900
Wire Wire Line
	3550 2100 3250 2100
Wire Wire Line
	3250 2100 2900 2100
Connection ~ 3250 2100
Connection ~ 2900 2100
$Comp
L Device:R_Small R3
U 1 1 5EA05C16
P 1950 2350
F 0 "R3" H 1891 2304 50  0000 R CNN
F 1 "10k" H 1891 2395 50  0000 R CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 1950 2350 50  0001 C CNN
F 3 "~" H 1950 2350 50  0001 C CNN
	1    1950 2350
	-1   0    0    1   
$EndComp
$Comp
L power:+3V3 #PWR05
U 1 1 5EA063C7
P 1950 2200
F 0 "#PWR05" H 1950 2050 50  0001 C CNN
F 1 "+3V3" H 1965 2373 50  0000 C CNN
F 2 "" H 1950 2200 50  0001 C CNN
F 3 "" H 1950 2200 50  0001 C CNN
	1    1950 2200
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 2200 1950 2250
Wire Wire Line
	1950 2450 1950 2550
$Comp
L Device:LED D2
U 1 1 5EA14565
P 6000 3000
F 0 "D2" V 6039 2883 50  0000 R CNN
F 1 "LED" V 5948 2883 50  0000 R CNN
F 2 "LED_SMD:LED_0603_1608Metric_Castellated" H 6000 3000 50  0001 C CNN
F 3 "~" H 6000 3000 50  0001 C CNN
	1    6000 3000
	0    -1   -1   0   
$EndComp
Wire Wire Line
	6000 3250 6000 3150
Wire Wire Line
	6000 2850 6000 2750
Wire Wire Line
	5350 2550 6000 2550
Wire Wire Line
	5350 2650 5800 2650
$Comp
L Device:R_Small R1
U 1 1 5EA1F32F
P 1150 2550
F 0 "R1" V 1346 2550 50  0000 C CNN
F 1 "1k" V 1255 2550 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 1150 2550 50  0001 C CNN
F 3 "~" H 1150 2550 50  0001 C CNN
	1    1150 2550
	0    -1   -1   0   
$EndComp
$Comp
L Device:R_Small R2
U 1 1 5EA1F8E6
P 1150 3200
F 0 "R2" V 1346 3200 50  0000 C CNN
F 1 "1k" V 1255 3200 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 1150 3200 50  0001 C CNN
F 3 "~" H 1150 3200 50  0001 C CNN
	1    1150 3200
	0    -1   -1   0   
$EndComp
Wire Wire Line
	1250 2550 1350 2550
Wire Wire Line
	1050 2550 950  2550
Wire Wire Line
	1050 3200 950  3200
Wire Wire Line
	1250 3200 1350 3200
$Comp
L 74xx:74HC245 U3
U 1 1 5EA261B4
P 7950 3450
F 0 "U3" H 7700 4100 50  0000 C CNN
F 1 "74HCT245" H 8200 4100 50  0000 C CNN
F 2 "Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm" H 7950 3450 50  0001 C CNN
F 3 "http://www.ti.com/lit/gpn/sn74HC245" H 7950 3450 50  0001 C CNN
	1    7950 3450
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR023
U 1 1 5EA276ED
P 7950 2450
F 0 "#PWR023" H 7950 2300 50  0001 C CNN
F 1 "VCC" H 7967 2623 50  0000 C CNN
F 2 "" H 7950 2450 50  0001 C CNN
F 3 "" H 7950 2450 50  0001 C CNN
	1    7950 2450
	1    0    0    -1  
$EndComp
Wire Wire Line
	7950 2450 7950 2650
$Comp
L power:GND #PWR024
U 1 1 5EA28C70
P 7950 4350
F 0 "#PWR024" H 7950 4100 50  0001 C CNN
F 1 "GND" H 7955 4177 50  0000 C CNN
F 2 "" H 7950 4350 50  0001 C CNN
F 3 "" H 7950 4350 50  0001 C CNN
	1    7950 4350
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR022
U 1 1 5EA2906E
P 7250 4150
F 0 "#PWR022" H 7250 3900 50  0001 C CNN
F 1 "GND" H 7255 3977 50  0000 C CNN
F 2 "" H 7250 4150 50  0001 C CNN
F 3 "" H 7250 4150 50  0001 C CNN
	1    7250 4150
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR021
U 1 1 5EA2C30B
P 7250 3850
F 0 "#PWR021" H 7250 3700 50  0001 C CNN
F 1 "VCC" H 7267 4023 50  0000 C CNN
F 2 "" H 7250 3850 50  0001 C CNN
F 3 "" H 7250 3850 50  0001 C CNN
	1    7250 3850
	1    0    0    -1  
$EndComp
Wire Wire Line
	7250 3850 7450 3850
Wire Wire Line
	7250 3950 7250 4150
Wire Wire Line
	7250 3950 7450 3950
$Comp
L Device:R_Small R4
U 1 1 5EA36360
P 5550 1050
F 0 "R4" V 5354 1050 50  0000 C CNN
F 1 "1k" V 5445 1050 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 5550 1050 50  0001 C CNN
F 3 "~" H 5550 1050 50  0001 C CNN
	1    5550 1050
	0    1    1    0   
$EndComp
$Comp
L Device:LED D1
U 1 1 5EA36996
P 5650 1300
F 0 "D1" V 5689 1183 50  0000 R CNN
F 1 "LED" V 5598 1183 50  0000 R CNN
F 2 "LED_SMD:LED_0603_1608Metric_Castellated" H 5650 1300 50  0001 C CNN
F 3 "~" H 5650 1300 50  0001 C CNN
	1    5650 1300
	0    -1   -1   0   
$EndComp
Wire Wire Line
	5650 1450 5650 1500
Wire Wire Line
	5650 1500 5200 1500
Connection ~ 5200 1500
Wire Wire Line
	5200 1050 5450 1050
Wire Wire Line
	5650 1050 5650 1150
$Comp
L Device:C_Small C11
U 1 1 5EA4056E
P 6850 2450
F 0 "C11" H 6942 2496 50  0000 L CNN
F 1 "0.1u" H 6942 2405 50  0000 L CNN
F 2 "Capacitor_SMD:C_0603_1608Metric" H 6850 2450 50  0001 C CNN
F 3 "~" H 6850 2450 50  0001 C CNN
	1    6850 2450
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR018
U 1 1 5EA415F7
P 6850 2350
F 0 "#PWR018" H 6850 2200 50  0001 C CNN
F 1 "VCC" H 6867 2523 50  0000 C CNN
F 2 "" H 6850 2350 50  0001 C CNN
F 3 "" H 6850 2350 50  0001 C CNN
	1    6850 2350
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR019
U 1 1 5EA42EEC
P 6850 2550
F 0 "#PWR019" H 6850 2300 50  0001 C CNN
F 1 "GND" H 6855 2377 50  0000 C CNN
F 2 "" H 6850 2550 50  0001 C CNN
F 3 "" H 6850 2550 50  0001 C CNN
	1    6850 2550
	1    0    0    -1  
$EndComp
$Comp
L Device:R_Small R6
U 1 1 5EA435CA
P 9700 1650
F 0 "R6" V 9504 1650 50  0000 C CNN
F 1 "330" V 9595 1650 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 9700 1650 50  0001 C CNN
F 3 "~" H 9700 1650 50  0001 C CNN
	1    9700 1650
	0    1    1    0   
$EndComp
$Comp
L Device:R_Small R7
U 1 1 5EA43BD3
P 9700 2400
F 0 "R7" V 9504 2400 50  0000 C CNN
F 1 "330" V 9595 2400 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 9700 2400 50  0001 C CNN
F 3 "~" H 9700 2400 50  0001 C CNN
	1    9700 2400
	0    1    1    0   
$EndComp
$Comp
L Device:R_Small R8
U 1 1 5EA43F48
P 9700 3150
F 0 "R8" V 9504 3150 50  0000 C CNN
F 1 "330" V 9595 3150 50  0000 C CNN
F 2 "Resistor_SMD:R_0603_1608Metric" H 9700 3150 50  0001 C CNN
F 3 "~" H 9700 3150 50  0001 C CNN
	1    9700 3150
	0    1    1    0   
$EndComp
NoConn ~ 8450 3350
NoConn ~ 8450 3450
NoConn ~ 8450 3550
NoConn ~ 8450 3650
$Comp
L power:GND #PWR020
U 1 1 5EA4940A
P 6950 3700
F 0 "#PWR020" H 6950 3450 50  0001 C CNN
F 1 "GND" H 6955 3527 50  0000 C CNN
F 2 "" H 6950 3700 50  0001 C CNN
F 3 "" H 6950 3700 50  0001 C CNN
	1    6950 3700
	1    0    0    -1  
$EndComp
Wire Wire Line
	7450 3650 6950 3650
Wire Wire Line
	6950 3650 6950 3700
Wire Wire Line
	7450 3550 6950 3550
Wire Wire Line
	6950 3550 6950 3650
Connection ~ 6950 3650
Wire Wire Line
	7450 3450 6950 3450
Wire Wire Line
	6950 3450 6950 3550
Connection ~ 6950 3550
Wire Wire Line
	7450 3350 6950 3350
Wire Wire Line
	6950 3350 6950 3450
Connection ~ 6950 3450
Wire Wire Line
	7450 2950 6950 2950
Wire Wire Line
	7450 3050 6950 3050
Wire Wire Line
	7450 3150 6950 3150
Wire Wire Line
	7450 3250 6950 3250
$Comp
L Connector:Screw_Terminal_01x03 J3
U 1 1 5EA5F5BA
P 10200 1650
F 0 "J3" H 10280 1692 50  0000 L CNN
F 1 "Screw_Terminal_01x03" H 10280 1601 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-3-5.0-H_1x03_P5.00mm_Horizontal" H 10200 1650 50  0001 C CNN
F 3 "~" H 10200 1650 50  0001 C CNN
	1    10200 1650
	1    0    0    -1  
$EndComp
$Comp
L Connector:Screw_Terminal_01x03 J4
U 1 1 5EA60314
P 10200 2400
F 0 "J4" H 10280 2442 50  0000 L CNN
F 1 "Screw_Terminal_01x03" H 10280 2351 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-3-5.0-H_1x03_P5.00mm_Horizontal" H 10200 2400 50  0001 C CNN
F 3 "~" H 10200 2400 50  0001 C CNN
	1    10200 2400
	1    0    0    -1  
$EndComp
$Comp
L Connector:Screw_Terminal_01x03 J5
U 1 1 5EA60CB0
P 10200 3150
F 0 "J5" H 10280 3192 50  0000 L CNN
F 1 "Screw_Terminal_01x03" H 10280 3101 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-3-5.0-H_1x03_P5.00mm_Horizontal" H 10200 3150 50  0001 C CNN
F 3 "~" H 10200 3150 50  0001 C CNN
	1    10200 3150
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR026
U 1 1 5EA6E45F
P 9900 1450
F 0 "#PWR026" H 9900 1300 50  0001 C CNN
F 1 "VCC" H 9917 1623 50  0000 C CNN
F 2 "" H 9900 1450 50  0001 C CNN
F 3 "" H 9900 1450 50  0001 C CNN
	1    9900 1450
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR027
U 1 1 5EA84A03
P 9900 2200
F 0 "#PWR027" H 9900 2050 50  0001 C CNN
F 1 "VCC" H 9917 2373 50  0000 C CNN
F 2 "" H 9900 2200 50  0001 C CNN
F 3 "" H 9900 2200 50  0001 C CNN
	1    9900 2200
	1    0    0    -1  
$EndComp
$Comp
L power:VCC #PWR028
U 1 1 5EA86FF6
P 9900 2950
F 0 "#PWR028" H 9900 2800 50  0001 C CNN
F 1 "VCC" H 9917 3123 50  0000 C CNN
F 2 "" H 9900 2950 50  0001 C CNN
F 3 "" H 9900 2950 50  0001 C CNN
	1    9900 2950
	1    0    0    -1  
$EndComp
Wire Wire Line
	10000 1550 9900 1550
Wire Wire Line
	9900 1550 9900 1450
Wire Wire Line
	10000 2300 9900 2300
Wire Wire Line
	9900 2300 9900 2200
Wire Wire Line
	10000 3050 9900 3050
Wire Wire Line
	9900 3050 9900 2950
Wire Wire Line
	10000 3150 9800 3150
Wire Wire Line
	10000 2400 9800 2400
Wire Wire Line
	10000 1650 9800 1650
Wire Wire Line
	9600 1650 9300 1650
Wire Wire Line
	9600 2400 9300 2400
Wire Wire Line
	9600 3150 9300 3150
Wire Wire Line
	8450 2950 8750 2950
Wire Wire Line
	8450 3050 8750 3050
Wire Wire Line
	8750 3150 8450 3150
Text Label 8750 2950 2    50   ~ 0
CH1
Text Label 8750 3050 2    50   ~ 0
CH2
Text Label 8750 3150 2    50   ~ 0
CH3
Text Label 9300 1650 0    50   ~ 0
CH1
Text Label 9300 2400 0    50   ~ 0
CH2
Text Label 9300 3150 0    50   ~ 0
CH3
NoConn ~ 4150 3550
NoConn ~ 4150 3650
NoConn ~ 4150 3750
NoConn ~ 4150 3850
NoConn ~ 4150 3950
NoConn ~ 4150 4050
NoConn ~ 5350 2850
NoConn ~ 5350 3150
NoConn ~ 5350 3250
NoConn ~ 5350 2950
NoConn ~ 5350 2750
NoConn ~ 5350 3050
Wire Wire Line
	5350 3350 5800 3350
Wire Wire Line
	5350 3450 5800 3450
Wire Wire Line
	5350 3550 5800 3550
NoConn ~ 5350 3750
NoConn ~ 5350 3850
NoConn ~ 5350 3950
NoConn ~ 5350 4050
NoConn ~ 5350 4150
NoConn ~ 5350 4250
NoConn ~ 5350 4350
NoConn ~ 5350 4450
NoConn ~ 5350 4550
NoConn ~ 5350 4650
Text Label 5800 3350 2    50   ~ 0
IO16
Text Label 5800 3450 2    50   ~ 0
IO17
Text Label 5800 3550 2    50   ~ 0
IO18
Text Label 6950 2950 0    50   ~ 0
IO16
Text Label 6950 3050 0    50   ~ 0
IO17
Text Label 6950 3150 0    50   ~ 0
IO18
$Comp
L Connector_Generic:Conn_01x03 J7
U 1 1 5EAF4988
P 10200 4600
F 0 "J7" H 10280 4642 50  0000 L CNN
F 1 "Conn_01x03" H 10280 4551 50  0000 L CNN
F 2 "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Horizontal" H 10200 4600 50  0001 C CNN
F 3 "~" H 10200 4600 50  0001 C CNN
	1    10200 4600
	1    0    0    -1  
$EndComp
Wire Wire Line
	10000 4500 9700 4500
Wire Wire Line
	9700 4600 10000 4600
Wire Wire Line
	10000 4700 9700 4700
$Comp
L power:GND #PWR025
U 1 1 5EAFDF8E
P 9700 4850
F 0 "#PWR025" H 9700 4600 50  0001 C CNN
F 1 "GND" H 9705 4677 50  0000 C CNN
F 2 "" H 9700 4850 50  0001 C CNN
F 3 "" H 9700 4850 50  0001 C CNN
	1    9700 4850
	1    0    0    -1  
$EndComp
Wire Wire Line
	7950 4250 7950 4350
Wire Wire Line
	9700 4700 9700 4850
Text Label 9700 4500 0    50   ~ 0
TXD
Text Label 9700 4600 0    50   ~ 0
RXD
$Comp
L power:GND #PWR030
U 1 1 5EB06328
P 9900 1750
F 0 "#PWR030" H 9900 1500 50  0001 C CNN
F 1 "GND" H 9905 1577 50  0000 C CNN
F 2 "" H 9900 1750 50  0001 C CNN
F 3 "" H 9900 1750 50  0001 C CNN
	1    9900 1750
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR031
U 1 1 5EB091EE
P 9900 2500
F 0 "#PWR031" H 9900 2250 50  0001 C CNN
F 1 "GND" H 9905 2327 50  0000 C CNN
F 2 "" H 9900 2500 50  0001 C CNN
F 3 "" H 9900 2500 50  0001 C CNN
	1    9900 2500
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR032
U 1 1 5EB097E3
P 9900 3250
F 0 "#PWR032" H 9900 3000 50  0001 C CNN
F 1 "GND" H 9905 3077 50  0000 C CNN
F 2 "" H 9900 3250 50  0001 C CNN
F 3 "" H 9900 3250 50  0001 C CNN
	1    9900 3250
	1    0    0    -1  
$EndComp
Wire Wire Line
	10000 3250 9900 3250
Wire Wire Line
	10000 2500 9900 2500
Wire Wire Line
	10000 1750 9900 1750
NoConn ~ 8450 3250
NoConn ~ 5350 3650
Wire Wire Line
	6950 3250 6950 3350
Connection ~ 6950 3350
$EndSCHEMATC
