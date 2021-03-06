# AQPy 
Repository for scripts and files to read the PMS5003 air quality index sensor and the BME280 temperature/pressure/humidity sensor from a Raspberry Pi. `systemctl` is used to manage the `read_sensors.py` python script. The data is stored into a postgresql database with the timescaledb extension. From there, Grafana is used to plot the data over time. 

# Hardware 
## PMS5003 
The PMS5003 is assumed to be connected over serial in the `/dev/serial0` position. See the [PMS5003 manual](https://www.aqmd.gov/docs/default-source/aq-spec/resources-page/plantower-pms5003-manual_v2-3.pdf) for wiring diagram of the PMS5003. The `pinout` command on the Raspberry Pi OS will show the function of the GPIO pins. 

| PMS Wire No. | Raspberry Pi Pin No. |
| ------------ | -------------------- |
| VCC (1) | 2 | 
| GND (2) | 6 | 
| SET (3) | unused | 
| RX (4) | 8 | 
| TX (5) | 10 |
| RESET (6) | unused | 

## BME280 
The BME280 is assumed to be connected with I2C. 
| BME280 Terminal | Raspberry Pi Pin No. |
| --------------- | -------------------- |
| 3V3 | 1 | 
| GND | 9 | 
| SCL | 5 | 
| SDA | 3 | 

# Installation 
1. copy `aqi.service` to `/etc/systemd/system` with `sudo cp aqi.service /etc/systemd/system` 
2. run `sudo systemctl enable aqi` to start `aqi.service` at boot 
3. either `sudo reboot` or `sudo systemctl start aqi` to start the service 
4. make sure its running with `systemctl status aqi`. It will say "active (running)" if things are working properly. 

# Maintenance 
`systemctl` stores logs that can be accessed through `journalctl -u aqi`. `journalctl` uses the `less` linux utility to show the logs. A brief summary of `aqi.service` can be obtained by running `systemctl status aqi`. If the sensors stop working (or I didn't code things robustly enough) the python runtime errors will be recorded by `systemctl`. If the `read_sensors.py` script fails, `systemctl` will automatically restart it however if it fails too many times it will wait longer and longer between retries. 