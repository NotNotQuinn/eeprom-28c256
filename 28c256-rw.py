#!/usr/bin/env python3
from typing import List, Union
import argparse
import logging
import camino
import time
import math
import _io
import sys

logger = logging.getLogger(__name__)
log_traceback = False

def config_logging(verbosity: int, force=False, msg_format='%(levelname)-8s | %(name)s: %(message)s'):
    global log_traceback
    level = "ERROR"
    log_traceback = False
    if verbosity >= 3:
        verbosity = 3
        level = "DEBUG"
        log_traceback = True
    elif verbosity >= 2:
        level = "INFO"
        log_traceback = True
        logging.getLogger("camino").setLevel("WARNING")
    elif verbosity >= 1:
        log_traceback = True
        level = "WARNING"


    logging.basicConfig(format=msg_format, level=level, force=force)
    logger.debug(f'Verbosity set to {verbosity} ({level})')
    return verbosity

# logging configuration
config_logging(0)

# Little endian (least significant byte is stored at lowest address)


class EEPROM_Programmer():

    # The maximum address usable on the EEPROM.
    MAX_ADDRESS = 0x7FFF
    # The number of bytes this EEPROM stores.
    EEPROM_SIZE = MAX_ADDRESS+1
    # A series of byte patterns for testing writing to the EEPROM.
    WRITE_TEST_PATTERNS = [
            [ 0xA5, 0xA5, 0xA5, 0xA5 ],
            [ 0x00, 0xFA, 0xCA, 0xDE ],
            [ 0xC0, 0xFF, 0xEE, 0x00 ],
            [ 0xDE, 0xAD, 0xBE, 0xEF ],
            [ 0xBE, 0xEF, 0xDE, 0xAD ],
            [ 0xCA, 0xFE, 0xD0, 0x0D ],
            [ 0xBA, 0xAA, 0xAA, 0xAD ],
            [ 0x8B, 0xAD, 0xF0, 0x0D ]
        ]

    def __init__(self, arduino: camino.Arduino):
        self.arduino = arduino

    ### UNDERLYING ARDUINO COMMUNICATIONS ###

    def _read(self, address: int) -> int:
        """Reads a single byte from the EEPROM.

        Args:
            address (int): The address of the byte to read.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.

        Returns:
            int: The value of the byte, within the range (00..ff) inclusive.
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        return self.arduino.read(address & 0xFF, address >> 8, out=int, signed=False)

    def _write(self, address: int, byte: int) -> None:
        """Writes a single byte to the EEPROM.

        Args:
            address (int): The address to store the byte to.
            byte (int): The value to store.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.
            ValueError: Byte outside of allowed range (00..ff) inclusive.

        Returns:
            _type_: _description_
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if byte > 0xFF or byte < 0:
            raise ValueError(f"Byte out of range 0x00-0xFF: got 0x{byte:04x}")

        return self.arduino.write(address & 0xFF, address >> 8, byte)

    def _hexdump16(self, address: int) -> str:
        """Returns a string with a single line formatted as a hexdump of the address given.

        Args:
            address (int): The address to start reading the hexdump from.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.
            ValueError: Address is not divisible by 16.

        Returns:
            str: The hexdump string, OR a string describing an error which occurred inside the arduino. In the case of an error, the string will start with "[arduino error]"
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 16 != 0:
            raise ValueError(f"Address must be divisible by 16: got 0x{address:04x}")

        return self.arduino.hexdump16(address & 0xFF, address >> 8, out=str)

    def _hexdump32(self, address: int) -> str:
        """Returns a string with two lines formatted as a hexdump of the address given.

        Args:
            address (int): The address to start reading the hexdump from.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.
            ValueError: Address is not divisible by 32.

        Returns:
            str: The hexdump string, OR a string describing an error which occurred inside the arduino. In the case of an error, the string will start with "[arduino error]"
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 32 != 0:
            raise ValueError(f"Address must be divisible by 32: got 0x{address:04x}")

        return self.arduino.hexdump32(address & 0xFF, address >> 8, out=str)

    def _read_page(self, address: int) -> Union[bytes, None]:
        """Reads a page (64 bytes) of the EEPROM.

        Args:
            address (int): The page address to start reading from.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.
            ValueError: Address is not divisible by 64.

        Returns:
            None | bytes: Returns None on errors within the arduino, or bytes on success.
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 64 != 0:
            raise ValueError(f"Address must be divisible by 64: got 0x{address:04x}")

        return self.arduino.read_page(address & 0xFF, address >> 8, out=bytes)

    def _write_page(self, address: int, data: List[int]) -> Union[str, None]:
        """Writes a page (64 bytes) of data to the EEPROM. Considerably faster than writing one byte at a time.

        Args:
            address (int): The page address to write to.
            data (List[int]): The sequence of bytes to write into the page.

        Raises:
            ValueError: Address outside of allowed range (0000..MAX_ADDRESS) inclusive.
            ValueError: Address is not divisible by 64.
            ValueError: Data does not have exactly 64 items.

        Returns:
            str | None: Returns None on success, returns a string for errors within the arduino.
        """

        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 64 != 0:
            raise ValueError(f"Address must be divisible by 64: got 0x{address:04x}")

        if len(data) != 64:
            raise ValueError(f"Data array must be length 64: got {len(data)}")

        ret = self.arduino.write_page(address & 0xFF, address >> 8, *data, out=str)
        # Sleep to allow the arduino to finish the write cycle
        # Since interrupts are disabled during it, we wont
        # be able to communicate with it.

        # I have no idea how long this needs to be lol, but this works
        # and 0.005 doesnt work
        time.sleep(0.01)
        return ret

    def _echo(self, data: bytes):
        """Returns the bytes you send."""

        return self.arduino.echo(data)

    ### METHODS ###

    def hexdump(self, start: int=0x0000, stop: int=EEPROM_SIZE, allow_repetition=False):
        """Dumps EEPROM contents from start (inclusive) to stop (exclusive).

        Args:
            start (int, optional): Starts hexdump before or at this address. Defaults to 0.
            stop (int, optional): Stops hexdump after or at this address. Defaults to EEPROM_SIZE.
        """

        if stop <= start: raise ValueError("Start must be less than stop.")
        if stop > self.EEPROM_SIZE: raise ValueError("Stop must be less than EEPROM_SIZE (0x{:04x})".format(self.EEPROM_SIZE))
        if start < 0: raise ValueError("Start must not be less than zero.")

        # Record each line
        first_line = (math.trunc(start/0x10))*0x10
        final_line = (math.ceil(stop/0x10))*0x10

        # Read pages (64 bytes) to be more efficient
        first_page = (math.trunc(first_line/0x40))*0x40
        final_page = (math.ceil(final_line/0x40))*0x40

        # Is set to trigger an exit of the method
        done = False
        # Records the previously printed line's data
        prev_line_data = bytes()
        # Records if the previously printed line was only partially displayed
        prev_line_partial = False
        # Records if we are currently in a "*". a "*" happens when the same data is repeated on multiple lines in a row.
        within_star = False

        # Loop over each page
        for page_addr in range(first_page, final_page, 0x40):
            if done: break

            # Read one page at a time
            data = self._read_page(page_addr)

            # Go over each line within the page.
            for line in range(0, 0x40, 0x10):
                line_addr = page_addr+line

                if line_addr < first_line: continue
                if line_addr >= final_line: done = True; break

                # Get the data for this line
                line_data = data[line:line+0x10]

                # If we are within a "*" and the data matches, and this isnt the end of the dump: skip
                if within_star and line_data == prev_line_data and not stop-0x10 < line_addr:
                    continue

                # No longer within a "*"
                within_star = False

                # Format each byte in the line
                hd = [f'{byte:02x}' for byte in line_data]
                # Visualize the data for the line as ascii
                visualized = f"|{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in line_data])}|"
                # Records the address to print on the line
                shown_addr = line_addr
                # Records if the current line is partially printed
                line_partial = False

                if start > line_addr:
                    # Blank out the data before the start
                    line_partial = True
                    shown_addr = line_addr+start%0x10
                    visualized = (" "*(start%0x10)) + "|" +str(visualized[start%0x10+1:])
                    for k in range(start%0x10):
                        hd[k] = "  "
                if stop-0x10 < line_addr:
                    # Blank out the data after the end
                    line_partial = True
                    visualized = str(visualized[:-(0x10 - (stop%0x10-1))]) + "|"
                    for k in range(0xf, stop%0x10-1, -1):
                        hd[k] = "  "

                if prev_line_data == line_data and not prev_line_partial and not line_partial and not allow_repetition:
                    # Begin a new "*"
                    print('*')
                    within_star = True
                else:
                    # Print as usual
                    print(f"{shown_addr:04x}  {hd[0]} {hd[1]} {hd[2]} {hd[3]} {hd[4]} {hd[5]} {hd[6]} {hd[7]}  {hd[8]} {hd[9]} {hd[10]} {hd[11]} {hd[12]} {hd[13]} {hd[14]} {hd[15]}  {visualized}")

                # Current data has become the previous data.
                prev_line_data = line_data
                prev_line_partial = line_partial

        # Print the final address, the byte at this address will not have been printed.
        print(f"{stop:04x}")


    def write_test(self, trial_count: int=8):
        """Runs a series of read/write trials on the first 4 EEPROM pages to verify everything is working correctly.
        Reports any errors as they occur, and the % of errors after all the trails are finished.

        Args:
            trial_count (int, optional): The number of times to write/read the first 4 EEPROM pages. Defaults to 8.
        """
        # // Cycles through one message per trial
        count = 0
        for i in range(trial_count):
            data = [0]*64
            for j in range(64):
                data[j] = WRITE_TEST_PATTERNS[i % len(msg)][j % 4]

            self._write_page(0x00, data)
            self._write_page(0x40, data)
            self._write_page(0x80, data)
            self._write_page(0xc0, data)
            self.hexdump(0x100)
            for a in range(0x100):
                got = self._read(a)
                expected = WRITE_TEST_PATTERNS[i % len(WRITE_TEST_PATTERNS)][a % 4]

                if got != expected:
                    count += 1
                    flipped = got ^ expected
                    msg = ""
                    msg += f"{a:04x}: Expected {expected:02x}, got {got:02x}.   ("
                    for _ in range(8):
                        msg += '1' if flipped & 0x80 else '0'
                        flipped <<= 1
                    msg += " flipped)"
                    logger.error(msg)

        total = trial_count * 256
        percent = (count / total) * 100
        logger.info(f"Done! {percent}% ({count}/{total}) errors avg over {trial_count} trials.")


def get_eeprom(port='COM3', baud=115200) -> EEPROM_Programmer:
    logger.info('Connecting to arduino...')
    logger.debug(f'  {port = }')
    logger.debug(f'  {baud = }')
    connection = camino.SerialConnection(port=port, baud=baud)
    eeprom = EEPROM_Programmer(camino.Arduino(connection))
    logger.info('Arduino connected!')
    return eeprom


def upload_file(file, eeprom: EEPROM_Programmer):
    FILE_LEN = EEPROM_Programmer.EEPROM_SIZE

    raw_data = file.read()
    file.close()

    if type(raw_data) == bytes:
        buf = raw_data
    elif type(raw_data) == str:
        buf = bytes(raw_data, "ascii")
    else:
        buf = bytes(raw_data)

    if len(buf) != FILE_LEN:
        logger.fatal(f"FATAL: File length must be exactly {FILE_LEN} (0x{FILE_LEN:x}); Got {len(buf)} (0x{len(buf):x})")
        exit(1)

    # Write file contents to EEPROM
    for addr in range(0, FILE_LEN, 64):
        eeprom._write_page(addr, buf[addr:addr+64])
        print(f"Writing... [0x{addr:04x}] {100*((addr+64)/FILE_LEN):.2f}%", end='\r', file=sys.stderr)
    print(file=sys.stderr)

    # Read EEPROM and verify contents
    for addr in range(0, FILE_LEN, 64):
        new_data = eeprom._read_page(addr)
        should_data = buf[addr:addr+64]
        print(f"Verifying... [0x{addr:04x}] {100*((addr+64)/FILE_LEN):.2f}%", end='\r', file=sys.stderr)
        if new_data != should_data:
            print(f"\nVerification failed! address 0x{addr:04x}, got {new_data!r}, instead of {should_data!r}", file=sys.stderr)
            exit(1)
    print(file=sys.stderr)


def download_file(file, eeprom: EEPROM_Programmer):
    FILE_LEN = EEPROM_Programmer.EEPROM_SIZE
    # Hex buffer
    buf = ""

    # Read EEPROM
    for addr in range(0, FILE_LEN, 64):
        data = eeprom._read_page(addr)
        buf += data.hex()
        print(f"Reading... [0x{addr:04x}] {100*((addr+64)/FILE_LEN):.2f}%", end='\r', file=sys.stderr)
    print(file=sys.stderr)
    if type(file) == _io.TextIOWrapper:
        file.write(str(bytes.fromhex(buf), encoding="ascii"))
    else:
        file.write(bytes.fromhex(buf))
    file.close()




def get_cli_args():
    p = argparse.ArgumentParser(
        add_help=True,
        prog="28c256-rw.py",
        description="Read/Write model 28c265 EEPROMs.",
    )
    p.add_argument("-v", "--verbose", help="Show more output. -v for WARNING, -vv for INFO, -vvv for DEBUG. Default is ERROR", action="count", default=False)
    mode = p.add_argument_group("Mode determining arguments", "These arguments set the mode to DOWNLOAD, UPLOAD and HEXDUMP respectively.")
    mode_required = mode.add_mutually_exclusive_group(required=True)
    mode_required.add_argument("-D", "--download",
                   metavar="OUTFILE",
                   type=argparse.FileType('wb'),
                   help="Download the EEPROM and store in OUTFILE"
                   )
    mode_required.add_argument("-U", "--upload",
                   metavar="INFILE",
                   type=argparse.FileType('rb'),
                   help="Upload INFILE to the EEPROM"
                   )
    mode_required.add_argument("-H", "--hexdump",
                   action='store',
                   metavar='[START:]STOP',
                   nargs='?',
                   const='0x8000',
                   type=str,
                   help="Hexdump the EEPROM contents from addresses START to STOP. Defaults to dump the entire EEPROM."
                   )

    hexdump = p.add_argument_group("Hexdump mode options", "These options only apply when in HEXDUMP mode (-H/--hexdump)")
    hexdump.add_argument("-r", "--allow-repetition",
                         help="Allow repeated lines in hexdump output.",
                         action="store_true",
                         dest="allow_repetition"
                         )

    args = p.parse_args()
    return args


def parse_address_range(specifier: str):
    start, stop = 0, EEPROM_Programmer.EEPROM_SIZE
    if specifier.count(":") == 0:
        stop = int(specifier, base=0)
    elif specifier.count(":") == 1:
        start, stop = [int(n, base=0) for n in specifier.split(":")]
    else:
        raise ValueError("address range invalid syntax: must match [START:]STOP")

    return start, stop


def main_cli():
    try:
        args = get_cli_args()
        args.verbose = config_logging(args.verbose, force=True)
    except Exception:
        # This exception must be logged
        logging.exception("Parsing arguments or logging configuration failed. Cannot continue.")
        exit(1)

    logger.debug(f"Input interpretation: {args!r}")
    logger.debug(f'  {args.verbose = }')
    logger.debug(f'  {args.upload = }')
    logger.debug(f'  {args.download = }')
    logger.debug(f'  {args.hexdump = }')
    logger.debug(f'    {args.allow_repetition = }')

    if args.upload != None:
        mode = "upload"
    elif args.download != None:
        mode = "download"
    elif args.hexdump != None:
        mode = "hexdump"
    else:
        logger.fatal("Input interpretation is ambiguous: no valid mode")
        exit(1)

    logger.debug(f'  {mode = }')

    # Mode and file are verified, we can now begin.
    eeprom = get_eeprom()

    if mode == "hexdump":
        start, stop = parse_address_range(args.hexdump)
        eeprom.hexdump(start=start, stop=stop, allow_repetition=args.allow_repetition)
    elif mode == "upload":
        upload_file(args.upload, eeprom)
    elif mode == "download":
        download_file(args.download, eeprom)


if __name__ == "__main__":
    try:
        main_cli()
    except Exception as e:
        msg = f"{e.__class__.__name__}: {e!s}"
        if log_traceback:
            logger.exception(msg)
        else:
            logger.error("(use -v for traceback) " + msg)
