import pigpio

# I2C address of the multiplexer
TCAADDR = 0x70
# I2C address of the heart rate sensor (both have same address)
MAXADDR = 0x57

# pigpio command codes for i2c_zip()
Z_END = 0
Z_READ = 6
Z_WRITE = 7

# Heart rate sensor register addresses
MAX_INT_1 = 0x00
MAX_INT_2 = 0x01
MAX_INT_EN_1 = 0x02
MAX_INT_EN_2 = 0x03
MAX_FIFO_WR_PTR = 0x04
MAX_OVF_COUNTER = 0x05
MAX_FIFO_RD_PTR = 0x06
MAX_FIFO_DATA = 0x07
MAX_FIFO_CONF = 0x08
MAX_MODE_CONF = 0x09
MAX_SPO2_CONF = 0x0a
MAX_LED1_PA = 0x0c
MAX_LED2_PA = 0x0d
MAX_TINT = 0x1f
MAX_TFRAC = 0x20
MAX_TEMP_EN = 0x21
MAX_PART_ID = 0xff

# Heart rate sensor constants
MAX_FIFO_ROLLOVER_EN_F = 1 << 4
MAX_MODE_HR_F = 0b010
MAX_MODE_SPO2_F = 0b011
MAX_MODE_MULTI_F = 0b111
MAX_MODE_RESET_F = 1 << 6
MAX_MODE_SHDN_F = 1 << 7
MAX_DIE_TEMP_RDY_F = 1 << 1

class HeartRateManager:
    NUM_SENSORS = 2

    def __init__(self):
        # Initialize GPIO
        print("Initializing GPIO...")
        self.pi = pigpio.pi("pulse.local")

        # Open I2C multiplexer on bus 1
        self.tca_handle = self.pi.i2c_open(1, TCAADDR)
        # Open heart rate sensor on bus 1
        self.max_handle = self.pi.i2c_open(1, MAXADDR)

        self.current_sensor_num = -1

        # Ensure connection to sensors exists
        for i in range(self.NUM_SENSORS):
            print(f"Setting up sensor {i}...", end="")
            self.select_sensor(i)
            assert self.pi.i2c_read_byte_data(self.max_handle, MAX_PART_ID) == 0x15

            # Reset
            self.pi.i2c_write_byte_data(self.max_handle, MAX_MODE_CONF, MAX_MODE_RESET_F)
            # Enable temperature ready flag
            self.pi.i2c_write_byte_data(self.max_handle, MAX_INT_EN_2, MAX_DIE_TEMP_RDY_F)
            # Enable SpO2 mode
            self.pi.i2c_write_byte_data(self.max_handle, MAX_MODE_CONF, MAX_MODE_SPO2_F)
            # Use max ADC range, 400 samples per second, max pulse width
            self.pi.i2c_write_byte_data(self.max_handle, MAX_SPO2_CONF, 0b11 << 5 | 0b011 << 2 | 0b11)
            # Set LED pulse amplitude
            self.pi.i2c_write_byte_data(self.max_handle, MAX_LED1_PA, 0x80)
            self.pi.i2c_write_byte_data(self.max_handle, MAX_LED2_PA, 0x80)
            # Perform sample averaging (8), allow FIFO rollover
            self.pi.i2c_write_byte_data(self.max_handle, MAX_FIFO_CONF, 0b011 << 5 | MAX_FIFO_ROLLOVER_EN_F)
            # Reset FIFO
            self.pi.i2c_zip(self.max_handle, [Z_WRITE, 4, MAX_FIFO_WR_PTR, 0, 0, 0, Z_END])
            print(" OK")

    def select_sensor(self, num):
        """Switch communication over I2C to the given sensor number, 0 or 1."""
        if num < 0 or num >= self.NUM_SENSORS:
            raise ValueError(f"Invalid sensor number {num}")
        if num == self.current_sensor_num:
            return
        self.pi.i2c_write_byte(self.tca_handle, 1 << num)
        self.current_sensor_num = num

    def read_temp(self, sensor_num):
        """Read the current temperature from the given sensor as a float, or -1 if failed."""
        self.select_sensor(sensor_num)

        # Start temperature reading
        self.pi.i2c_write_byte_data(self.max_handle, MAX_TEMP_EN, 1)
        # Wait until the temperature reading is ready
        while True:
            r = self.pi.i2c_read_byte_data(self.max_handle, MAX_INT_2)
            if r & MAX_DIE_TEMP_RDY_F != 0:
                break

        # Get temperature reading
        (count, data) = self.pi.i2c_zip(self.max_handle, [Z_WRITE, 1, MAX_TINT, Z_READ, 2, Z_END])
        if count != 2:
            print("Unknown read_temp() data:", (count, data))
            return -1
        return int(data[0]) + (int(data[1]) * 0.0625)

    def read_hr(self, sensor_num):
        self.select_sensor(sensor_num)

        # Get number of samples to read
        wr_ptr = self.pi.i2c_read_byte_data(self.max_handle, MAX_FIFO_WR_PTR)
        rd_ptr = self.pi.i2c_read_byte_data(self.max_handle, MAX_FIFO_RD_PTR)
        if wr_ptr == rd_ptr:
            # No new data
            return (0, [], [])
        if wr_ptr < rd_ptr:
            # Wrap around
            wr_ptr += 1 << 5

        num_samples = wr_ptr - rd_ptr
        if num_samples > 32 or num_samples <= 0:
            # Invalid, ignore
            print("Invalid num_samples", num_samples)
            return (-1, [], [])
        (count, data) = self.pi.i2c_zip(self.max_handle, [Z_WRITE, 1, MAX_FIFO_DATA, Z_READ, num_samples * 6, 0])
        if count != num_samples * 6:
            print("Unknown read_hr() data:", (count, data))
            return (-1, [], [])

        res1 = []
        res2 = []
        # Convert bytearray into integer values for each LED data stream
        for i in range(num_samples):
            res1.append(data[i * 6] << 16 | data[i * 6 + 1] << 8 | data[i * 6 + 2])
            res2.append(data[i * 6 + 3] << 16 | data[i * 6 + 4] << 8 | data[i * 6 + 5])
        return (num_samples, res1, res2)

    def stop(self):
        """Put sensors into power-save mode and close all GPIO resources."""
        for i in range(self.NUM_SENSORS):
            self.select_sensor(i)
            # Enter power-save mode
            self.pi.i2c_write_byte_data(self.max_handle, MAX_MODE_CONF, MAX_MODE_SHDN_F)
        try:
            self.pi.i2c_close(self.max_handle)
            self.pi.i2c_close(self.tca_handle)
        except pigpio.error:
            pass
        self.pi.stop()

# Optical heart rate detection
# This class is an adaptation of code from SparkFun Electronics
# https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library/blob/72d5308df500ae1a64cc9d63e950c68c96dc78d5/src/heartRate.cpp
class BeatFinder:
    FIR_COEFFS = (172, 321, 579, 927, 1360, 1858, 2390, 2916, 3391, 3768, 4012, 4096)

    def __init__(self):
        self.ir_min = -20
        self.ir_max = 20

        self.ir_signal_cur = 0
        self.ir_signal_prev = 0
        self.ir_signal_min = 0
        self.ir_signal_max = 0
        self.ir_avg = 0
        self.ir_avg_reg = 0

        self.pos_edge = False
        self.neg_edge = False

        self.buffer = [0] * 32
        self.offset = 0

    def check_for_beat(self, sample):
        """Return True if the given sample, when examined with previously supplied samples, describes a heartbeat."""
        beat_found = False

        self.ir_signal_prev = self.ir_signal_cur

        # Estimate average DC
        self.ir_avg_reg += ((sample << 15) - self.ir_avg_reg) >> 4
        self.ir_avg = self.ir_avg_reg >> 15

        # Apply low pass FIR filter
        self.buffer[self.offset] = sample - self.ir_avg
        self.ir_signal_cur = self.FIR_COEFFS[11] * self.buffer[(self.offset - 11) & 0x1f]
        for i in range(11):
            self.ir_signal_cur += self.FIR_COEFFS[i] * (self.buffer[(self.offset - i) & 0x1f] + self.buffer[(self.offset - 22 + i) & 0x1f])
        self.offset += 1
        self.offset %= 32
        self.ir_signal_cur >>= 15

        # Detect positive zero-crossing (rising edge)
        if self.ir_signal_prev < 0 and self.ir_signal_cur >= 0:
            self.pos_edge = True
            self.neg_edge = False
            self.ir_signal_max = 0

        # Detect negative zero-crossing (falling edge)
        if self.ir_signal_prev > 0 and self.ir_signal_cur <= 0:
            self.ir_min = self.ir_signal_min
            self.ir_max = self.ir_signal_max
            self.pos_edge = False
            self.neg_edge = True
            self.ir_signal_min = 0
            if self.ir_max - self.ir_min > 20 and self.ir_max - self.ir_min < 1000:
                beat_found = True

        # Find max value in positive cycle
        if self.pos_edge and self.ir_signal_cur > self.ir_signal_prev:
            self.ir_signal_max = self.ir_signal_cur

        # Find min value in negative cycle
        if self.neg_edge and self.ir_signal_cur < self.ir_signal_prev:
            self.ir_signal_min = self.ir_signal_cur

        return beat_found

    def get_cur(self):
        """Return the current signal value calculated by this BeatFinder."""
        return self.ir_signal_cur
