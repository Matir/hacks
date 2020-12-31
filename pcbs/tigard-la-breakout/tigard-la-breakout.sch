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
L Connector_Generic:Conn_02x05_Odd_Even J2
U 1 1 5FDFFF50
P 2650 1100
F 0 "J2" H 2700 1517 50  0000 C CNN
F 1 "FX2" H 2700 1426 50  0000 C CNN
F 2 "Matir:PinHeader_2x05_P2.54mm_Both" H 2650 1100 50  0001 C CNN
F 3 "~" H 2650 1100 50  0001 C CNN
	1    2650 1100
	1    0    0    -1  
$EndComp
$Comp
L Connector_Generic:Conn_02x08_Odd_Even J3
U 1 1 5FE009E0
P 3900 1200
F 0 "J3" H 3950 1717 50  0000 C CNN
F 1 "Saleae" H 3950 1626 50  0000 C CNN
F 2 "Matir:PinHeader_2x08_P2.54mm_Both" H 3900 1200 50  0001 C CNN
F 3 "~" H 3900 1200 50  0001 C CNN
	1    3900 1200
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR03
U 1 1 5FE023E1
P 4200 1800
F 0 "#PWR03" H 4200 1550 50  0001 C CNN
F 1 "GND" H 4205 1627 50  0000 C CNN
F 2 "" H 4200 1800 50  0001 C CNN
F 3 "" H 4200 1800 50  0001 C CNN
	1    4200 1800
	1    0    0    -1  
$EndComp
Wire Wire Line
	4200 1800 4200 1600
Wire Wire Line
	4200 1600 4200 1500
Connection ~ 4200 1600
Wire Wire Line
	4200 1500 4200 1400
Connection ~ 4200 1500
Wire Wire Line
	4200 1400 4200 1300
Connection ~ 4200 1400
Wire Wire Line
	4200 1200 4200 1300
Connection ~ 4200 1300
Wire Wire Line
	4200 1200 4200 1100
Connection ~ 4200 1200
Wire Wire Line
	4200 1100 4200 1000
Connection ~ 4200 1100
Wire Wire Line
	4200 1000 4200 900 
Connection ~ 4200 1000
NoConn ~ 1050 1400
NoConn ~ 1050 1500
NoConn ~ 1550 1500
NoConn ~ 1550 1400
$Comp
L power:GND #PWR01
U 1 1 5FE04377
P 1650 1750
F 0 "#PWR01" H 1650 1500 50  0001 C CNN
F 1 "GND" H 1655 1577 50  0000 C CNN
F 2 "" H 1650 1750 50  0001 C CNN
F 3 "" H 1650 1750 50  0001 C CNN
	1    1650 1750
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR02
U 1 1 5FE04695
P 2950 1500
F 0 "#PWR02" H 2950 1250 50  0001 C CNN
F 1 "GND" H 2955 1327 50  0000 C CNN
F 2 "" H 2950 1500 50  0001 C CNN
F 3 "" H 2950 1500 50  0001 C CNN
	1    2950 1500
	1    0    0    -1  
$EndComp
Wire Wire Line
	2950 1300 2950 1450
Wire Wire Line
	2450 1300 2450 1450
Wire Wire Line
	2450 1450 2950 1450
Connection ~ 2950 1450
Wire Wire Line
	2950 1450 2950 1500
Wire Wire Line
	1550 1300 1650 1300
Wire Wire Line
	1650 1300 1650 1600
Wire Wire Line
	1050 1300 950  1300
Wire Wire Line
	950  1300 950  1600
Wire Wire Line
	950  1600 1650 1600
Connection ~ 1650 1600
Wire Wire Line
	1650 1600 1650 1750
Wire Wire Line
	1050 1200 850  1200
Wire Wire Line
	1050 1100 850  1100
Wire Wire Line
	1050 1000 850  1000
Wire Wire Line
	1050 900  850  900 
Wire Wire Line
	1750 900  1550 900 
Wire Wire Line
	1750 1000 1550 1000
Wire Wire Line
	1750 1100 1550 1100
Wire Wire Line
	1750 1200 1550 1200
Text Label 1750 1200 2    50   ~ 0
CH7
Text Label 1750 1100 2    50   ~ 0
CH5
Text Label 1750 1000 2    50   ~ 0
CH3
Text Label 1750 900  2    50   ~ 0
CH1
Text Label 850  1200 0    50   ~ 0
CH6
Text Label 850  1100 0    50   ~ 0
CH4
Text Label 850  1000 0    50   ~ 0
CH2
Text Label 850  900  0    50   ~ 0
CH0
$Comp
L Connector_Generic:Conn_02x07_Odd_Even J1
U 1 1 5FDFEE03
P 1250 1200
F 0 "J1" H 1300 1717 50  0000 C CNN
F 1 "Tigard" H 1300 1626 50  0000 C CNN
F 2 "Matir:PinHeader_2x07_P1.27mm_Both" H 1250 1200 50  0001 C CNN
F 3 "~" H 1250 1200 50  0001 C CNN
	1    1250 1200
	1    0    0    -1  
$EndComp
Wire Wire Line
	2450 1200 2250 1200
Wire Wire Line
	2450 1100 2250 1100
Wire Wire Line
	2450 1000 2250 1000
Wire Wire Line
	2450 900  2250 900 
Text Label 2250 1200 0    50   ~ 0
CH6
Text Label 2250 1100 0    50   ~ 0
CH4
Text Label 2250 1000 0    50   ~ 0
CH2
Text Label 2250 900  0    50   ~ 0
CH0
Wire Wire Line
	3150 900  2950 900 
Wire Wire Line
	3150 1000 2950 1000
Wire Wire Line
	3150 1100 2950 1100
Wire Wire Line
	3150 1200 2950 1200
Text Label 3150 1200 2    50   ~ 0
CH7
Text Label 3150 1100 2    50   ~ 0
CH5
Text Label 3150 1000 2    50   ~ 0
CH3
Text Label 3150 900  2    50   ~ 0
CH1
Text Label 3500 900  0    50   ~ 0
CH0
Text Label 3500 1000 0    50   ~ 0
CH1
Text Label 3500 1100 0    50   ~ 0
CH2
Text Label 3500 1200 0    50   ~ 0
CH3
Text Label 3500 1300 0    50   ~ 0
CH4
Text Label 3500 1400 0    50   ~ 0
CH5
Text Label 3500 1500 0    50   ~ 0
CH6
Text Label 3500 1600 0    50   ~ 0
CH7
Wire Wire Line
	3500 900  3700 900 
Wire Wire Line
	3700 1000 3500 1000
Wire Wire Line
	3500 1100 3700 1100
Wire Wire Line
	3700 1200 3500 1200
Wire Wire Line
	3500 1300 3700 1300
Wire Wire Line
	3700 1400 3500 1400
Wire Wire Line
	3500 1500 3700 1500
Wire Wire Line
	3700 1600 3500 1600
$EndSCHEMATC
