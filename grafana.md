# Grafana
Grafana is a dashboard frontend for the postgres database. Queries can be entered in the graphical interface and plotted. The raspberry pi hosts the grafana server. 

# Accessing Grafana 
Find the raspberry pi's local ip address. You could check your router's list of connect devices. The raspberry pi should show up as aqpi. Alternatively, plug the raspberry pi into a monitor and using a keyboard open the terminal application and run `ip addr show`. If connected over wifi, use the ip address listed under `wlan0`. If over ethernet, use `eth0`. Enter the IP address into your browser while connected to the same network the raspberry pi is on. 

# Dashboard Setup
I have added four plots and three statistics to the grafana dashboard. The plots of temperature, humidity, and AQI use the timescaledb function `time_bucket` to plot averages over a window dependent interval. The width of the interval is determined by the `PPI` (points per interval) variable accessed by clicking the gear icon in top right corner of the dashboard. The default is to plot 50 points. Some amount of averaging is required to smooth the sensor data. The fourth plot, "Sensor Readings per Hour", should reliably read 60. This indicates the raspberry pi is reading the sensors once per minute without errors. This frequency is defined in `read_sensors.py`. 