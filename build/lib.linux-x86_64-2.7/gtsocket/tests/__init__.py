import unittest

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(['gtsocket.tests.test_encoding', 'gtsocket.tests.test_socket'])