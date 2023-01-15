## Flashcap ##

Flashcap is a tool for testing the reported capacity of flash devices.

This works by *overwriting the entire device* with a sequence derived from the
location on the device.  It then reads the entire device and verifies the
expected values.  I expect that it would find the following types of issues:

* Devices that fail when writing before their advertised capacity.
* Devices that pretend to write but do not store the data.
* Devices that write to areas other than the intended area.
* Devices that have bad blocks that return data other than that written.
