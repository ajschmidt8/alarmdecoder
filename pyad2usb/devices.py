import usb.core
import usb.util
import time
import threading
from pyftdi.pyftdi.ftdi import *
from pyftdi.pyftdi.usbtools import *
from . import util
from .event import event

class Device(object):
    on_open = event.Event('Called when the device has been opened')
    on_close = event.Event('Called when the device has been closed')
    on_read = event.Event('Called when a line has been read from the device')
    on_write = event.Event('Called when data has been written to the device')

    def __init__(self):
        pass

    def __del__(self):
        pass

    class ReadThread(threading.Thread):
        def __init__(self, device):
            threading.Thread.__init__(self)
            self._device = device
            self._running = False

        def stop(self):
            self._running = False

        def run(self):
            self._running = True

            while self._running:
                try:
                    self._device.read_line()
                except util.CommError, err:
                    self.stop()

                time.sleep(0.25)

class USBDevice(Device):
    FTDI_VENDOR_ID = 0x0403
    FTDI_PRODUCT_ID = 0x6001
    BAUDRATE = 115200

    @staticmethod
    def find_all():
        devices = []

        try:
            devices = Ftdi.find_all([(USBDevice.FTDI_VENDOR_ID, USBDevice.FTDI_PRODUCT_ID)], nocache=True)
        except (usb.core.USBError, FtdiError), err:
            raise util.CommError('Error enumerating AD2USB devices: {0}'.format(str(err)))

        return devices

    def __init__(self, vid=FTDI_VENDOR_ID, pid=FTDI_PRODUCT_ID, serial=None, description=None):
        Device.__init__(self)

        self._vendor_id = vid
        self._product_id = pid
        self._serial_number = serial
        self._description = description
        self._buffer = ''
        self._device = Ftdi()
        self._running = False

        self._read_thread = Device.ReadThread(self)

    def open(self, baudrate=BAUDRATE, interface=0, index=0):
        self._running = True

        try:
            self._device.open(self._vendor_id,
                             self._product_id,
                             interface,
                             index,
                             self._serial_number,
                             self._description)

            self._device.set_baudrate(baudrate)
        except (usb.core.USBError, FtdiError), err:
            self.on_close()

            raise util.CommError('Error opening AD2USB device: {0}'.format(str(err)))
        else:
            self._read_thread.start()

            self.on_open((self._serial_number, self._description))

    def close(self):
        try:
            self._running = False
            self._read_thread.stop()

            self._device.close()
        except (FtdiError, usb.core.USBError):
            pass

        self.on_close()

    def write(self, data):
        self._device.write_data(data)

        self.on_write(data)

    def read_line(self, timeout=0.0):
        start_time = time.time()
        got_line = False
        ret = None

        try:
            while self._running:
                buf = self._device.read_data(1)
                self._buffer += buf

                if buf == "\n":
                    if len(self._buffer) > 1:
                        if self._buffer[-2] == "\r":
                            self._buffer = self._buffer[:-2]

                            # ignore if we just got \r\n with nothing else in the buffer.
                            if len(self._buffer) != 0:
                                got_line = True
                                break
                    else:
                        self._buffer = self._buffer[:-1]

                if timeout > 0 and time.time() - start_time > timeout:
                    break

                time.sleep(0.01)
        except (usb.core.USBError, FtdiError), err:
            self.close()

            raise util.CommError('Error reading from AD2USB device: {0}'.format(str(err)))
        else:
            if got_line:
                ret = self._buffer
                self._buffer = ''

                self.on_read(ret)

        return ret


class SerialDevice(Device):
    BAUDRATE = 9600

    def __init__(self):
        Device.__init__(self)

    def __del__(self):
        pass

    def open(self, baudrate=BAUDRATE, interface="COM1", index=0):
        pass

    def close(self):
        pass

    def write(self, data):
        pass

    def read_line(self, data):
        pass
