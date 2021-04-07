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
L Connector_Generic:Conn_02x03_Odd_Even J1
U 1 1 60765C80
P 1550 1500
F 0 "J1" H 1600 1817 50  0000 C CNN
F 1 "PiHdr" H 1600 1726 50  0000 C CNN
F 2 "Connector_PinSocket_2.54mm:PinSocket_2x03_P2.54mm_Vertical" H 1550 1500 50  0001 C CNN
F 3 "~" H 1550 1500 50  0001 C CNN
	1    1550 1500
	1    0    0    -1  
$EndComp
NoConn ~ 1350 1400
NoConn ~ 1350 1500
NoConn ~ 1350 1600
$Comp
L power:GND #PWR02
U 1 1 6076678A
P 1950 1600
F 0 "#PWR02" H 1950 1350 50  0001 C CNN
F 1 "GND" H 1955 1427 50  0000 C CNN
F 2 "" H 1950 1600 50  0001 C CNN
F 3 "" H 1950 1600 50  0001 C CNN
	1    1950 1600
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 1600 1850 1600
$Comp
L power:+5V #PWR01
U 1 1 60766AAE
P 1950 1300
F 0 "#PWR01" H 1950 1150 50  0001 C CNN
F 1 "+5V" H 1965 1473 50  0000 C CNN
F 2 "" H 1950 1300 50  0001 C CNN
F 3 "" H 1950 1300 50  0001 C CNN
	1    1950 1300
	1    0    0    -1  
$EndComp
Wire Wire Line
	1950 1300 1950 1400
Wire Wire Line
	1950 1400 1850 1400
Wire Wire Line
	1950 1400 1950 1500
Wire Wire Line
	1950 1500 1850 1500
Connection ~ 1950 1400
$Comp
L Connector:Screw_Terminal_01x02 J2
U 1 1 6076714B
P 3400 1400
F 0 "J2" H 3480 1392 50  0000 L CNN
F 1 "Screw_Terminal_01x02" H 3480 1301 50  0000 L CNN
F 2 "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-5.0-H_1x02_P5.00mm_Horizontal" H 3400 1400 50  0001 C CNN
F 3 "~" H 3400 1400 50  0001 C CNN
	1    3400 1400
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR04
U 1 1 6076761F
P 3100 1550
F 0 "#PWR04" H 3100 1300 50  0001 C CNN
F 1 "GND" H 3105 1377 50  0000 C CNN
F 2 "" H 3100 1550 50  0001 C CNN
F 3 "" H 3100 1550 50  0001 C CNN
	1    3100 1550
	1    0    0    -1  
$EndComp
Wire Wire Line
	3200 1500 3100 1500
Wire Wire Line
	3100 1500 3100 1550
$Comp
L power:+5V #PWR03
U 1 1 607679D4
P 3100 1300
F 0 "#PWR03" H 3100 1150 50  0001 C CNN
F 1 "+5V" H 3115 1473 50  0000 C CNN
F 2 "" H 3100 1300 50  0001 C CNN
F 3 "" H 3100 1300 50  0001 C CNN
	1    3100 1300
	1    0    0    -1  
$EndComp
Wire Wire Line
	3100 1300 3100 1400
Wire Wire Line
	3100 1400 3200 1400
$Comp
L Mechanical:MountingHole H1
U 1 1 607707C7
P 1200 2400
F 0 "H1" H 1300 2446 50  0000 L CNN
F 1 "MountingHole" H 1300 2355 50  0000 L CNN
F 2 "MountingHole:MountingHole_3.2mm_M3" H 1200 2400 50  0001 C CNN
F 3 "~" H 1200 2400 50  0001 C CNN
	1    1200 2400
	1    0    0    -1  
$EndComp
Connection ~ 1950 1500
Connection ~ 1950 1600
$EndSCHEMATC
