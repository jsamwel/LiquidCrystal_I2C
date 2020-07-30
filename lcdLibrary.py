
import smbus
import time

class lcd_I2C:
	def __init__(self, Cols, Lines, ADDR):
		self.ADDR  = ADDR 	# I2C device address
		self.Cols = Cols	# Maximum characters per line
		self.Lines = Lines 	# Maximum number of lines
		self.dotsize = 0

		# Define some device constants
		self.CHR = 1 # Mode - Sending data
		self.CMD = 0 # Mode - Sending command
		
		# Define commands
		self.commands = {
			"CLEARDISPLAY" : 0x01,
			"RETURNHOME" : 0x02,
			"ENTRYMODESET" : 0x04,
			"DISPLAYCONTROL" : 0x08,
			"CURSORSHIFT" : 0x10,	
			"FUNCTIONSET" : 0x20,
			"SETCGRAMADDR" : 0x40,
			"SETDDRAMADDR" : 0x80
		}
		
		# flags for display entry mode
		self.displayEntrySet = {
			"ENTRYRIGHT" : 0x00,
			"ENTRYLEFT" : 0x02,
			"ENTRYSHIFTINCREMENT" : 0x01,
			"ENTRYSHIFTDECREMENT" : 0x00
		}
		
		# flags for display on/off control
		self.displayControlSet = {
			"DISPLAYON" : 0x04,
			"DISPLAYOFF" : 0x00,
			"CURSORON" : 0x02,
			"CURSOROFF" : 0x00,
			"BLINKON" : 0x01,	
			"BLINKOFF" : 0x00
		}
		
		# flags for display/cursor shift
		self.displayCursorSet = {
			"DISPLAYMOVE" : 0x08,
			"CURSORMOVE" : 0x00,
			"MOVERIGHT" : 0x04,
			"MOVELEFT" : 0x00
		}

		# flags for function set
		self.functionSet = {
			"8BITMODE" : 0x10,
			"4BITMODE" : 0x00,
			"2LINE" : 0x08,
			"1LINE" : 0x00,
			"5x10DOTS" : 0x04,
			"5x8DOTS" : 0x00
		}

		# flags for backlight control
		self.backlightControl = {
			"BACKLIGHT" : 0x08,
			"NOBACKLIGHT" : 0x00
		}
		
		self.__displayFunction = self.functionSet["4BITMODE"] | self.functionSet["5x8DOTS"]
		
		if self.Lines > 1:
			self.__displayFunction |= self.functionSet["2LINE"]
		else:
			self.__displayFunction |= self.functionSet["1LINE"]
			
		# for some 1 line displays you can select a 10 pixel high font
		if self.dotsize != 0 and self.Lines == 1:
			self.__displayFunction |= self.functionSet["5x10DOTS"]
			
		self.__displayMode = self.displayEntrySet["ENTRYLEFT"] | self.displayEntrySet["ENTRYSHIFTDECREMENT"]
		self.__displayControl = self.displayControlSet["DISPLAYON"] | self.displayControlSet["CURSOROFF"]
		self.__displayControl |= self.displayControlSet["BLINKOFF"]
		
		self.__backlight = self.backlightControl["NOBACKLIGHT"]
		
		self.ENABLE = 0b00000100 # Enable bit
		
		self.E_DELAY = 0.0005
		self.E_PULSE = 0.0005

		self.bus = smbus.SMBus(1) # Rev 2 Pi uses 1

	def init(self):	
		displayCommand = self.commands["DISPLAYCONTROL"] | self.__displayControl
		functionCommand = self.commands["FUNCTIONSET"] | self.__displayFunction
		entryCommand = self.commands["ENTRYMODESET"] | self.__displayMode
	
		self.sendCommand(0x33) 							# 110011 Initialise
		self.sendCommand(0x32) 							# 110010 Initialise
		self.sendCommand(entryCommand)					# 000110 Cursor move direction
		self.sendCommand(displayCommand) 				# 001100 Display On,Cursor Off, Blink Off
		self.sendCommand(functionCommand) 				# 101000 Data length, number of lines, font size
		self.sendCommand(self.commands["CLEARDISPLAY"]) # 000001 Clear display
		time.sleep(self.E_DELAY)

	def sendString(self, message):

		message = message.ljust(self.Cols," ")

		for i in range(self.Cols):
			self.sendData(message[i])
	
	def setCursor(self, col, row):
		row_offsets = [0x00, 0x40, 0x14, 0x54]
		
		if row > self.Lines:
			row = self.Lines-1
			
		self.sendCommand(self.commands["SETDDRAMADDR"] | (col + row_offsets[row]));
	
	def clearScreen(self):
		self.sendCommand(self.commands["CLEARDISPLAY"])
		
	def home(self):
		self.sendCommand(self.commands["RETURNHOME"])
		
	def setBackLight(self, value):
		if value:
			self.backlight()
		else:
			self.noBacklight()
	
	# Functions for display control
	def noDisplay(self):
		self.__displayControl &= ~self.displayControlSet["DISPLAYON"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def display(self):
		self.__displayControl |= self.displayControlSet["DISPLAYON"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def noCursor(self):
		self.__displayControl &= ~self.displayControlSet["CURSORON"];
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def cursor(self):
		self.__displayControl |= self.displayControlSet["CURSORON"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def noBlink(self):
		self.__displayControl &= ~self.displayControlSet["BLINKON"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def blink(self):
		self.__displayControl |= self.displayControlSet["BLINKON"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)
		
	def noBacklight(self):
		self.__backlight = self.backlightControl["BACKLIGHT"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)

	def backlight(self):
		self.__backlight = self.backlightControl["NOBACKLIGHT"]
		self.sendCommand(self.commands["DISPLAYCONTROL"] | self.__displayControl)
	
	# mid level functions for sending commands / data	
	def sendData(self, data):
		self.__sendByte(ord(data),self.CHR)
		
	def sendCommand(self, cmd):
		self.__sendByte(cmd, self.CMD)
	
	# Low level function for communication		
	def __sendByte(self, bits, mode):
		bits_high = mode | (bits & 0xF0) | self.__backlight
		bits_low = mode | ((bits<<4) & 0xF0) | self.__backlight

		self.bus.write_byte(self.ADDR, bits_high)
		self.toggle_enable(bits_high)

		self.bus.write_byte(self.ADDR, bits_low)
		self.toggle_enable(bits_low)
		
	def toggle_enable(self, bits):
		time.sleep(self.E_DELAY)
		self.bus.write_byte(self.ADDR, (bits | self.ENABLE))
		time.sleep(self.E_PULSE)
		self.bus.write_byte(self.ADDR,(bits & ~self.ENABLE))
		time.sleep(self.E_DELAY)
			
