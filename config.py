from configparser import ConfigParser
import os

config = ConfigParser()

configPath = 'userdata/config.ini'

def configExists():
	if os.path.isfile(configPath):
		return True
	else:
		return False
		
def loadConfig():
	if configExists():
		config.read(configPath)
		
def clearChallongeConfig():
	config['challonge']['username'] = ''
	config['challonge']['apiKey'] = ''
	saveConfig()
		
def saveConfig():
	if os.path.exists('userdata/') is False:
		os.makedirs('userdata')
	with open(configPath, 'w') as configFile:
		config.write(configFile)
		
def setConfigChallonge(name, api):
	config['challonge'] = {}
	config['challonge']['username'] = name
	config['challonge']['apiKey'] = api
	saveConfig()

def setConfigCSVPath(path):
	if path[len(path) - 1] != '/':
		path = path + '/'
	if 'settings' not in config:
		config['settings'] = {}
	config['settings']['csvpath'] = path
	saveConfig()
	
def setDefaultScoring(list):
	if 'settings' not in config:
		config['settings'] = {}
	config['settings']['defaultscoring'] = list
	saveConfig()