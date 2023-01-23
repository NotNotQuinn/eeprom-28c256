import _camino as camino
import time
from typing import List, Union
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

    def hexdump(self, stop: int=EEPROM_SIZE):
        """Dumps EEPROM contents from 0x0000 to stop, rounding up to the nearest multiple of 64.

        Args:
            stop (int, optional): Stops hexdump after this address has been reached. Defaults to self.EEPROM_SIZE.
        """

        for a in range(0x0000, stop, 0x40):
            # print(eeprom._hexdump32(a))
            # print(eeprom._hexdump32(a+0x20))
            d = eeprom._read_page(a)
            print(
                f"{a+0x00:04x}:  {d[0+0x00]:02x} {d[1+0x00]:02x} {d[2+0x00]:02x} {d[3+0x00]:02x} {d[4+0x00]:02x} {d[5+0x00]:02x} {d[6+0x00]:02x} {d[7+0x00]:02x}  {d[8+0x00]:02x} {d[9+0x00]:02x} {d[10+0x00]:02x} {d[11+0x00]:02x} {d[12+0x00]:02x} {d[13+0x00]:02x} {d[14+0x00]:02x} {d[15+0x00]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x00:0x10]])}|\n"
                f"{a+0x10:04x}:  {d[0+0x10]:02x} {d[1+0x10]:02x} {d[2+0x10]:02x} {d[3+0x10]:02x} {d[4+0x10]:02x} {d[5+0x10]:02x} {d[6+0x10]:02x} {d[7+0x10]:02x}  {d[8+0x10]:02x} {d[9+0x10]:02x} {d[10+0x10]:02x} {d[11+0x10]:02x} {d[12+0x10]:02x} {d[13+0x10]:02x} {d[14+0x10]:02x} {d[15+0x10]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x10:0x20]])}|\n"
                f"{a+0x20:04x}:  {d[0+0x20]:02x} {d[1+0x20]:02x} {d[2+0x20]:02x} {d[3+0x20]:02x} {d[4+0x20]:02x} {d[5+0x20]:02x} {d[6+0x20]:02x} {d[7+0x20]:02x}  {d[8+0x20]:02x} {d[9+0x20]:02x} {d[10+0x20]:02x} {d[11+0x20]:02x} {d[12+0x20]:02x} {d[13+0x20]:02x} {d[14+0x20]:02x} {d[15+0x20]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x20:0x30]])}|\n"
                f"{a+0x30:04x}:  {d[0+0x30]:02x} {d[1+0x30]:02x} {d[2+0x30]:02x} {d[3+0x30]:02x} {d[4+0x30]:02x} {d[5+0x30]:02x} {d[6+0x30]:02x} {d[7+0x30]:02x}  {d[8+0x30]:02x} {d[9+0x30]:02x} {d[10+0x30]:02x} {d[11+0x30]:02x} {d[12+0x30]:02x} {d[13+0x30]:02x} {d[14+0x30]:02x} {d[15+0x30]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x30:0x40]])}|"
            )
        print("=-------------------------------------------------------------------------=")

    def write_test(self, trial_count:int = 8):
        """Runs a series of read/write trials on the first 4 EEPROM pages to verify everything is working correctly.
        Reports to stdout any errors as they occur, and the % of errors after all the trails are finished.

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
                    print(f"{a:04x}: Expected {expected:02x}, got {got:02x}.", end="")
                    print("   (", end="")
                    for _ in range(8):
                        print('1' if flipped & 0x80 else '0', end="")
                        flipped <<= 1
                    print(" flipped)")

        total = trial_count * 256
        percent = (count / total) * 100
        print(f"Done! {percent}% ({count}/{total}) errors avg over {trial_count} trials.")

def create_file(filename):
    buf = bytes([0xea] * EEPROM_Programmer.EEPROM_SIZE)
    with open(filename, 'wb') as f:
        f.write(buf)

def main():
    FILE_LEN = EEPROM_Programmer.EEPROM_SIZE

    print('[arduino] Connecting...')
    connection = camino.SerialConnection(port='COM3', baud=115200)
    eeprom = EEPROM_Programmer(camino.Arduino(connection, silent=True))
    print("[arduino] Connected!")

    filename = "./dank_file.o"
    create_file(filename)

    with open(filename, "rb") as f:
        buf = bytes(f.read())

    if len(buf) != FILE_LEN:
        print(f"FATAL: File length must be exactly {FILE_LEN} (0x{FILE_LEN:x}. Got {len(buf)} (0x{len(buf):x})")
        exit(1)

    # Write file contents to EEPROM
    for addr in range(0, FILE_LEN, 64):
        eeprom._write_page(addr, buf[addr:addr+64])
        print(f"Writing... [0x{addr:04x}] {100*((addr+64)/FILE_LEN):.2f}%", end='\r')
    print()

    # Read EEPROM and verify contents
    for addr in range(0, FILE_LEN, 64):
        new_data = eeprom._read_page(addr)
        should_data = buf[addr:addr+64]
        print(f"Verifying... [0x{addr:04x}] {100*((addr+64)/FILE_LEN):.2f}%", end='\r')
        if new_data != should_data:
            print(f"\nVerification failed! address 0x{addr:04x}, got {new_data!r}, instead of {should_data!r}")
            exit(1)
    print()
    # eeprom.hexdump()


def main_cli():
    import argparse
    p = argparse.ArgumentParser(
        add_help=True,
        prog="28c256-rw.py",
        description="Read/Write model 28c265 EEPROMs.",
    )
    p.add_argument("-v", "--verbose", help="show more output", action="store_true", default=False)
    mode = p.add_argument_group("required arguments")
    mode_required = mode.add_mutually_exclusive_group(required=True)
    mode_required.add_argument("--download", "-D",
                   metavar="OUTFILE",
                   type=argparse.FileType('wb'),
                   help="download 32768 bytes from the EEPROM"
                   )
    mode_required.add_argument("--upload", "-U",
                   metavar="INFILE",
                   type=argparse.FileType('rb'),
                   help="upload 32768 bytes to the EEPROM"
                   )
    args = p.parse_args()
    if args.upload != None:
        mode = "upload"
    elif args.download != None:
        mode = "download"

    print(mode)


if __name__ == "__main__":
    main_cli()
