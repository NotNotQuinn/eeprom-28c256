# EEPROM 28c256
This is a command-line utility for reading or writing to AT28C256 model
EEPROMs through an arduino with a breadboard.

This is made in an effort to follow along with [Ben Eater's 6502 computer building series](https://www.youtube.com/watch?v=LnzuMJLZRdU&list=PLowKtXNTBypFbtuVMUVXNR0z1mu7dp7eH),
but without buying the EEPROM programmer (because its expensive, and I have lots of free time).

## Features

This utility features uploading a binary file to the EEPROM, downloading the EEPROM
to a local file, and a hexdump like output.

### Upload

When uploading to the EEPROM the script writes the entire content of the EEPROM, and then
reads back the entire contents to verify they were written correctly. This cannot be disabled.

An example: Uploading `FILE.bin` to the eeprom.
```sh
$ ./28c256-rw.py -U FILE.bin
```

```txt
Writing... [0x7fc0] 100.00%
Verifying... [0x7fc0] 100.00%
```

### Download

When downloading the EEPROM contents, the EEPROM is read one page at a time (64 bytes).

An example: Downloading the EEPROM contents into `EEPROM-27-01-2023.bin`.
```sh
$ ./28c256-rw.py -D EEPROM-27-01-2023.bin
```

```
Reading... [0x7fc0] 100.00%
```

### Hexdump

To quickly check specific bytes in the EEPROM, hexdump spits them out in hexdump-like output.
The start/stop addresses can be any address. If there is repeated data, a "*" is shown.

An example: Dumping the entire EEPROM.

```
./28c256-rw.py -H
```

```
0000  48 65 6c 6c 6f 2c 20 4d  79 20 6e 61 6d 65 20 69  |Hello, My name i|
0010  73 20 51 75 69 6e 6e 2e  20 54 68 65 20 72 65 61  |s Quinn. The rea|
0020  73 6f 6e 20 74 68 69 73  20 66 69 6c 65 20 69 73  |son this file is|
0030  20 66 75 6c 6c 20 6f 66  20 27 51 27 20 69 73 20  | full of 'Q' is |
0040  62 65 63 61 75 73 65 20  69 74 73 20 74 68 65 20  |because its the |
0050  66 69 72 73 74 20 6c 65  74 74 65 72 20 6f 66 20  |first letter of |
0060  6d 79 20 6e 61 6d 65 2e  0a 51 51 51 51 51 51 51  |my name..QQQQQQQ|
0070  51 51 51 51 51 51 51 51  51 51 51 51 51 51 51 51  |QQQQQQQQQQQQQQQQ|
*
8000
```

An example: Dumping bytes `0x2000` to `0x2060`.

```
./28c256-rw.py -H 0x2000:0x2060
```

```
2000  51 51 51 51 51 51 51 51  51 51 51 51 51 51 51 51  |QQQQQQQQQQQQQQQQ|
*
2060
```

An example: Showing bytes `0x7ffc` and `0x7ffd`.

```
./28c256-rw.py -H 0x7ffc:0x7ffe
```

```
7ffc                                       51 51                    |QQ|
7ffe
```


## Setup

### Hardware required

If you need to use this, you will likely have most if not all of the hardware already:
* AT28C256 EEPROM
* Arduino with at least 28 free pins
* Breadboard
* 28+ wired ribbon cable (or equivalent; its just wires)

### Hardware setup

To setup the hardware:

1. Place the AT28C256 EEPROM into the breadboard.
2. Connect each pin of the AT28C256 EEPROM to the Arduino using the ribbon cable.
   Take note of the pin numbers on the Arduino which you used, connect 5V and GND also.
3. Connect the Arduino to your computer.

### Software setup

To setup the software:

1. Download and setup the [Arduino IDE](https://www.arduino.cc/en/software) on your computer.
	* Test that the arduino works properly by running a small test program to
	  flash the builtin LED.
2. Install the `camino` library to your Arduino IDE.
3. Download this repository from github onto your PC.
4. Create a new project in the arduino IDE and copy the `28c256.ino` file and `vec/` folder into it.
5. Edit the section labeled "EEPROM pins to Arduino pins" such that the arduino pins match
   which pin you used when plugging in the EEPROM. This step is very important
   to get right the first time.
6. Ensure you have `python3` installed on your system. Install the `camino` python package.
7. Run `28c256-rw.py` and see if it works!

### Troubleshooting

If you encounter issues setting up the EEPROM and verifying that it works, there are some
things that might help you resolve your issues:

<!-- Editors node: I spent way too long rewording these paragraphs to match the same line -->

* Ensure that each wire connecting the EEPROM to the arduino make proper contact. Does it
  seem obvious? Yes, but its really not. (especially when working in the "software" realm
  for a few hours)

* Double check that the arduino pins used to plug in the EEPROM are correctly recorded in
  `28c256.ino`. If any of these are swapped it might not be obvious, but the data written
  will be wrong when read by some other hardware. However: It will seem correct ONLY from
  the arduino's perspective. Only if pins 14, 20, 22, 27 or 28 are swapped the chip won't
  work. If something else is swapped: it may seem to be working, but it wont be. View the
  [datasheet](https://eater.net/datasheets/28c256.pdf) to see what pin has which function.

* Try running the read/write tests. To run them, see the help output for the CLI tool. If
  for some reason you can't get the CLI tool to work there are tests you can run from the
  arduino itself. To run the test from the arduino without the CLI, recompile `28c256.ino`
  with the line that says `#define USE_CAMINO` commented out. This will automatically run
  a basic test to help you get more intuition about the problem. However, the recommended
  way to test is through the CLI, if possible.

* If the above test is giving different data every time, (i.e., `Expected ff, got XX.` ->
  and `XX` is different each time) then there might be interference between the wires. To
  solve this issue make sure that none of the wires connected to IO are directly parallel
  to any wire connected to address pins. This is especially important for the lower order
  address bits. Try moving or pushing the wires while the arduino-based tests are running
  to get a sense of what positioning of wires can cause issues.

* If you are still having issues and have a few capacitors laying around try putting a 10
  μF (microfarad) capacitor across each power pin (pins 14 & 28) of the EEPROM. This will
  store a tiny amount of power closer to the EEPROM. This solved some issues, but doesn't
  seem to be necessary as after removing them the issues haven't come back. Only try this
  if you already have the capacitors.

* If you're still having issues getting the CLI working and you believe its an issue with
  this library feel free to open an issue and I'll try to resolve the issue as best I can,
  if I can, and when I have time. In your issue, please be very descriptive of things you
  tried and didn't try, and why those things didn't work. I will probably ask about these
  things anyway, so this will only serve to help me figure out the problem faster.

## Usage

CLI usage text:

```txt
usage: 28c256-rw.py [-h] [-v] (-D OUTFILE | -U INFILE | -H [[START:]STOP] | -T N) [-a] [-s] [-w S] [-d]

Read out and write to model AT28C256 EEPROMs. Uploaded files must be exactly 0x8000 bytes in length.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Show more output. -v for WARNING, -vv for INFO, -vvv for DEBUG. Default is ERROR

Mode determining arguments:
  These arguments set the mode to DOWNLOAD, UPLOAD, HEXDUMP and WRITE-TESTING respectively.

  -D OUTFILE, --download OUTFILE
                        Download the EEPROM and store in OUTFILE
  -U INFILE, --upload INFILE
                        Upload INFILE to the EEPROM
  -H [[START:]STOP], --hexdump [[START:]STOP]
                        Hexdump the EEPROM contents from addresses START (inclusive) to STOP (exclusive).
                        Defaults to dump the entire EEPROM.
  -T N, --run-write-tests N
                        WARNING: DATA LOSS POSSIBLE. Runs write tests for the EEPROM. Each of N times the
                        first 256 bytes of the EEPROM are written and then read back. The total error
                        percentage is reported.

Hexdump options:
  These options modify the behaviour of HEXDUMP mode, and WRITE-TESTING mode when using --hexdump-tests.

  -a, --hexdump-all     Allow repeated lines in hexdump output. By default when a line is repeated more
                        than once, an asterisk is shown. This option disables that behaviour.

Write-testing options:
  These modify the behaviour of WRITE-TESTING mode.

  -s, --hexdump-tests   Dumps the bytes that are modified each trial using HEXDUMP.
  -w S, --read-wait-time S
                        Specifies the amount of time in seconds to wait after writing and before reading
                        the test data. Floating point values are accepted. Default is 1.
  -d, --double-read     Reads the test data back twice, using the second data only. Somehow this improves
                        error rates to near zero in some cases.
```
