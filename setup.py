import os
import sys

EXE_FILE = 'export'

def setup(arg = ''):
	RUN_COMMAND = "nohup python3 -u %s.py &" % EXE_FILE

	if arg != 'debug':
		r = os.system('sudo pip3 install -r requirements.txt')
		if r != 0:
			os.system('curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py')
			os.system('sudo python3 get-pip.py')
			os.system('rm get-pip.py')
			os.system('sudo pip3 install -r requirements.txt')
	try:
		from telegram.ext import Updater, MessageHandler, Filters
	except:
		os.system('sudo pip3 install python-telegram-bot --upgrade') # need to use some experiement feature, e.g. message filtering

	try:
		import yaml
		with open('TELEGRAPH_TOKENS') as f:
			TELEGRAPH_TOKENS = yaml.load(f, Loader=yaml.FullLoader)
	except:
		with open('TELEGRAPH_TOKENS', 'w') as f:
			f.write(yaml.dump({}, sort_keys=True, indent=2))

	# kill the old running bot if any. If you need two same bot running in one machine, use mannual command instead
	os.system("ps aux | grep ython | grep %s | awk '{print $2}' | xargs kill -9" % EXE_FILE)

	if arg.startswith('debug'):
		os.system(RUN_COMMAND[6:-2])
	else:
		os.system(RUN_COMMAND)


if __name__ == '__main__':
	if len(sys.argv) > 1:
		setup(sys.argv[1])
	else:
		setup('')