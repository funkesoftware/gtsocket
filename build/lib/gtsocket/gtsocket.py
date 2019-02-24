from __future__ import division # python 2 compatibility
"""Receive and/or send commands to radio controlled sockets (model GT-FSI-11) from brand 'Globaltronics'."""
"""
    Copyright (C) 2018  Markus Funke

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser
    
import time
from datetime import datetime
from threading import Thread
from RPi import GPIO

# get full path to configuration file which is in the same directory as this module file
CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.path.splitext(os.path.basename(__file__))[0] + '.cfg')

config = ConfigParser({})
# read standard config shipped with this package and overwrite with config in .gtsocket folder in home folder (if exists)
config.read([CONFIG_FILE, os.path.expanduser('~/.gtsocket/config.ini')])

SENDING_PIN = int(config.get('general', 'sending_GPIO_pin')) if config.has_option('general', 'sending_GPIO_pin') else None
RECEIVING_PIN = int(config.get('general', 'receiving_GPIO_pin')) if config.has_option('general', 'receiving_GPIO_pin') else None

SEQUENCE_REPETITIONS = int(config.get('general', 'sequence_repetitions')) if config.has_option('general', 'sequence_repetitions') else None
MAX_SIGNAL_DIFFERENCE = int(config.get('general', 'max_signal_difference')) if config.has_option('general', 'max_signal_difference') else 20 # max difference (in %) of the measured signal length to a pre-defined signal length (in socket_signals.py) to be matched
SEQUENCE_MIN_LENGTH = int(config.get('general', 'sequence_min_length')) if config.has_option('general', 'sequence_min_length') else 10 # a measures sequence of signals must consist of at least this amount of signal to be considered a signal_sequence

receiving_GPIO_initialized = False
sending_GPIO_initialized = False

def initialize_receiving_GPIO():
    """Set up that GPIO pin of Raspberry Pi as input pin, which was configured as receiving pin in config."""
    if RECEIVING_PIN is None: raise SocketError('Cannot initialize receiving GPIO. No sending pin given in config.')
    global receiving_GPIO_initialized
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RECEIVING_PIN, GPIO.IN)
    receiving_GPIO_initialized = True

def initialize_sending_GPIOs():
    """Set up that GPIO pin of Raspberry Pi as output pin, which was configured as sending pin in config."""
    if SENDING_PIN is None: raise SocketError('Cannot initialize sending GPIO. No sending pin given in config.')
    global sending_GPIO_initialized
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENDING_PIN, GPIO.OUT)
    sending_GPIO_initialized = True
    
def initialize_GPIOs():
    """Initialize both receiving and sending GPIO pin of Raspberry Pi with RPi.GPIO module."""
    initialize_receiving_GPIO()
    initialize_sending_GPIOs()
    
def clear_GPIOs():
    """Clear (configure as input pin) all used GPIO Raspberry Pi pins to prevent damage to Raspberry Pi board."""
    global sending_GPIO_initialized, receiving_GPIO_initialized
    GPIO.cleanup()
    sending_GPIO_initialized = False
    receiving_GPIO_initialized = False

class EncodingError(Exception):
    """Exception raised by Encoding class."""
    def __init__(self, message):
        Exception.__init__(self, message)

class Encoding():
    def __init__(self, init_signal_sequence, binary_0_signal_sequence, binary_1_signal_sequence):
        self.init_signal_sequence = init_signal_sequence
        self.binary_0_signal_sequence = binary_0_signal_sequence
        self.binary_1_signal_sequence = binary_1_signal_sequence
        
    def encode(self, data_sequence, add_init_sequence = True):
        """Convert given data_sequence (str) (consisting of 1s and 0s) to list of signals (time periods w/ or w/o radio signal)."""
        signal_sequence = self.get_init_sequence() if add_init_sequence else []
        for c in data_sequence:
            if c != '0' and c != '1': raise EncodingError('{} can not be encoded it is not a valid binary value (only 0 and 1 allowed).'.format(c))
            signals = self.binary_0_signal_sequence if c == '0' else self.binary_1_signal_sequence
            signal_sequence.extend(signals)
        return signal_sequence
    
    def decode(self, signal_sequence):
        """Convert given list of signals (time periods w/ or w/o radio signal) to data string (consisting of 1s and 0s)."""
        
        # if signal sequence starts with init sequence, strip off this init sequence
        if signal_sequence[0:len(self.get_init_sequence())] == self.get_init_sequence():
            signal_sequence = signal_sequence[len(self.get_init_sequence()):]
        
        binary_signal_sequences = [self.binary_0_signal_sequence, self.binary_1_signal_sequence]
        
        data_sequence = ''
        while signal_sequence and len(signal_sequence) >= 2:
            one_bit_signals = signal_sequence[0:2]
            
            try:
                signal_sequence_index = binary_signal_sequences.index(one_bit_signals)
                data_sequence += str(signal_sequence_index)
                signal_sequence = signal_sequence[2:]
            except ValueError:
                return ''
        return data_sequence
    
    def get_init_sequence(self):
        return list(self.init_signal_sequence)
    
    def get_allowed_signals(self, mode = 'all'):
        if mode == 'init':
            allowed_signals = self.get_init_sequence()
        elif mode == 'binary':
            allowed_signals = self.binary_0_signal_sequence + self.binary_1_signal_sequence
        else:
            allowed_signals = self.get_init_sequence() + self.binary_0_signal_sequence + self.binary_1_signal_sequence
                    
        return list(set(allowed_signals)) # return list of unique signals
    
    def get_best_fitting_signal(self, signal, mode='all'):
        """Return that init or binary signal (depends on mode) with smallest difference to given signal and not more difference than MAX_SIGNAL_DIFFERENCE."""
        allowed_signals = self.get_allowed_signals(mode)
        
        smallest_difference = None
        best_fitting_signal = None
        for possible_signal in allowed_signals:
            difference = abs(signal - possible_signal)
            if (abs(difference / possible_signal) * 100) > MAX_SIGNAL_DIFFERENCE: continue
            if smallest_difference is None or difference < smallest_difference:
                smallest_difference = difference
                best_fitting_signal = possible_signal
        return best_fitting_signal
    
    def convert_to_best_fitting_sequence(self, signal_sequence, mode='all'):
        return [self.get_best_fitting_signal(signal, mode) for signal in signal_sequence]
    
    def find_init_sequence(self, signal_sequence):
        best_fitting_signal_sequence = self.convert_to_best_fitting_sequence(signal_sequence, 'init')
        init_sequence = self.get_init_sequence()
        if len(init_sequence) == 0:
            return None
        
        position = 0
        while len(best_fitting_signal_sequence) >= len(init_sequence):
            if best_fitting_signal_sequence[:len(init_sequence)] == init_sequence:
                return position
            best_fitting_signal_sequence = best_fitting_signal_sequence[1:] if len(best_fitting_signal_sequence) > 1 else []
            position += 1
        return None

class SocketError(Exception):
    """Exception raised by Socket class."""
    def __init__(self, message):
        Exception.__init__(self, message)

class Socket():
    """With this class commands can be send to and received from socket.
    
    An object of this class represents a socket which has been linked to 
    the letter given to the __init__ function and can be used to switch 
    that socket on or off (send 'on' or 'off' command to it) or to receive 
    commands (or raw signals) which are send to/for this socket.
    If more than one socket have been linked to the same letter the object 
    represents all those socket since the program cannot distinguish them.
    
    To be able to send/receive commands GPIOs have to be initialized first 
    and cleared if not needed anymore.
    """
    def __init__(self, name, **options):
        """Initialize socket and create list of data sequences configured in config file.
        
        Args
        ----------
        name : str
            The name of the socket (as in config) you want to send commands to / receive command for.
        
        Kwargs
        ------
        init_status : str ('on' or 'off)
            The status / command to initialize to socket with. This command will be sent automatically on object creation.
        """
        
        self.__receiving_active = False
        """Indicates if receiving for this socket is active. Is set to False to stop receiving thread."""
        self.receiving_thread = None
        """The thread receiving signals / commands for this socket."""
        self._signal_handlers = []
        """Functions registered to be called whenever a raw signal is received."""
        self._command_handlers = []
        """Functions registered to be called whenever a command for this socket is received."""
        
        self.__name = name
        self.__encodings = {}
        
        socket_config_section = 'socket:' + self.__name
        group_name = config.get(socket_config_section, 'group') if config.has_option(socket_config_section, 'group') else None
        group_config_section = 'group:' + group_name
        if config.has_option(group_config_section, 'encodings'):
            for encoding_name in config.get(group_config_section, 'encodings').split(','):
                encoding_section = 'encoding:' + encoding_name
                init_sequence = [int(signal) for signal in config.get(encoding_section, 'init').split(',')] if config.has_option(encoding_section, 'init') else []
                binary_0_sequence = [int(signal) for signal in config.get(encoding_section, '0').split(',')] if config.has_option(encoding_section, '0') else []
                binary_1_sequence = [int(signal) for signal in config.get(encoding_section, '1').split(',')] if config.has_option(encoding_section, '1') else []
                self.__encodings[encoding_name] = Encoding(init_sequence, binary_0_sequence, binary_1_sequence)
        else:
            raise SocketError('No encoding information found in config for group {}.'.format(group_name))
        
        self._start_data = config.get(group_config_section, 'start_data') if config.has_option(group_config_section, 'start_data') else None
        self._end_data = config.get(socket_config_section, 'end_data') if config.has_option(socket_config_section, 'end_data') else None
        
        self._command_data = {}
        for command in ['on','off']:
            command_data = config.get(socket_config_section, '{}_command_data'.format(command)) if config.has_option(socket_config_section, '{}_command_data'.format(command)) else None
            while command_data is not None and '|' in command_data:
                command_data = config.get(command_data.split('|')[0], command_data.split('|')[1]) if config.has_option(command_data.split('|')[0], command_data.split('|')[1]) else None
            self._command_data[command] = command_data.split(',') if command_data is not None else None
        
        init_status = options.get('init_status', None)
        if init_status == 'on':
            self.switch_on()
        elif init_status == 'off':
            self.switch_off()
            
    def get_name(self):
        return self.__name
            
    def is_on(self):
        """Return boolean indicating if this socket is currently switched on."""
        if self.status == 'on':
            return True
        elif self.status == 'off':
            return False
        else:
            return None
        
    def switch_on(self):
        """Switch socket on by sending command 'on' to this socket."""
        self.send_command('on')
        self.status = 'on'
    
    def switch_off(self):
        """Switch socket off by sending command 'off' to this socket."""
        self.send_command('off')
        self.status = 'off'
    
    def toggle(self):
        """Toggle this switch. Switch it on if it is off and switch it off if it is on."""
        if self.status is None: raise SocketError('The socket cannot be toggled. It does not yet have a status.')
        if self.status == 'on':
            self.switch_off()
        else:
            self.switch_on()
            
    def _get_encodings(self):
        return self.__encodings
            
    def get_command_signal_sequences(self, command):
        """Create and return list of signals sequences in all available encodings which need to be sent to send the given command to this socket."""
        command_signal_sequences = []
        for data_sequence in self._command_data[command]:
            for encoding in self.__encodings.values():
                sequence = encoding.encode(self._start_data + data_sequence + self._end_data)
                for _ in range(SEQUENCE_REPETITIONS):
                    command_signal_sequences.append(sequence)
        return command_signal_sequences
            
    def send_command(self, command):
        """Get signal sequences to send given command to this socket and create and start thread which sends those signal sequences."""
        if not sending_GPIO_initialized: raise SocketError('Cannot send socket command. The sending GPIO has not been initialized.')
        
        signal_sequences = self.get_command_signal_sequences(command)
        sending_thread = Thread(target=self._send_signal_sequences, args=(signal_sequences,))
        sending_thread.start()
        sending_thread.join()
        
    def _send_signal_sequences(self, signal_sequences):
        """Send given signal sequences via 433Mhz sender by switching sending GPIO pin on and off for time periods specified in signal sequences."""
        GPIO.output(SENDING_PIN, 0)
        
        for sequence in signal_sequences:
            for signal in sequence:
                signalLength = abs(signal)
                new_value = 1 if signal > 0 else 0
                signalSeconds = signalLength / 1000000
                
                GPIO.output(SENDING_PIN, new_value)
                time.sleep(signalSeconds)
                
    def add_signal_handler(self, handler_function):
        """Register given function as signal handler which is called whenever this socket receives a signal sequence."""
        self._signal_handlers.append(handler_function)
        
    def add_command_handler(self, handler_function):
        """Register given function as command handler which is called whenever this socket receives a command."""
        self._command_handlers.append(handler_function)
        
    def get_command_by_data_sequence(self, data_sequence):
        """Use signal/data sequences specified in config file to determine corresponding command for given data sequence."""
        for command, data_sequences in self._command_data.items():
            for test_data_sequence in data_sequences:
                test_data_sequence = self._start_data + test_data_sequence + self._end_data
                if data_sequence == test_data_sequence:
                    return command
        
        return None
    
    def is_receiving_active(self):
        return self.__receiving_active
        
    def start_receiving(self):
        """Create and start thread receiving signals / commands for this socket."""
        # if there are no handers registered, we do not need to receive anything
        if len(self._signal_handlers) == 0 and len(self._command_handlers) == 0: return
        
        if not receiving_GPIO_initialized: raise SocketError('Cannot receive signals. The receiving GPIO has not been initialized.')
        
        self.__receiving_active = True
        self.receiving_thread = Thread(target=self._receive_signals, args=(lambda: self.__receiving_active,))
        self.receiving_thread.start()
        return self.receiving_thread
    
    def stop_receiving(self):
        """Stop thread which is receiving signals / commands for this socket."""
        self.__receiving_active = False
        
    def _receive_signals(self, is_receiving_active):
        """Receive signals / commands for this socket by monitoring receiving GPIO pin status and calling registered handler functions."""
        current_encoding = None
        current_sequence = []
            
        start_time = datetime.now()
        last_value = None
        
        # find length of longest init sequence in encodings to keep current_sequence that short while searching for init sequences
        max_init_sequence_length = 1
        for encoding in self.__encodings.values():
            if len(encoding.get_init_sequence()) > max_init_sequence_length:
                max_init_sequence_length = len(encoding.get_init_sequence())
        
        while is_receiving_active():
            value_now = GPIO.input(RECEIVING_PIN)
            time_now = datetime.now()
            
            if value_now != last_value:
                if last_value is not None:
                    time_delta = time_now - start_time
                    signal = int(round(time_delta.microseconds + (time_delta.seconds * 1000000), -2))
                    if signal == 0: continue
                    if value_now != 0: signal *= -1;
                    
                    if current_encoding is not None:
                        # init sequence was already found, now recording binary signals
                        best_fitting_signal = current_encoding.get_best_fitting_signal(signal, 'binary')
                        if best_fitting_signal is not None:
                            current_sequence.append(best_fitting_signal)
                        else:
                            # found signal which is not a binary signal (maybe the next init signal?), binary data (sequence) ends here, process this sequence
                            if len(current_sequence) > SEQUENCE_MIN_LENGTH:
                                # signal sequence found, process it
                                if len(self._signal_handlers) > 0:
                                    for signal_handler in self._signal_handlers:
                                        signal_handler(current_sequence, current_encoding)
                                if len(self._command_handlers) > 0:
                                    data_sequence = current_encoding.decode(current_sequence)
                                    command = self.get_command_by_data_sequence(data_sequence)
                                    if command is not None:
                                        for command_handler in self._command_handlers:
                                            command_handler(self, command)
                            
                            current_sequence = []
                            current_encoding = None
                    
                    if current_encoding is None:
                        # no encoding found yet, look for init sequences
                        current_sequence.append(signal)
                        for encoding in self.__encodings.values():
                            init_sequence_found_pos = encoding.find_init_sequence(current_sequence)
                            if init_sequence_found_pos is not None:
                                current_encoding = encoding
                                break
                            
                        if current_encoding is None:
                            current_sequence = current_sequence[max_init_sequence_length*-1:]
                        else:
                            current_sequence = current_encoding.get_init_sequence()
    
                last_value = value_now
                start_time = time_now