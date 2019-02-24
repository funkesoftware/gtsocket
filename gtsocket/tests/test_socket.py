import unittest
from threading import Thread
from gtsocket import Socket, initialize_GPIOs, clear_GPIOs, SEQUENCE_REPETITIONS

class TestSocket(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        
        initialize_GPIOs()
        
        self.test_socket_name = 'A'
        self.test_socket_command = 'on'
        self.socket = Socket(self.test_socket_name)
        self.encodings = self.socket._get_encodings()
        
    def test_get_name(self):
        self.assertEqual(self.socket.get_name(), self.test_socket_name)
        
    def test_switching(self):
        self.socket.switch_on()
        self.assertTrue(self.socket.is_on(), 'Failed to switch socket on.')
        self.socket.switch_off()
        self.assertFalse(self.socket.is_on(), 'Failed to switch socket off.')
        self.socket.toggle()
        self.assertTrue(self.socket.is_on(), 'Failed to toggle socket.')
        
    def test_getting_signal_sequences_for_command(self):
        signal_sequences = self.socket.get_command_signal_sequences(self.test_socket_command)
        self.assertIsInstance(signal_sequences, list)
        
        number_of_sequences = float(len(signal_sequences))
        self.assertGreater(number_of_sequences, 0)
        self.assertTrue((number_of_sequences / SEQUENCE_REPETITIONS).is_integer(), 'The number of sequences is not a multiple of SEQUENCE_REPETITIONS.')
        self.assertTrue(( (number_of_sequences / SEQUENCE_REPETITIONS) / len(self.encodings.values())).is_integer(), 'The number of sequences is not a multiple of the number of encodings.')
        
        for signal_sequence in signal_sequences:
            self.assertGreater(len(signal_sequence), 0)
            found_valid_encoding = False
            for encoding in self.encodings.values():
                encoding_valid = True
                allowed_signals = encoding.get_allowed_signals()
                for signal in signal_sequence:
                    if signal not in allowed_signals:
                        encoding_valid = False
                        break
                if encoding_valid: found_valid_encoding = True
            self.assertTrue(found_valid_encoding, 'One of the signal sequences of {}-{} contains invalid signals.'.format(self.test_socket_name, self.test_socket_command))
                
    def dummy_signal_handler(self, sequence, encoding):
        pass
                
    def test_receiving(self):
        self.socket.add_signal_handler(self.dummy_signal_handler)
        receiving_thread = self.socket.start_receiving()
        self.assertTrue(self.socket.is_receiving_active())
        self.assertIsInstance(receiving_thread, Thread)
        self.socket.stop_receiving()
        self.assertFalse(self.socket.is_receiving_active())
        
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.socket.stop_receiving()
        clear_GPIOs()
        
if __name__ == '__main__':
    unittest.main()