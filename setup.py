from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='gtsocket',
      version='0.1',
      description='Receive and/or send commands to radio controlled sockets (model GT-FSI-11) from brand "Globaltronics".',
      long_description=long_description,
      long_description_content_type='text/markdown',
      keywords='radio socket 433Mhz Globaltronics GT-FSI-11 RPi EasyHome',
      url='https://github.com/funkesoftware/gtsocket',
      author='Markus Funke',
      author_email='gtsocket@funke-software.de',
      license='GPLv3+',
      packages=find_packages(),
      install_requires=[
          'future',
          'configparser',
      ],
      test_suite='gtsocket.tests.test_suite',
      scripts=['bin/gtsocket-test','bin/gtsocket-setup'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Topic :: Communications',
          'Topic :: Home Automation',
      ],
      include_package_data=True,
      zip_safe=False)