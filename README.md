Introduction
============

This package provides the Python module 'gtsocket' which can be used to send commands to (switch on and off) 433Mhz controlled 
sockets (model GT-FSI-11) from the manufacturer 'Globaltronics' and to receive such commands sent by the corresponding remote.

Supported models (known so far) are:
* Globaltronics: GT-FSI-11 (also sold as EasyHome by ALDI Süd)

If you were able to successfully work with another model, please send me an [e-mail](gtsocket@funke-software.de) and I'll update this document.

I'll try to describe this module as completely as possible in this document. If you prefer a quick overview please read at least the sections **Usage** and **Scripts**.

Installation
============

This package can be installed via PIP:

	pip install gtsocket
	
or cloned from the GitHub page:

	git clone git@github.com:funkesoftware/gtsocket.git
	
How it works
============

As far as I analysed the protocol, sending commands (on/off) to the sockets by the remote works as follows:

The remote transmits information by switching on and off sending on 433Mhz. 

A **signal** (as used in this document) is a period of time during which sending on 433Mhz is either ON the whole time or OFF the whole time.
Such signals are defined as positive or negative integers in the config.
Positive values mean X microsec ON, negatives mean X microsec OFF, i.e. 300 = 300 microsec ON (receiving a signal on 433Mhz), -2400 = 2400 microsec. OFF (not receiving any signal).

A **signal sequence** (as used in this document) refers to a sequence of signals, for example: [-300, 700] meaning first 300 microsec. OFF, then 700 microsec. ON.

A **data sequence** is a sequence of binary 1s and 0s. An encoding defines how to transmit a data sequence as a signal sequence. For example a 1 might be transmitted as [300, -700] and a 0 as [1000, -200].

Each command as sent from the remote to a socket consists of four parts with the following schema: 

	init start data end

- the **init** signal sequence: shared by all commands sent in the same encoding
- the **start** data sequence: shared by all commands
- the **data** data sequence: shared by one or more socket-command combinations
- the **end** data sequence: shared by all commands for a specific socket

Each socket-command combination has difference data sequences that work. The remote sends those one after the other. Each command sequence is sent in all available encodings (in my case two) and repeated several times (in my case four times).

In summary, sending command ON to socket A might look like this:

	init start data(A-on1) end(A) [sent in encoding 1 four times]
	init start data(A-on1) end(A) [sent in encoding 2 four times]
	init start data(A-on2) end(A) [sent in encoding 1 four times]
	init start data(A-on2) end(A) [sent in encoding 2 four times]
	init start data(A-on3) end(A) [sent in encoding 1 four times]
	init start data(A-on3) end(A) [sent in encoding 2 four times]
	init start data(A-on4) end(A) [sent in encoding 1 four times]
	init start data(A-on4) end(A) [sent in encoding 2 four times]

The following configuration section describes how to define the encodings and data sequences for the needed commands.

Configuration
=============

(Please see script section below - the gtsocket-setup script provides a wizard for creating a config file.)
(Please also see the gtsocket.cfg file for a default config with explaining comments.)

In the [general] section with:

- **receiving_GPIO_pin** and **sending_GPIO_pin** set the Rasperry Pi GPIO BCM pin numbers the 433Mhz receiver and sender are connected to
- **max_signal_difference** define the maximum difference between the measured signal length and the signal length defined in an encoding for the measured signal to be recognized as the defined signal (in percent)
- **sequence_min_length** define the minimum length of a sequence of signals to be considered valid, shorter sequences will not trigger a signal/command 
handler
- **sequence_repetitions** define how often a command signal sequence is repeated using a given encoding when sending a command (the manufacturer's 
remote repeats four times)

The command signal sequences are sent in different encodings. My remote sends commands in two different encodings and I assume other remotes use the same encodings. So you probably can keep the default config here. The encodings are defined as follows:

	[encoding:1]
	init=300,-2400
	1=1000,-500
	0=300,-1200
	
The section must be named [encoding:NAME]. The NAME of the encoding can be chosen freely (but you should better omit whitespace characters).
Each command sequence starts with an init sequence consisting of two signals, each binary 1 and each binary 0 is encoded as two signals each.

Sockets switched by the same remote share the same encodings and the same start data sequence. Those are defined in a [group:NAME] section.

	[group:1]
	encodings=1,2
	start_data=1110
	
With **encodings** define the names of the encodings and with **start_data** the start data sequence used by the group of sockets.

Each individual socket is defined in a [socket:NAME] section.

	[socket:A]
	group=1
	on_command_data=1101111110100110,0111001011010001,1100011110010101,1001101101011010
	off_command_data=0100001101100010,0001000000101000,1011111011101011,0000100100000111
	end_data=1100
	
With **group** define the group of sockets this socket belongs to. With **end_data** define the end data sequence this socket uses. With **on_command_data** and **off_command_data** define the data sequences for commands ON and OFF as a comma-separated list. Some socket-command combinations share the same data sequences. For my sockets the data sequences for A-on and C-off are the same. In such cases you can reuse the data sequences of another socket as follows:

	[socket:C]
	off_command_data=socket:A|on_command_data
	
Usage
=====

Make sure you complete the configuration part first. The default configuration will most probably not work with your sockets. The `bin/gtsocket-setup` script provides a wizard for creating a config file specific for your setup.
Please have a look at the `bin/gtsocket-test` script which contains working examples for sending and receiving commands.

Sending commands
----------------

After importing the module

	import gtsocket
	
initialize GPIOs of Raspberry Pi as configured in config file. This configures sending pin as output pin and 
receiving pin as input pin. This has to be done only once at the beginning of the script, **not** every time a command is sent.

	gtsocket.initialize_GPIOs()

Create socket object specifying the name (as defined in the config) of the socket the command should be sent to ('A' in this case) and send command 'on' 
to (switch on) this socket.

	socket = gtsocket.Socket('A')
	socket.send_command('on')
	
Clear GPIOs of Raspberry Pi which have been initialized with initialize_GPIOs(). This sets those pins back to input mode.
This has to be done only once at the end of the script, **not** every time a command is sent.

	gtsocket.clear_GPIOs()
	
Receiving commands
------------------

Import module:

	import gtsocket
	
Initialize GPIOs of Raspberry Pi as described in *sending commands*:

	gtsocket.initialize_GPIOs()
	
Create socket object, which commands should be received for:

	socket = gtsocket.Socket('A')
	
Register any function as a command handler for this socket:

	socket.add_command_handler(my_command_handler)
	
The function will receive the socket object and the command received as arguments. It might for example look like this:

	def my_command_handler(socket, command):
		print("Received command", command, "for socket", socket.get_name())
		
Start receiving commands for this socket. This will create a new thread which does the receiving. The thread is saved in 
`socket.receiving_thread` and returned by `start_receiving()`.

	socket.start_receiving()
	
Once you want to stop receiving:

	socket.stop_receiving()
	socket.receiving_thread.join()

Clear GPIOs of Raspberry Pi as described in *sending commands*.

	gtsocket.clear_GPIOs()
	
Scripts
=======

When installed via pip the commands `gtsocket-setup` and `gtsocket-test` are available (otherwise you'll find them in the `bin/` folder).
`gtsocket-setup` is a helper tool to find out the correct encoding and signal/data sequences for your specific sockets and 
create a config file for your setup. 
`gtsocket-test` serves as a demo which shows how to use the module and can be used to manually send commands and test if 
receiving commands works.

Setup script - gtsocket-setup
----------------------------------

Execute script with `gtsocket-setup` and follow the instructions. A config file specific for your setup will be created as `~/.gtsocket/config.ini`.

The setup script consists of three steps: *pins*, *encodings* and *sequences*.
Invoking the script without any option will start with the first step. 
With the option **-s / --step** you can directly jump to a certain step.

At the beginning of the script (regardless of the step) you are asked which group of sockets you want to create the config for. A group of sockets are 
those sockets controlled by the same remote. You can choose a name freely but you should avoid whitespace characters.

**pins** defines the GPIO pins the sending and receiving devices are connected to.

**encodings** is used to determine the encodings your remote uses to send the data (how long the signals sent via radio are, which are used to 
send binary 1s and 0s). (Please see also sections *How it works* and *Configuration*)

You'll be asked to press and hold a button on your remote so that the script can receive transmitted signals and determine the encoding (with your help).
After that you'll get an overview of the received signals which should look similar to this:

	P(0)=-200, P(1)=800, P(2)=-500, P(3)=1000, P(4)=200, P(5)=-100, P(6)=300, P(7)=-1200, P(8)=-1300, P(9)=-2400, P(a)=1100, P(b)=2900, P(c)=-7300, P(d)=900, P(e)=-600, P(f)=400, P(10)=-1100, P(11)=-5700, P(12)=100, P(13)=-1500, P(14)=-1400, P(15)=-1000, P(16)=-400, P(17)=700, P(18)=-800, P(19)=3000, P(1a)=600, P(1b)=-2500, P(1c)=-3400, P(1d)=-900, P(1e)=-700
	Received signals: 0.1.2.3.2.4.5.1.2.6.7.6.8.3.2.6.8.3.2.3.2.6.8.3.2.4.8.6.7.6.8.3.2.3.2.3.2.4.8.6.8.6.9.3.2.a.2.3.2.6.8.6.8.3.2.3.2.a.2.6.7.6.8.a.2.4.8.a.2.3.2.6.7.3.2.6.7.6.7.6.8.a.2.3.2.3.2.6.8.6.8.6.9.a.2.3.2.3.2.6.8.6.7.a.
	2.3.2.3.2.6.8.6.8.3.2.4.8.3.2.3.2.6.8.3.2.6.8.6.8.6.8.3.2.a.2.3.2.6.8.6.8.b.c.d.e.d.e.d.e.f.10.f.10.d.e.3.e.d.e.f.10.f.7.d.e.f.10.f.11.12.13.12.14.12.13.12.0.12.0.12.15.12.16.12.15.12.0.12.7.12.13.12.5.12.8.4.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.12.5.
	12.5.12.5.12.5.12.c.d.e.d.e.d.e.f.7.f.10.d.e.d.e.d.e.f.7.f.10.d.e.f.10.d.e.d.e.f.7.d.e.f.10.f.10.f.10.d.e.d.e.d.e.f.10.f.10.b.c.d.e.d.e.d.e.f.10.f.10.d.e.d.e.d.e.f.10.f.10.d.e.f.10.d.e.d.e.f.10.d.e.f.10.f.10.f.10.d.e.d.e.17.18.f.10.f.10.19.c.d.e.d.e.d.e.f.10.f.
	10.d.e.d.e.d.e.f.10.f.10.1a.1b.12.0.12.16.12.18.12.1c.12.0.12.1d.12.0.12.7.12.5.12.8.12.5.12.8.12.5.12.5.12.5.12.5.12.e.d.e.d.e.f.10.f.7.6.9.3.2.a.2.3.2.6.7.a.2.3.2.6.7.6.7.6.7.3.2.3.2.3.2.3.2.6.7.6.7.3.2.6.8.3.2.6.7.3.2.3.2.3.2.6.8.6.8.6.9.3.2.3.2.3.2.6.8.3.2.a.2.6.7.
	6.7.6.7.a.2.3.2.3.2.3.2.6.7.6.7.3.2.6.8.3.2.6.8.3.2.3.2.3.2.6.7.6.7.6.9.3.2.3.2.3.2.6.7.a.2.3.2.6.8.6.8.6.8.3.2.3.2.3.2.3.2.6.7.6.8.3.2.6.8.3.2.6.7.3.2.3.2.3.2.6.8.6.8.6.9.3.2.3.2.3.2.6.7.a.2.3.2.6.7.6.7.6.8.3.2.3.2.a.2.3.2.
	6.8.6.7.3.2.6.8.3.2.6.8.3.2.3.2.3.2.6.8.6.8.b.c.d.e.d.e.d.e.f.10.d.e.d.e.f.10.f.10.f.10.d.e.d.e.d.e.d.e.f.10.f.10.d.e.f.10.d.e.f.10.d.e.d.e.d.e.f.10.f.10.19.c.d.e.d.e.d.e.f.10.d.e.d.e.f.10.f.10.f.10.d.e.d.e.d.e.d.e.f.10.f.10.d.e.f.10.d.e.f.10.d.e.d.e.d.e.f.10.f.10.19.
	c.d.e.d.e.d.e.f.10.d.e.d.e.f.10.f.10.f.10.d.e.d.e.d.e.d.e.f.10.f.10.d.e.f.10.d.e.f.10.d.e.d.e.d.e.f.10.f.10.19.c.d.e.d.e.d.e.f.10.d.e.d.e.f.10.f.10.f.10.d.e.d.e.d.1e.d.e.f.10.f.10.d.e.f.10.d.e.f.10.d.e.d.e.d.e.f.10.f.
	
The first line is a legend and shows how (with which indices) the received signals are shown to you below. Received signals are separated by dots and each number corresponds to a received signal. In this example a "0" means we received a low signal of 200µs and a "6" means we received a high signal of 300µs.

Now you have to specify which signals you think belong to the actual command signals and which are noise. This looks more complicated than it is. Just look which indices repeat in the sequence and which do not. In this example the indices "0" and "1" you can find in the beginning but they do not appear later, so they are most probably noise. "3", "8", "10" for example appear pretty often.

Now decide which indices to keep (command signals) and which to dismiss (noise). You do not have to be 100% correct on the first try. Just keep those you are sure are command signals and those you are not sure about. You'll repeat this until you are pretty sure about the command signals. Better keep too many than too few. A couple of wrong signals won't harm that much later. (Reading *How it works* and *Configuration* will help you here.)

Once you have narrowed down the command signals long enough you should see something like this (The dots disappear once we don't need them anymore to distinguish between indices like "1", "0" and "10"):

	P(0)=300, P(1)=-2400, P(2)=1000, P(3)=-500, P(4)=-1200, P(5)=2900, P(6)=-7300, P(7)=900, P(8)=-600, P(9)=400, P(a)=-1100
	Received signals: 04787878949401232323042304042323042323042304232304230423230404012323230423040423230423230423042323042304232304040123232304710404040404040403000003030400000000000800030003080004280423000000000003040401232323042304042323042323042304232304230423230404567878789a789a9a78789a78789a789a78789a789a7
	8789a9a567878789a789a9a78789a78789a789a78789a789a78789a9a567878789a789a9a78789a78789a789a78789a789a78789a9a567878789a789a9a78789a78789a789a78789a789a78789a9401232323042323042323232323230423040423230423230404012323230423230423232323232304230404232304232304040123232304232304232323232323042304
	042323042323040401232323042323042323232323230423040423230423230404567878789a78789a7878787878789a789a9a78789a78789a94567878789a78789a7878787878789a789a9a78789a78789a9a567878789a78789a7878787878789a789a9a78789a78789a94567878789478789a7878787878789a789a9a78789a78789a940123232304042323230404230
	4232304230404042323230404012323230404232323040423042323042304040423232304040123232304042323230404230423230423040404232323040401232323040423232304042304232304230404042323230404567878789a9a7878789a9a789a78789a789a9a9a7878789a9a567878789a9a7878789a9a789a78789a789a9a9a7878789a9a567878789a9a7878
	789a9a789a78789a789a9a9a7878789a9a567878789a9a7878789a9a789a78789a789a9a9a7878789a94012323230423230404042323232304042304230423232304040123232304232304040423232323040423042304232323040401232323042323040404232323230404230423042323230404012323230423230404042323232304042304230423232304045678787
	89a7878949a9a787878789a9a789a789a7878789a9a567878789a7878949a9a787878789a9a789a789a7878789a9a567878789a78789a9a9a787878789a9a789a789a7878789a9a567878789a78789a9a9a787878789a9a789a789a7878789a9401232323042304042323042323042304232304230423230404012323230423040423230423230423042323042304232304
	040123232304230404232304232304230423230423042323040401232323042304042323042323042304232304230423230404567878789a789a9a78789a78789a789a78789a789a78789a94567878789a789a9a78789a78789a789a787894789a78789a9a567878789a789a9a78789a78789a789a78789a789a78789a9a567878789a789a9a78789a78789a789a78789a7
	89a78789a9401232323042323042323232323230423040423230423230404012323230423230423232323232304230
	
After choosing a name for the encoding (you can choose freely but I suggest to keep the default) you'll be asked to give the signal sequences for "init", "binary 1" and "binary 0". Those have to be extracted from the received signal sequence above. Once you've understood the underlying system (see sections *How it works* and *Configuration*) those are easy to spot:

In the received signal sequence you should find repeating patterns which start with an "init" sequence consisting of two signals followed by a sequence of binary 1s and 0s each encoding by two signals. The received signal sequence above for example contains the following patterns:

	047878789494 (initial rubbish)
	01232323042304042323042323042304232304230423230404 (init sequence 01, followed by pairs of 23 and 04)
	01232323042304042323042323042304232304230423230404
	012323230471
	Later on:
	567878789a789a9a78789a78789a789a78789a789a78789a9a (init sequence 56, followed by pairs of 78 and 9a)
	567878789a789a9a78789a78789a789a78789a789a78789a9a
	567878789a789a9a78789a78789a789a78789a789a78789a9a
	567878789a789a9a78789a78789a789a78789a789a78789a94
	
Those are your encodings:

 - Encoding 1: 01 = Init, 23 = binary 1, 04 = binary 0
 - Encoding 2: 56 = Init, 78 = binary 1, 9a = binary 0

Which one you define as binary 1 and which as binary 0 does not matter. But you have to be consistent between the two encodings. You might have noticed that `01232323042304042323042323042304232304230423230404` and `567878789a789a9a78789a78789a789a78789a789a78789a9a` encode the same data just with two different encodings. So if you choose to set `23` as binary 1 you also have to set `78` as binary 1.

**sequences** is used to determine the actual data that is sent for each command (like "switch on socket A").

For that you have to determine the data which is sent for each button (socket command combination) you want to be able to use.
Please follow the instructions of the script. You should get an output similar to the following. (If not, you most probably made a mistake during the "encodings" step. Please try to redo it.):

	1110-1100011110010101-1100
	1110-1100011110010101-1100
	1110-1100-0111
	1110-1100
	1110-110001111001010-1110
	1110-110001-1110
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-1001101101011010-1100
	1110-100110110101101-0110
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-1101111110100110-1100
	1110-11011111101001-1011
	1110-0111001011010001-1100
	[...]

As you can see each set of data is sent eight times (4 times in encoding 1 and 4 times in encoding 2 (you cannot see the different encodings here)). Now you have to tell the script the "start data", "data sequence" and "end data" for each button (socket command combination). The "start data" should be the same for all buttons, the "end data" should be unique for each socket (not button!) and you should be able to see four different "data sequences". The script helps to distinguish between the three by separating them with dashes. In this example the "start data" is `1110`, the "end data" is `1100` and the "data sequences" are `1100011110010101`, `1001101101011010`, `1101111110100110` and `0111001011010001` (the last one was be repated, too, but was truncated here).

Once you have found all the data sent with the buttons on your remote, you'll find your config file specific for your sockets in `~/.gtsocket/config.ini` and you are ready to go and test with the `gtsocket-test` script.

Testing script - gtsocket-test
------------------------------

Use the following command to send a command to a specific socket (in this example send command 'on' to socket 'A'):

	gtsocket-test -m send -s A -c on
	
To receive and print to stdout commands for a specific socket for a certain amount of time (in this example socket 'B' for 5 sec):

	gtsocket-test -m receive -s B -t 5
	
Known issues
============

 - Receiving signals/commands from the remote for multiple sockets at the same time does not work well. 
	In that case many signals are not recognized correctly which leads to commands not being detected.
