In the Pulse project, my primary responsibility was developing the matching algorithm that determines compatibility between two individuals. 
I fetched heart rate and conversation scores from the database, which were collected through wearable wristbands and processed using Google Cloud Speech-to-Text. 
Using this data, I designed and implemented the algorithm to analyze trends and combine the heart rate and conversation metrics into a compatibility score. 
The final score was used to decide whether the individuals were a successful match. My work emphasized ensuring the algorithm’s accuracy, efficiency, and seamless integration with the database and other software components.


## GPIO Setup
![pulse2](https://github.com/user-attachments/assets/00a35517-0d93-4dd2-a4e8-b7c7479ff16f)
![pulse](https://github.com/user-attachments/assets/6f1b7ead-acfb-4900-afb5-d0416468f379)


```
..1..2............3.
456..............7..
```
1. Ground
2. Mic BCLK
3. Mic DOUT
4. 3.3V
5. I2C data
6. I2C clock
7. Mic LRCL

## Software Setup

1. Turn on iphslamma hotspot

### Host
1. Install Python packages from requirements.txt
2. Ensure venv is activated
3. Ensure OpenAI API key environment variable is set
4. Ensure SSH identity is added

### Raspberry Pi
1. Start pigpio daemon with `sudo pigpiod -t 0`
   - `-t 0` is necessary to avoid interfering with I2S microphone input
2. Ensure `$HOME/record` directory exists
