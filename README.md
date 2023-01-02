# EEPROM 28c256
This is an EEPROM read/writer that uses [camino](https://github.com/n-wach/camino)
to communicate through python what to read/write.

This is made in an effort to follow along with [Ben Eater's 6502 computer building series](https://www.youtube.com/watch?v=LnzuMJLZRdU&list=PLowKtXNTBypFbtuVMUVXNR0z1mu7dp7eH),
but without buying the EEPROM programmer (because its expensive, and I have lots of free time).

So far I don't know if it was actually worth it.

## Using
To use this, you need to hook up your AT28C256 EEPROM to an arduino, however you are able to.
Once you have done that, edit the arduino file with the correct pins (EEPROMXX -> arduino pin #).
Next install the `camino` python package and use the included `writer.py` file to communicate with the arduino and write your data :)

As of right now, this package has many bugs and I would not recommend using it at all. (it hardly works)
