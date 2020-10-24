#!/usr/bin/env python3

import numpy as np
import serial 
import struct 
import time 
import psycopg2 as psql 
import smbus2 
import bme280 
import datetime 
import sys 

class PMS5003:
	def __init__(self, serial, startup_delay):
		self.serial = serial # serial corresponding to PMS5003 sensor 		
		# startup delay recommended to allow fans to come up to speed 
		self.startup_delay = startup_delay # seconds, time to wait after Wake() is called 
		self.cmd_delay = .5 # seconds, delay after issuing a command to PMS5003 
		self.timeout = 5 # seconds, time to wait for the sensor to send its data 

		# set default sensor mode 
		self.Wake() 
		self.SetActive() 

	def Sleep(self):
		''' tell PMS5003 to enter sleep mode
			sleep mode saves power and extends longevity of sensor 
			sensor does not take measurements in sleep mode 
		''' 
		self.serial.write([0x42, 0x4D, 0xE4, 0x00, 0x00, 0x01, 0x73]) 
		self.status = 'ASLEEP'
		time.sleep(self.cmd_delay) 
		self.DrainBuffer()

	def Wake(self):
		''' tell PMS5003 to leave sleep mode ''' 
		self.serial.write([0x42, 0x4D, 0xE4, 0x00, 0x01, 0x01, 0x74]) 
		self.status = 'AWAKE'
		time.sleep(self.startup_delay) 
		self.DrainBuffer()

	def SetPassive(self):
		''' set the PMS5003 to passive mode 
			in passive mode, the PMS5003 takes and sends data only when requested 
			request data by calling RequestData
		''' 
		self.serial.write([0x42, 0x4D, 0xE1, 0x00, 0x00, 0x01, 0x70]) 
		self.mode = 'PASSIVE'
		time.sleep(self.cmd_delay) 

	def SetActive(self):
		''' set the PMS5003 to active mode 
			in active mode, the PMS5003 takes and sends data constantly 
			active mode is liable to quickly fill the serial receive buffer 
				make sure to be constantly reading the data or else the data could become corrupted
		''' 
		self.serial.write([0x42, 0x4D, 0xE1, 0x00, 0x01, 0x01, 0x71]) 
		self.mode = 'ACTIVE' 
		time.sleep(self.cmd_delay) 

	def RequestData(self):
		''' request the PMS5003 take and send the data for a single sensor reading 
			when in passive mode 
		''' 
		self.serial.write([0x42, 0x4D, 0xE2, 0x00, 0x00, 0x01, 0x71]) 
		time.sleep(self.cmd_delay) 

	def Read(self):
		''' non-blocking function to read the PMS5003 data streamed over serial 
			the PMS5003 message is 32 bytes long and begins with b'0x42' and b'0x4d' 
			this function waits until b'0x42' and b'0x4d' are present in the buffer 
				and then reads and parses the 32B message 
			last 2 bytes of the message are a "checksum" 
				byte wise sum of the first 30 bytes must match the last 2 bytes 
				if this is not true, then an error in reading the data occurred 
		''' 

		# search for start of PMS5003 32B message 
		st = time.time() 
		c = b'' 
		found = False
		while (time.time() - st < self.timeout):
			c = ord(self.serial.read())
			if (c==0x42):
				found = True
				break 

		# if not found within self.timeout seconds raise error 
		if not(found):
			raise RuntimeError('start byte not found') 

		# make sure the second byte of the message matches the expected 2nd byte 
		if (ord(self.serial.read())!=0x4d):
			raise RuntimeError('second start byte not found') 

		# read the next 30 bytes 
		r = self.serial.read(30)
		if (len(r)!=30):
			raise RuntimeError('read wrong length')

		# parse data into 15 2 byte integers 
		data = struct.unpack('>15H', r) 

		# compute sum of data 
		s = 0 
		for i in range(len(r)-2):
			s += r[i] 

		# compare checksum (test for validity of recieved data) 
		if (s + 0x42 + 0x4d != data[-1]):
			raise RuntimeError('checksum problem') 

		# extract data into dictionary 
		d = {} 
		d['pm_st'] = list(data[1:4])
		d['pm_en'] = list(data[4:7])
		d['hist'] = list(data[7:13])
		return d 

	def AveragedRead(self, avg_time=10):
		''' read the PMS5003 for avg_time seconds and average the data over that time period ''' 

		# wake if needed 
		prev_status = self.status 
		if (self.status == 'ASLEEP'):
			self.Wake() 

		# take measurements over avg_time seconds 
		start = time.time() 
		N = 1 # number of measurements in the time frame 
		data = self.Read() 
		while (time.time() - start < avg_time):
			tmp = self.Read() 
			N += 1 
			# sum data 
			for key in data:
				for i in range(len(data[key])):
					data[key][i] += tmp[key][i] 

		# divide by number of measurements to get average 
		for key in data:
			for i in range(len(data[key])):
				data[key][i] = int(round(float(data[key][i])/N))

		# put back to sleep if started asleep 
		if (prev_status == 'ASLEEP'):
			self.Sleep() 

		return data 

	def DrainBuffer(self):
		''' reads all the data from the serial buffer 
			helps prevent data corruption by preventing the buffer from overflowing 
		''' 
		while (self.serial.in_waiting>0):
			self.serial.read() 

# setup PMS5003 objects 
ser = serial.Serial(port='/dev/serial0', baudrate=9600) 
pms = PMS5003(ser, startup_delay=20) 
pms.Sleep() 
avg_time = 10 # seconds, time to read PMS sensor 

# set BME280 objects 
port = 1 
address = 0x76 
bus = smbus2.SMBus(port) 
calibration = bme280.load_calibration_params(bus, address) 

# PSQL table for PMS5003 data 
conn_pms = psql.connect(database='pms', user='pi', password='rpi4')
cur_pms = conn_pms.cursor()

# PSQL table for BME280 data 
conn_bme = psql.connect(database='bme', user='pi', password='rpi4') 
cur_bme = conn_bme.cursor() 

while True:
	# read PMS5003 AQI data and push to PSQL table 
	data = pms.AveragedRead(avg_time)  
	cur_pms.execute('insert into pi' + ''' (t, pm10_st, pm25_st, pm100_st, 
		pm10_en, pm25_en, pm100_en, 
		p1, p2, p3, p4, p5, p6) values 
		(now(), {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})'''.format(
			data['pm_st'][0], data['pm_st'][1], data['pm_st'][2], 
			data['pm_en'][0], data['pm_en'][1], data['pm_en'][2], 
			data['hist'][0], data['hist'][1], data['hist'][2], 
			data['hist'][3], data['hist'][4], data['hist'][5]
			))
	conn_pms.commit()

	# read BME280 temperature/pressure/humidity data and push to PSQL table 
	bme_data = bme280.sample(bus, address, calibration) 
	cur_bme.execute('insert into pi' + ''' (t, temperature, humidity, pressure) values 
		(now(), {}, {}, {})'''.format(bme_data.temperature*9/5+32, bme_data.humidity, bme_data.pressure))
	conn_bme.commit() 

	# sleep for 30 seconds to get ~1 reading per minute 
	time.sleep(30)
