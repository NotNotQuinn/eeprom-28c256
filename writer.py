import camino
from typing import List
# Little endian (least significant byte is stored at lowest address)


class EEPROM_Programmer():
    MAX_ADDRESS = 0x7FFF
    def __init__(self, arduino: camino.Arduino):
        self.arduino = arduino

    ### UNDERLYING ARDUINO COMMUNICATIONS ###

    def _read(self, address: int):
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        return self.arduino.read(address & 0xFF, address >> 8, out=int)

    def _write(self, address: int, byte: int):
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if byte > 0xFF or byte < 0:
            raise ValueError(f"Byte out of range 0x00-0xFF: got 0x{byte:04x}")

        return self.arduino.write(address & 0xFF, address >> 8, byte)

    def _hexdump16(self, address: int):
        """Returns a hexdump string, or a string starting with "[arduino error]" describing the error."""
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 16 != 0:
            raise ValueError(f"Address must be divisible by 16: got 0x{address:04x}")

        return self.arduino.hexdump16(address & 0xFF, address >> 8, out=str)

    def _hexdump32(self, address: int):
        """Returns a two line hexdump string, or a string starting with "[arduino error]" describing the error."""
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 32 != 0:
            raise ValueError(f"Address must be divisible by 32: got 0x{address:04x}")

        return self.arduino.hexdump32(address & 0xFF, address >> 8, out=str)

    def _read_page(self, address: int):
        """Returns None on errors within the arduino."""
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 64 != 0:
            raise ValueError(f"Address must be divisible by 64: got 0x{address:04x}")

        return self.arduino.read_page(address & 0xFF, address >> 8, out=bytes)

    def _write_page(self, address: int, data: List[int]):
        """Returns None on success, returns a string for errors within the arduino."""
        if address > self.MAX_ADDRESS or address < 0:
            raise ValueError(f"Address out of range 0x0000-{hex(self.MAX_ADDRESS)}: got 0x{address:04x}")

        if address % 64 != 0:
            raise ValueError(f"Address must be divisible by 64: got 0x{address:04x}")

        if len(data) != 64:
            raise ValueError(f"Data array must be length 64: got {len(data)}")

        return self.arduino.write_page(address & 0xFF, address >> 8, *data, out=str)

    def _echo(self, data: bytes):
        """Returns the bytes you send."""

        return self.arduino.echo(data)


connection = camino.SerialConnection(port='COM3', baud=115200)
eeprom = EEPROM_Programmer(camino.Arduino(connection))

# eeprom._write(0, 0xde)
# print(eeprom._hexdump32(0x00))
# for i in range(0x0000, 0x8000, 0x20):
#     print(eeprom._hexdump32(i))

# print(f'{eeprom._write_page(0, [0xc0, 0xff, 0xee, 0x00] * 0x10) = }')

for a in range(0x0000, 0x80, 0x40):
    # print(eeprom._hexdump32(a))
    # print(eeprom._hexdump32(a+0x20))
    d = eeprom._read_page(a)
    print(
        f"{a+0x00:04x}:  {d[0+0x00]:02x} {d[1+0x00]:02x} {d[2+0x00]:02x} {d[3+0x00]:02x} {d[4+0x00]:02x} {d[5+0x00]:02x} {d[6+0x00]:02x} {d[7+0x00]:02x}  {d[8+0x00]:02x} {d[9+0x00]:02x} {d[10+0x00]:02x} {d[11+0x00]:02x} {d[12+0x00]:02x} {d[13+0x00]:02x} {d[14+0x00]:02x} {d[15+0x00]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x00:0x10]])}|\n"
        f"{a+0x10:04x}:  {d[0+0x10]:02x} {d[1+0x10]:02x} {d[2+0x10]:02x} {d[3+0x10]:02x} {d[4+0x10]:02x} {d[5+0x10]:02x} {d[6+0x10]:02x} {d[7+0x10]:02x}  {d[8+0x10]:02x} {d[9+0x10]:02x} {d[10+0x10]:02x} {d[11+0x10]:02x} {d[12+0x10]:02x} {d[13+0x10]:02x} {d[14+0x10]:02x} {d[15+0x10]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x10:0x20]])}|\n"
        f"{a+0x20:04x}:  {d[0+0x20]:02x} {d[1+0x20]:02x} {d[2+0x20]:02x} {d[3+0x20]:02x} {d[4+0x20]:02x} {d[5+0x20]:02x} {d[6+0x20]:02x} {d[7+0x20]:02x}  {d[8+0x20]:02x} {d[9+0x20]:02x} {d[10+0x20]:02x} {d[11+0x20]:02x} {d[12+0x20]:02x} {d[13+0x20]:02x} {d[14+0x20]:02x} {d[15+0x20]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x20:0x30]])}|\n"
        f"{a+0x30:04x}:  {d[0+0x30]:02x} {d[1+0x30]:02x} {d[2+0x30]:02x} {d[3+0x30]:02x} {d[4+0x30]:02x} {d[5+0x30]:02x} {d[6+0x30]:02x} {d[7+0x30]:02x}  {d[8+0x30]:02x} {d[9+0x30]:02x} {d[10+0x30]:02x} {d[11+0x30]:02x} {d[12+0x30]:02x} {d[13+0x30]:02x} {d[14+0x30]:02x} {d[15+0x30]:02x}  |{''.join([chr(c) if c >= 32 and c < 127 else '.' for c in d[0x30:0x40]])}|"
    )


# If packet size becomes a real problem:

# SUBJECT: Discussion/Question: How plausible is it to increase packet size for a custom build?
#
# Hello, I am interested in increasing the packet size for Camino (for a custom build). It isn't mission critical but it would be a nice-to-have for a personal project.
# Also, I think it will be a fun challenge. (I would imagine unreliable data would be the trade off)
#
# I want to try to increase it maybe 2^16 bytes (or at least 2^9), how technically plausible is this from a hardware point of view?
# I don't know what goes into a decision to pick a packet size, could you share the benefits of using 256 bytes?
#
# I also noticed in the readme:
# > It is a known issue that packets with more than around 100 bytes of data are unreliable in some setups.
#
# I am curious what contributes to the unreliability, and what setups are effected.
