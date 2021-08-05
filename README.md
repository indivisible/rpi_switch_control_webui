Control your nintendo switch with a Raspberry Pi Zero!

What you need:

* a Raspberry Pi Zero W (other SBCs with USB gadget mode could work, but this is the only one I've tested)
* a power source for the raspberry (trying to power it off the switch gets wonky)
* being comfortable with Linux. Sorry, no pre-made SD image yet!

To get it working:

1. install raspbian or whatever you're comfortable with on the raspberry
1. install some basic tools: `sudo apt-get install git python3-pip`, [go](https://golang.org/doc/install)
1. install [omakoto/raspberry-switch-control](https://github.com/omakoto/raspberry-switch-control/)
1. clone and install this repo:
   1. `git clone https://github.com/indivisible/rpi_switch_control_webui`
   1. `cd rpi_switch_control_webui`
   1. `sudo pip3 install -r requirements.txt`
1. then on every boot:
   1. run the gadget setup script: `sudo $HOME/go/src/github.com/omakoto/raspberry-switch-control/scripts/switch-controller-gadget`
   1. run the web frontend: `cd rpi_switch_control_webui && sudo python3 webui.py -- /home/pi/go/bin/nsbackend`
   1. (make sure you're not running it in an interactive SSH session to avoid disconnection stopping it. Maybe use `tmux` or `screen`)
1. connect to the interfaces on `http://THE-RASPBERRYS-IP:8000/` and maybe on `http://THE-RASPBERRYS-IP:8000/controller_test.html` (if you have a Switch pro controller connected to your PC via USB and use Chrome)

For some sample macros see the `macro_examples` directory

Current problems:

* hard to set up, no installer
* no startup script
* no wake support
* remote control can get a bit laggy
* macro language is not very powerful
* no documentation or tests
