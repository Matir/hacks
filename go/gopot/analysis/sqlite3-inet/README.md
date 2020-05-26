# sqlite3-inet
SQLite3 functions to operate with IPv4 addresses

# About

Instructions (mostly from extension-functions.c):
```
1) Compile with
   Linux:
     gcc -fPIC -lm -shared ipv4-ext.c -o libsqliteipv4.so
   Mac OS X:
     gcc -fno-common -dynamiclib ipv4-ext.c -o libsqliteipv4.dylib
   (You may need to add flags
    -I /opt/local/include/
    if your sqlite3 is installed from Mac ports, or
    -I /sw/include/
    if installed with Fink.)
            Please, note that sqlite3 from macport 1.6.0 is not compiled with
            --enable-load-extension. So you cannot try this extension from
            within the sqlite3 shell.
            The same applies to leopard's /usr/bin/sqlite3
2) In your application, call sqlite3_enable_load_extension(db,1) to
   allow loading external libraries.  Then load the library libsqliteipv4
   using sqlite3_load_extension; the third argument should be 0.
   See http://www.sqlite.org/cvstrac/wiki?p=LoadableExtensions.
3) Use, for example:
   SELECT ISINNET( '10.0.0.1', '10.0.0.0', 8 );

The programm template was taken from
    http://sqlite.org/contrib/
    http://sqlite.org/contrib/download/extension-functions.c?get=25

Note: Loading extensions is by default prohibited as a
security measure; see "Security Considerations" in
http://www.sqlite.org/cvstrac/wiki?p=LoadableExtensions.
If the sqlite3 program and library are built this
way, you cannot use these functions from the program, you
must write your own program using the sqlite3 API, and call
sqlite3_enable_load_extension as described above.

If the program is built so that loading extensions is permitted,
the following will work:
sqlite> SELECT load_extension('./libsqliteipv4.so');
sqlite> select isinnet( '123.234.210.109', '123.123.23.18', '255.248.0.0' );
0

```

# Usage

This library provide IPv4 ISINNET, IP2INT, INT2IP, NETFROM, NETLENGTH, NETMASKLENGTH functions in SQL queries.

```
Author use these functions for store ip addresses as integers and networks as intervals of integers and search as
    select * from table_addr
    where IP2INT('172.16.1.193') between ip_from and ip_to;

For example, 
    ip_from = ('172.16.1.193/255.255.255.0')
    ip_to = ('172.16.1.193/255.255.255.0') + NETLENGTH('172.16.1.193/255.255.255.0')
or
    ip_to = ('172.16.1.193/24') + NETLENGTH('172.16.1.193/24')
or
    ip_to = ('172.16.1.193/24') + NETMASKLENGTH('24');


The description of IP2INT function:

    IP2INT( ip )

    IP2INT returns NULL if there is any kind of error, mainly :
	- strings are not valid IPV4 addresses or
	- number of bits is not a number or is out of range
    IP2INT returns integer number of IPV4 address otherwise

    SELECT IP2INT('192.168.1.1');
            ==>3232235777
    SELECT IP2INT('255.255.255.255');
            ==>4294967295
    SELECT IP2INT('0.0.0.0');
            ==>0


The description of INT2IP function:

    INT2IP( int_number )
    integer number may be a string ('3232235777' for
    example) or a number (3232235777 for example).
    Number 3232235777 is an integer number of the
    IPV4 address 192.168.1.1

    IP2INT returns NULL if int_number is not an integer number.
    IP2INT returns IPV4 address otherwise.
    
    SELECT INT2IP(3232235777);
    SELECT INT2IP('3232235777');
            ==>192.168.1.1
    SELECT INT2IP(4294967295);
    SELECT INT2IP('4294967295');
            ==>255.255.255.255
    SELECT INT2IP(0);
    SELECT INT2IP('0');
            ==>0.0.0.0	
            

The description of NETFROM function:

    NETFROM( network, mask ) or
    NETFROM( network/mask )
    mask may be specified the CIDR way as a number of bits,
    or as a standard 4 bytes notation.
    if CIDR notation is used, mask may be a string ('24' for
    example) or a number (24 for example).

    NETFROM returns NULL if there is any kind of error, mainly :
	- strings are not valid standard 4 bytes notation or
	- number of bits is not a number or is out of range
    NETFROM returns integer number of mask otherwise.

    SELECT NETFROM('192.168.1.1/255.255.255.0');
    SELECT NETFROM('192.168.1.1/24');
    SELECT NETFROM('192.168.1.1','255.255.255.0');
    SELECT NETFROM('192.168.1.1','24');
    SELECT NETFROM('192.168.1.1',24);
            ==>3232235776
    SELECT NETFROM('192.168.1.1/255.255.255.255');
    SELECT NETFROM('192.168.1.1/32');
    SELECT NETFROM('192.168.1.1','255.255.255.255');
    SELECT NETFROM('192.168.1.1','32');
    SELECT NETFROM('192.168.1.1',32);
            ==>3232235777
    SELECT NETFROM('192.168.1.1/255.255.128.0');
    SELECT NETFROM('192.168.1.1/17');
    SELECT NETFROM('192.168.1.1','255.255.128.0');
    SELECT NETFROM('192.168.1.1','17');
    SELECT NETFROM('192.168.1.1',17);
            ==>3232235520


The description of NETLENGTH function:

    NETLENGTH( network, mask ) or
    NETLENGTH( network/mask )
    mask may be specified the CIDR way as a number of bits,
    or as a standard 4 bytes notation.

    NETLENGTH returns NULL if there is any kind of error, mainly :
	- strings are not valid standard 4 bytes notation or
	- number of bits is not a number or is out of range
    NETLENGTH returns integer number of mask length otherwise.

    SELECT NETLENGTH('192.168.1.1','255.255.255.0');
    SELECT NETLENGTH('192.168.1.1,'24');
    SELECT NETLENGTH('192.168.1.1,24);
    SELECT NETLENGTH('192.168.1.1/255.255.255.0');
    SELECT NETLENGTH('192.168.1.1/24');
            ==>256
    SELECT NETLENGTH('192.168.1.1','255.255.255.255');
    SELECT NETLENGTH('192.168.1.1,'32');
    SELECT NETLENGTH('192.168.1.1,32);
    SELECT NETLENGTH('192.168.1.1/255.255.255.255');
    SELECT NETLENGTH('192.168.1.1/32');
            ==>1
    SELECT NETLENGTH('192.168.1.1','255.255.128.0');
    SELECT NETLENGTH('192.168.1.1,'17');
    SELECT NETLENGTH('192.168.1.1,17);
    SELECT NETLENGTH('192.168.1.1/255.255.128.0');
    SELECT NETLENGTH('192.168.1.1/17');
            ==>32768


The description of NETMASKLENGTH function:

    NETMASKLENGTH( mask )
    mask should be specified the CIDR way as a number of bits,
    in CIDR notation mask may be a string ('24' for
    example) or a number (24 for example). In CIDR notation
    mask should be in range from 8 to 32.

    NETLENGTH returns integer number of mask length.
    
    SELECT NETMASKLENGTH('24');
    SELECT NETMASKLENGTH(24);
            ==>256
    SELECT NETMASKLENGTH('32');
    SELECT NETMASKLENGTH(32);
            ==>1
    SELECT NETMASKLENGTH('17');
    SELECT NETMASKLENGTH(17);
            ==>32768

The NETTO function:
    SELECT NETTO('192.168.1.1/24') - NETFROM('192.168.1.1/24');
            ==>255
    SELECT NETTO('192.168.1.1/255.255.255.0') - NETFROM('192.168.1.1/255.255.255.0');
            ==>255


    SELECT NETTO('192.168.1.1','255.255.255.0') - NETFROM('192.168.1.1','255.255.255.0');
            ==>255
    SELECT NETTO('192.168.1.1','24') - NETFROM('192.168.1.1','24');
            ==>255


The ISINNET function reimplemented by Alexey Pechnikov (pechnikov@mobigroup.ru). Tests is saved as original author provide it. Thanks for idea! The code is public domain.


    ISINNET( ip, network, mask )
    mask may be specified the CIDR way as a number of bits,
    or as a standard 4 bytes notation.
    if CIDR notation is used, mask may be a string ('13' for
    example) or a number (13 for example)

    ISINNET returns NULL if there is any kind of error, mainly :
	- strings are not valid IPV4 addresses or
	- number of bits is not a number or is out of range
    ISINNET returns 1 if (ip & mask) = (net)
    ISINNET returns 0 otherwise

    SELECT ISINNET( '172.16.1.193', '172.16.1.0', 24 );
    SELECT ISINNET( '172.16.1.193', '172.16.1.0/24' );
            ==> 1
    SELECT ISINNET( '172.16.1.193', '172.16.1.0', 25 );
    SELECT ISINNET( '172.16.1.193', '172.16.1.0/25' );
            ==> 0
    SELECT ISINNET( '172.16.1.193', '172.16.1.0', '255.255.255.0' );
    SELECT ISINNET( '172.16.1.193', '172.16.1.0/255.255.255.0' );
            ==> 1
    SELECT ISINNET( '172.16.1.193', '172.16.1.0', '255.255.255.128' );
    SELECT ISINNET( '172.16.1.193', '172.16.1.0/255.255.255.128' );
            ==> 0

    CREATE TABLE ip_add (
	ip	varchar( 16 )
    );
    INSERT INTO ip_add VALUES('172.16.1.40');
    INSERT INTO ip_add VALUES('172.16.1.93');
    INSERT INTO ip_add VALUES('172.16.1.204');
    INSERT INTO ip_add VALUES('172.16.4.203');
    INSERT INTO ip_add VALUES('172.16.4.205');
    INSERT INTO ip_add VALUES('172.16.4.69');
    INSERT INTO ip_add VALUES('10.0.1.204');
    INSERT INTO ip_add VALUES('10.0.1.16');
    INSERT INTO ip_add VALUES('10.1.0.16');
    INSERT INTO ip_add VALUES('192.168.1.5');
    INSERT INTO ip_add VALUES('192.168.1.7');
    INSERT INTO ip_add VALUES('192.168.1.19');

    SELECT ip FROM ip_add WHERE ISINNET( ip, '172.16.1.0', 16 );
    SELECT ip FROM ip_add WHERE ISINNET( ip, '172.16.1.0/16' );
    172.16.1.40
    172.16.1.93
    172.16.1.204
    172.16.4.203
    172.16.4.205
    172.16.4.69

    SELECT ip FROM ip_add WHERE ISINNET( ip, '172.16.1.0', 24 );
    SELECT ip FROM ip_add WHERE ISINNET( ip, '172.16.1.0/24' );
    172.16.1.40
    172.16.1.93
    172.16.1.204

    SELECT * FROM ip_add WHERE NOT ISINNET( ip, '128.0.0.0', 1 );
    SELECT * FROM ip_add WHERE NOT ISINNET( ip, '128.0.0.0/1' );
    10.0.1.204
    10.0.1.16
    10.1.0.16

    DELETE FROM ip_add WHERE NOT ISINNET( ip, '128.0.0.0', 1 );
    DELETE FROM ip_add WHERE NOT ISINNET( ip, '128.0.0.0/1' );

    SELECT * FROM ip_add;
    172.16.1.40
    172.16.1.93
    172.16.1.204
    172.16.4.203
    172.16.4.205
    172.16.4.69
    192.168.1.5
    192.168.1.7
    192.168.1.19
```

# Tests

Use tests from file ipv4-ext.sql to check the functions correctness.

# History

The project moved from my own fossil repository.
