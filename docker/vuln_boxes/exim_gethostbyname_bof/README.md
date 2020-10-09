== About ==

This *should* be an exploitable build of Exim and glibc as disclosed in
CVE-2015-0235, aka Metasploit module `linux/smtp/exim_gethostbyname_bof`.

Unfortunately, it requires Forward-confirmed reverse DNS.  I have not yet found
a way to force this case in the container.
