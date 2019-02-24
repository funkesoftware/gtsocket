import unittest
from gtsocket import Encoding, MAX_SIGNAL_DIFFERENCE

class TestEncoding(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        
        self.init_sequence = [-400, 1500]
        self.binary_0_sequence = [-300, 2700]
        self.binary_1_sequence = [100, -600]
        
        self.encoding = Encoding(self.init_sequence, self.binary_0_sequence, self.binary_1_sequence)
        
        self.test_data = '10111011000101'
        self.test_encoding_signals = [-400, 1500, 100, -600, -300, 2700]
        self.test_data_signals = [100, -600, -300, 2700, 100, -600, 100, -600, 100, -600, -300, 2700, 100, -600, 100, -600, -300, 2700, -300, 2700, -300, 2700, 100, -600, -300, 2700, 100, -600]
        
    def test_encode(self):
        self.assertListEqual(self.encoding.encode(self.test_data, True), self.init_sequence + self.test_data_signals)
        self.assertListEqual(self.encoding.encode(self.test_data, False), self.test_data_signals)
        
    def test_decode(self):
        self.assertEqual(self.encoding.decode(self.init_sequence + self.test_data_signals), self.test_data)
        self.assertEqual(self.encoding.decode(self.test_data_signals), self.test_data)
        
    def test_get_init_sequence(self):
        self.assertListEqual(self.encoding.get_init_sequence(), self.init_sequence)
        
    def test_get_allowed_signals(self):
        generated_list = self.encoding.get_allowed_signals('all')
        generated_list.sort()
        self.test_encoding_signals.sort()
        self.assertListEqual(generated_list, self.test_encoding_signals)
        
    def test_getting_best_fitting_signal(self):
        difference_multiplier = float(MAX_SIGNAL_DIFFERENCE) / 100;
        
        out_of_range = int(max(self.test_encoding_signals) * (difference_multiplier + 1)) + 2
        lower_end = int(min(self.test_encoding_signals) * (difference_multiplier + 1)) + 2
        upper_end = int(max(self.test_encoding_signals) * (difference_multiplier + 1))
        
        out_of_range_result = self.encoding.get_best_fitting_signal(out_of_range)
        self.assertIsNone(out_of_range_result, 'No best fitting signal should be found for {}. It should be out of range. {} was found.'.format(out_of_range, out_of_range_result))
        
        self.assertEqual(self.encoding.get_best_fitting_signal(lower_end), min(self.test_encoding_signals))
        self.assertEqual(self.encoding.get_best_fitting_signal(upper_end), max(self.test_encoding_signals))
        
if __name__ == '__main__':
    unittest.main()
        