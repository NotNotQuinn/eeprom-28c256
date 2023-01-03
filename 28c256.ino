// EEPROM (28C256) datasheet: https://eater.net/datasheets/28c256.pdf
// This is an EEPROM read/writer. :)

// #define USE_CAMINO

#ifdef USE_CAMINO
#include <Camino.h>
#endif

#include "vec/vec.h"
#include "vec/vec.c"

// My custom magic numbers
#define EEPROM01 22
#define EEPROM02 23
#define EEPROM03 24
#define EEPROM04 25
#define EEPROM05 26
#define EEPROM06 27
#define EEPROM07 28
#define EEPROM08 29
#define EEPROM09 30
#define EEPROM10 31
#define EEPROM11 32
#define EEPROM12 33
#define EEPROM13 34
//      EEPROM14 ~~
#define EEPROM15 47
#define EEPROM16 46
#define EEPROM17 45
#define EEPROM18 44
#define EEPROM19 43
#define EEPROM20 42
#define EEPROM21 41
#define EEPROM22 40
#define EEPROM23 39
#define EEPROM24 38
#define EEPROM25 37
#define EEPROM26 36
#define EEPROM27 35
//      EEPROM28 ~~

// NOP instruction :) for nanosecond delays
// Each should be 62.5 ns @ 16MHz clock
// (according to the internet)
#define NOP __asm__("nop\n\t")

// The maximum valid value for an address.
#define ADDR_MAX 0x7FFF

// To be able to write to the EEPROM, the write enable pin must be low
// Reference the datasheet for more information.
#define WRITE_ENABLE EEPROM27

// This pin must be low for the chip to work.
// Reference the datasheet for more information.
#define CHIP_ENABLE EEPROM20

// For the EEPROM to output anything to the IO pins, this pin must be low.
// Reference the datasheet for more information.
#define OUTPUT_ENABLE EEPROM22

// A list of all address pins in order from A0 to A14
byte ADDR_PINS[] = {
	EEPROM10, EEPROM09, EEPROM08, EEPROM07, EEPROM06, EEPROM05, EEPROM04, EEPROM03,
	EEPROM25, EEPROM24, EEPROM21, EEPROM23, EEPROM02, EEPROM26, EEPROM01
};
#define ADDR_PINS_LEN 15

// This is a list of All IO pins that are part of one group (an array :) )
// in order from IO0 to IO7
byte IO_PINS[] = {
	EEPROM11, EEPROM12, EEPROM13, EEPROM15, EEPROM16, EEPROM17, EEPROM18, EEPROM19
};
#define IO_PINS_LEN 8

// Stores the current mode of the IO pins
byte IO_PINS_MODE = INPUT;


typedef struct {
	// signals if this write job is a page write.
	bool is_page_write;
	// if is_page_write, then address must be divisible by 64,
	// regardless, it must be less than 0x8000.
	unsigned int address;
	// if is_page_write, then data is a 64 byte array.
	// otherwise, it is an array with a single byte.
	byte* data;
} write_job;
// A vector of write jobs.
#define vec_write_job write_job*

bool has_write_job = false;
vec_write_job write_jobs = vector_create();

void hexdump() {
#ifdef USE_CAMINO
	// Hexdump uses the serial port, therefor
	// it is not available while using camino
	return;
#else
	for (unsigned int i = 0U; i < 0x0100U; i += 16U) {
		char *msg = hexdump16(i);
		Serial.println(msg);
		free(msg);
	}
	Serial.println("=-------------------------------------------------------------------------=");
#endif
}

// Returns 80 byte (allocated) string formatted in a hexdump manner :)
char *hexdump16(unsigned int address) {
	byte data[16];
	char visualized[16];
	for (unsigned int j = 0U; j < 16U; j++) {
		byte b = readEEPROM(address+j);
		data[j] = b;
		visualized[j] = (isPrintable(b) && !isControl(b)) ? b : '.';
	}

	char *msg = malloc(80);
	sprintf(msg,
		"%04x:  %02x %02x %02x %02x %02x %02x %02x %02x  %02x %02x %02x %02x %02x %02x %02x %02x  |%.16s|",
		address,
		data[ 0], data[ 1], data[ 2], data[ 3], data[ 4], data[ 5], data[ 6], data[ 7],
		data[ 8], data[ 9], data[10], data[11], data[12], data[13], data[14], data[15], visualized
	);

	return msg;
}

// https://stackoverflow.com/questions/111928/is-there-a-printf-converter-to-print-in-binary-format#3208376
#define BYTE_TO_BINARY_PATTERN "%c%c%c%c%c%c%c%c"
#define BYTE_TO_BINARY(byte)  \
  (byte & 0x80 ? '1' : '0'), \
  (byte & 0x40 ? '1' : '0'), \
  (byte & 0x20 ? '1' : '0'), \
  (byte & 0x10 ? '1' : '0'), \
  (byte & 0x08 ? '1' : '0'), \
  (byte & 0x04 ? '1' : '0'), \
  (byte & 0x02 ? '1' : '0'), \
  (byte & 0x01 ? '1' : '0') 

void setup() {
	// Default control pin settings: (set before pins are enabled)
	digitalWrite(CHIP_ENABLE, LOW); // enable the chip
	digitalWrite(OUTPUT_ENABLE, LOW); // enable output from the chip
	digitalWrite(WRITE_ENABLE, HIGH); // disable writing to the chip
  digitalWrite(LED_BUILTIN, HIGH); // extra 5v pin

	// Control pins: always output
	pinMode(CHIP_ENABLE, OUTPUT);
	pinMode(OUTPUT_ENABLE, OUTPUT);
	pinMode(WRITE_ENABLE, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

	// Address pins: always output
	for (int i = 0; i < ADDR_PINS_LEN; i++) {
		pinMode(ADDR_PINS[i], OUTPUT);
	}

	// Initialize data pins for reading
	for (int i = 0; i < IO_PINS_LEN; i++) {
		pinMode(IO_PINS[i], INPUT);
	}
	IO_PINS_MODE = INPUT;

	// byte msg[4] = {0xde, 0xad, 0xbe, 0xef};
	// for (unsigned int i = 0; i < 0x300U; i++) {
	// 	writeEEPROM(i, msg[i%4]);
	// }

	// delay(100);

#ifdef USE_CAMINO
	camino.begin(115200);
#else
	Serial.begin(115200);
	byte msg[4] = {0x00, 0xff, 0x00, 0x00};
	// byte data[64];
	// for (int i = 0; i < 64; i++) {
	// 	data[i] = msg[i%4];
	// }
	// writeEEPROMPage(0x00, data);
	// writeEEPROMPage(0x40, data);
	// writeEEPROMPage(0x80, data);
	// writeEEPROMPage(0xc0, data);
	// hexdump();
  #define TRIAL_COUNT 64
  unsigned int count = 0;
  for (unsigned int i = 0; i < TRIAL_COUNT; i++)
  for (unsigned int a = 0; a < 0x100; a++) {
    byte got = readEEPROM(a);
    byte expected = msg[a%4];

    if (got != expected) {
      if (expected == 0x00) {
        Serial.print("Expected 0, got ");
        Serial.println(got);
      }
      count++;
      char text[40];
      byte flipped = got ^ expected;
      sprintf(text, "%04x: Expected %02x, got %02x.", a, expected, got);
      Serial.print(text);
      Serial.print("   (");
      for (int i = 0; i < 8; i++) {
        Serial.print(flipped & 0x80 ? '1' : '0');
        flipped <<= 1;
      }
      Serial.println(" flipped)");
    }
  }

  Serial.print("Done! ");
  Serial.print((double(count)/(TRIAL_COUNT*64.0)) * 100);
  Serial.print("% (");
  Serial.print(count);
  Serial.print("/");
  Serial.print(TRIAL_COUNT*64);
  Serial.print(") errors avg over ");
  Serial.print(TRIAL_COUNT);
  Serial.println(" trials.");
#endif
}

void loop() {
	if (!has_write_job) return;

	int num_items = vector_size(write_jobs);
	if (num_items == 0) {
		has_write_job = false;
		return;
	}
	// Disable interrupts while messing with write_jobs array
	// because jobs are added through interrupts, and we don't want that to
	// happen in the middle
	cli(); // disable interrupts ("cli()" == "clear" the "interrupts" flag)
	write_job job = write_jobs[0];
	vector_remove(&write_jobs, 0);
	sei(); // re-enable interrupts ("sei()" == "set" the "interrupts" flag)

	if (job.is_page_write) {
		writeEEPROMPage(job.address, job.data);
	} else {
		writeEEPROM(job.address, job.data[0]);
	}

	free(job.data);
}

// Sets the address pins to the address provided
void writeAddress(unsigned int addr) {
	for (int i = 0; i < ADDR_PINS_LEN; i++) {
		digitalWrite(ADDR_PINS[i], addr & 1);
		addr >>= 1;
	}
}

void pinModeIO(byte mode) {
	if (IO_PINS_MODE == mode) return;

	for (int i = 0; i < IO_PINS_LEN; i++) {
		pinMode(IO_PINS[i], mode);
	}

	IO_PINS_MODE = mode;
}

byte readEEPROM(unsigned int address) {
	// Go into read mode
	digitalWrite(OUTPUT_ENABLE, LOW);
	digitalWrite(WRITE_ENABLE, HIGH);

	// Data pins: input for reading
	pinModeIO(INPUT);

	// Set the address
	writeAddress(address);

	// Wait >=350 ns before reading (~375 ns)
	NOP; NOP; NOP; // 3 * 62.5 ns @ 16,000,000hz
	NOP; NOP; NOP; // 3 * 62.5 ns @ 16,000,000hz

	// Serial.print("Reading: ");
	byte data;
	// Read the IO pins
	for (int i = IO_PINS_LEN-1; i >= 0; i--) {
		byte bit = digitalRead(IO_PINS[i]);
		data = (data << 1) | bit;
		// Serial.print(bit);
	}
	// Serial.println();

	return data;
}

void writeEEPROM(unsigned int address, byte data) {
	// Configure initial control pins
	digitalWrite(OUTPUT_ENABLE, HIGH);
	digitalWrite(WRITE_ENABLE, HIGH);
	cli(); // No interrupts can happen, because reads will mess this up.
	// Set the address
	writeAddress(address);

	// Data pins: output for writing
	pinModeIO(OUTPUT);
	// Write the data
	for (int i = 0; i < IO_PINS_LEN; i++) {
		digitalWrite(IO_PINS[i], data & 1);
		data >>= 1;
	}

	sei();

	digitalWrite(WRITE_ENABLE, LOW);
	delay(1);
	digitalWrite(WRITE_ENABLE, HIGH);
	delay(10);
}

void writeEEPROMPage(unsigned int address, byte* data) {
	if (address % 0x40 != 0) {
		return; // idk if this is a good idea
	}

	cli();
	// Configure initial control pins
	digitalWrite(OUTPUT_ENABLE, HIGH);
	digitalWrite(WRITE_ENABLE, HIGH);


	// Data pins: output for writing
	pinModeIO(OUTPUT);

	for (int i = 0; i < 64; i++) {
		byte currentData = data[i];
		writeAddress(address+i);
		digitalWrite(WRITE_ENABLE, LOW);
		// Write data
		for (int i = 0; i < IO_PINS_LEN; i++) {
			digitalWrite(IO_PINS[i], currentData & 1);
			currentData >>= 1;
		}
		// wait >= 50ns
		NOP; NOP; NOP;
		digitalWrite(WRITE_ENABLE, HIGH);
		// High pulse must be >= 50ns
	}
	sei();

	// Wait up to 10 ms for the write cycle to complete
	delay(10);
}

#ifdef USE_CAMINO
void readEEPROM_callable(byte dataLength, byte data[]) {
	returns(readEEPROM(data[0] | data[1] << 8));
}

void writeEEPROM_callable(byte dataLength, byte dataArray[]) {
	// Copy a single tiny byte to its own array, how sweet.
	// This is needed because the same memory is used for all callables
	byte* data = malloc(1);
	if (data == NULL) {
		// OOM
		returns("[arduino error] OOM");
		return;
	}
	data[0] = dataArray[2];

	// Note: the lifetime of temp is not guaranteed to be long
	// don't use this pointer after instantiation
	write_job* temp = vector_add_asg(&write_jobs);
	temp->address = dataArray[0] | dataArray[1] << 8;
	temp->data = data;
	temp->is_page_write = false;
	// temp = NULL; // commented out for performance (does it matter tho?)
	has_write_job = true;
}

void hexdump16_callable(byte dataLength, byte data[]) {
	unsigned int address = data[0] | data[1] << 8;
	if (address % 16 != 0) {
		returns("[arduino error] address must be divisible by 16!");
		return;
	}
	char* msg = hexdump16(address);
	returns(msg);
	free(msg); // BE FREE LITTLE ONES
}

void hexdump32_callable(byte dataLength, byte data[]) {
	unsigned int address = data[0] | data[1] << 8;
	if (address % 32 != 0) {
		returns("[arduino error] address must be divisible by 32!");
		return;
	}

	char* msg1 = hexdump16(address);
	char* msg2 = hexdump16(address+16);

	// Join the two strings with newline.
	char big_msg[160];

	// Copy string 1
	int i;
	for (i = 0; msg1[i] != 0; i++) {
		big_msg[i] = msg1[i];
	}
	free(msg1);

	// Newline
	big_msg[i] = '\n';
	i++;

	// Copy string 2
	int j;
	for (j = 0; msg2[j] != 0; j++) {
		big_msg[i+j] = msg2[j];
	}
	free(msg2);

	// Null termination
	big_msg[i+j] = 0;

	returns(big_msg);
}

void readEEPROMPage_callable(byte dataLength, byte dataArray[]) {
	unsigned int address = dataArray[0] | dataArray[1] << 8;
	if (address % 64 != 0) {
		// No data should cause some sort of error on the other side.
		return;
	}

	byte outgoing[64];
	for (int i = 0; i < 64; i++) {
		outgoing[i] = readEEPROM(address+i);
	}

	returns(64, outgoing);
}

// NOTE: UNTESTED
void writeEEPROMPage_callable(byte dataLength, byte dataArray[]) {
	unsigned int address = dataArray[0] | dataArray[1] << 8;
	if (address % 64 != 0) {
		// TODO: Find a better way to express there was an error
		return;
	}

	// This is needed because the same memory is used for all callables
	byte* data = malloc(64);
	if (data == NULL) {
		// OOM
		returns("arduino OOM");
		return;
	}
	byte* incoming = &dataArray[2];
	for (int i = 0; i < 64; i++) {
		data[i] = incoming[i];
	}

	// Note: the lifetime of temp is not guaranteed to be long
	// don't use this pointer after instantiation
	write_job* temp = vector_add_asg(&write_jobs);
	temp->address = address;
	temp->data = data;
	temp->is_page_write = true;
	// temp = NULL; // commented out for performance (does it matter tho?)
	has_write_job = true;
}

// temp
void noop(byte dataLength, byte data[]) {}
BEGIN_CALLABLES {
	// read takes in address (2 bytes) and returns data (1 byte)
	{"read", readEEPROM_callable},
	// write takes in address (2 bytes) and data (1 byte)
	{"write", writeEEPROM_callable},
	// readPage takes in address (2 bytes, must be divisible by 64) and returns 64 bytes of data
	{"read_page", readEEPROMPage_callable},
	// writePage takes in address (2 bytes, must be divisible by 64) and 64 bytes of data
	{"write_page", writeEEPROMPage_callable},
	{"hexdump16", hexdump16_callable},
	{"hexdump32", hexdump32_callable},
} END_CALLABLES;
#endif
