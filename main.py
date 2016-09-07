import challonge
import config
import sys
import pickle
import os
import re
import urllib
import csv
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QDesktopWidget,
	QAction, qApp, QWidget, QGridLayout, QListWidget, QDialog, QInputDialog, QListWidgetItem,
	QLineEdit, QLabel, QMessageBox, QComboBox)
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import Qt

DEFAULT_SCORING = [15, 12, 10, 8, 5, 5, 3, 3]

DEFAULT_CSV_PATH = os.getcwd().replace('\\', '/') + '/csv/'

setDict = {}
tournamentDict = {}
nthDict = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th', 6: '6th', 7: '7th', 8: '8th', 9: '9th', 10: '10th', 11: '11th', 12: '12th', 13: '13th'}

def saveData():
	with open('userdata/setlist.pickle', 'wb') as f:
		pickle.dump(setDict, f, pickle.HIGHEST_PROTOCOL)
	with open('userdata/tournamentlist.pickle', 'wb') as f:
		pickle.dump(tournamentDict, f, pickle.HIGHEST_PROTOCOL)

def loadSetDict():
	if os.path.isfile('userdata/setlist.pickle'):
		with open('userdata/setlist.pickle', 'rb') as f:
			return pickle.load(f)
			
def loadTournamentDict():
	if os.path.isfile('userdata/tournamentlist.pickle'):
		with open('userdata/tournamentlist.pickle', 'rb') as f:
			return pickle.load(f)

def loadData():
	global setDict, tournamentDict
	setDict = loadSetDict()
	tournamentDict = loadTournamentDict()
	
def deleteData():
	if os.path.isfile('userdata/setlist.pickle'):
		os.remove('userdata/setlist.pickle')
	if os.path.isfile('userdata/tournamentlist.pickle'):
		os.remove('userdata/tournamentlist.pickle')
		
def exportCSV(path, filename, set):	# should return false on error, not yet implemented. csv file is also incredibly ugly
	set.calculateRankings()
	rankingsList = set.returnRankings()
	if not os.path.isdir(path):
		os.makedirs(path)
	with open(path + filename, 'w+', newline='') as csvfile:
		fieldnames = ['Player', 'Score']
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writerow({'Player': set.name, 'Score': '{!s}'.format(datetime.date.isoformat(datetime.date.today()))}) # must be better way of using multiple columns
		writer.writerow({'Player': '', 'Score': ''})
		writer.writeheader()
		for r in rankingsList:
			writer.writerow({'Player': r[0], 'Score': r[1]})
	return True
				
class Set:	## add sets with newSet = Set(s); setDict[s] = newSet --- make this a function probably
	def __init__(self, name):
		self.name = name
		self.tournaments = {}
		self.rankings = {}
		if 'settings' in config.config and 'scoring' in config.config['settings']:	# ability to set default scoring not yet implemented
			self.scoring = config.config['settings']['scoring']
		else:
			self.scoring = DEFAULT_SCORING
		saveData()
		
	def addTournament(self, url):
		if url in self.tournaments:
			raise ValueError('Tournament already exists.')
		elif url in tournamentDict:
			self.tournaments[url] = tournamentDict[url]
		else:
			self.tournaments[url] = Tournament(url)
		self.tournaments[url].sets.append(self)
		saveData()
		return True
		
	def removeTournament(self, url):
		if url not in self.tournaments:
			return False
		else:
			self.tournaments[url].sets.remove(self)
			if len(self.tournaments[url].sets) == 0:
				del tournamentDict[url]
			del self.tournaments[url]
		saveData()
			
	def removeSet(self):
		for key, t in self.tournaments.items():
			t.sets.remove(self)
			if len(t.sets) == 0:
				del tournamentDict[t.url]
		del setDict[self.name]
		saveData()
		
	def calculateRankings(self):
		self.rankings = {}
		for key, t in self.tournaments.items():
			for name, rank in t.participants.items():
				if name not in self.rankings:
					self.rankings[name] = 0
				if rank <= len(self.scoring):
					self.rankings[name] += self.scoring[rank - 1]

	def returnRankings(self):
		return sorted(self.rankings.items(), key=lambda x: x[1], reverse=True)
		
class Tournament:
	def __init__(self, url):
		self.url = url
		self.sets = []
		t = challonge.tournaments.show(url)
		p = challonge.participants.index(t['id'])
		self.participants = {}
		for participant in p:
			if participant['challonge-username'] is not None and participant['final-rank'] is not None:
				self.participants[participant['challonge-username']] = participant['final-rank']
		tournamentDict[url] = self
					
	def returnResults(self):
		return sorted(self.participants.items(), key=lambda x: x[1])
		
def loadConfig():
	if config.configExists():
		config.loadConfig()
		challonge.set_credentials(config.config['challonge']['username'], config.config['challonge']['apiKey'])
	else:
		pass
		
class MainWindow(QMainWindow):

	def __init__(self):
		super().__init__()
		
		self.initUI()
		
	def initUI(self):
	
		exitAction = QAction(QIcon(), '&Exit', self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(qApp.quit)
		
		challongeLoginAction = QAction(QIcon(''), 'Challonge Login', self)
		challongeLoginAction.setStatusTip('Login using challonge username and api key')	
		challongeLoginAction.triggered.connect(self.challongeLoginClicked)
		
		settingsAction = QAction(QIcon(''), 'Settings', self)
		settingsAction.setStatusTip('Change settings')
		settingsAction.triggered.connect(self.settingsActionClicked)
		
		deleteDataAction = QAction(QIcon(''), 'Delete all data', self)
		deleteDataAction.setStatusTip('Deletes all tournament and set data')
		deleteDataAction.triggered.connect(self.deleteDataClicked)
		
		menuBar = self.menuBar()
		fileMenu = menuBar.addMenu('&File')
		fileMenu.addAction(challongeLoginAction)
		fileMenu.addAction(settingsAction)
		fileMenu.addAction(exitAction)
		fileMenu.addAction(deleteDataAction)

		self.mainWidget = MainWidget(self)
		self.setCentralWidget(self.mainWidget)
	
		self.resize(1000, 600)
		self.center()
		self.setWindowTitle('Hypest-Rankings')
		self.setWindowIcon(QIcon('logo.png'))
		
		self.show()
		
	def center(self):
		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())
		
	def challongeLoginClicked(self):
		challongeLoginDialog = ChallongeLoginWindow(self)
		challongeLoginDialog.show()
		
	def settingsActionClicked(self):
		settingsDialog = SettingsWindow(self)
		settingsDialog.show()
		
	def deleteDataClicked(self):
		ok = QMessageBox.question(self, '', 'Really delete all set and tournament data?',
			QMessageBox.Yes, QMessageBox.No)
		if ok == QMessageBox.Yes:
			deleteData()
			
		
class MainWidget(QWidget):

	def __init__(self, parent):
		super(MainWidget, self).__init__(parent)
		
		self.initUI()
	
	def initUI(self):
		self.listSet = QListWidget(self)
		self.listSet.itemClicked.connect(self.setClicked)
		
		self.listTournament = QListWidget(self)
		
		self.listRankings = QListWidget(self)
		self.listRankings.currentResults = None
	
		btnAddSet = QPushButton('Add Set', self)
		btnAddSet.clicked.connect(self.btnAddSetClicked)
		
		btnRemoveSet = QPushButton('Remove Set', self)
		btnRemoveSet.clicked.connect(self.btnRemoveSetClicked)
		
		btnEditSet = QPushButton('Edit Set', self)
		btnEditSet.clicked.connect(self.btnEditSetClicked)
		
		btnShowSetRankings = QPushButton('Show Set Leaderboard', self)
		btnShowSetRankings.clicked.connect(self.btnShowSetRankingsClicked)
		
		btnExportCSV = QPushButton('Export Set Rankings to CSV', self)
		btnExportCSV.clicked.connect(self.btnExportCSVClicked)
		
		btnAddTournament = QPushButton('Add Tournament', self)
		btnAddTournament.clicked.connect(self.btnAddTournamentClicked)
		
		btnRemoveTournament = QPushButton('Remove Tournament', self)
		btnRemoveTournament.clicked.connect(self.btnRemoveTournamentClicked)
		
		btnShowTournamentRankings = QPushButton('Show Tournament Results', self)
		btnShowTournamentRankings.clicked.connect(self.btnShowTournamentRankingsClicked)
		
		self.labelRankings = QLabel('', self)
		self.labelRankings.setMaximumHeight(20)
		
		grid = QGridLayout()
		grid.setSpacing(10)
		
		grid.addWidget(self.listSet, 1, 0, 5, 1)
		
		grid.addWidget(btnAddSet, 1, 1)
		grid.addWidget(btnRemoveSet, 2, 1)
		grid.addWidget(btnEditSet, 3, 1)
		grid.addWidget(btnShowSetRankings, 4, 1)
		grid.addWidget(btnExportCSV, 5, 1)
		
		grid.addWidget(self.listTournament, 1, 2, 5, 1)
		
		grid.addWidget(btnAddTournament, 1, 3)
		grid.addWidget(btnRemoveTournament, 2, 3)
		grid.addWidget(btnShowTournamentRankings, 3, 3)
		
		grid.addWidget(self.labelRankings, 0, 4)
		grid.addWidget(self.listRankings, 1, 4, 5, 1)
				
		self.setLayout(grid)
		
		self.loadSetList()
		
	def btnExportCSVClicked(self):
		if self.listSet.currentItem():
			filename = '{}.csv'.format(self.listSet.currentItem().text())
			path = ''
			if 'settings' in config.config and 'csvpath' in config.config['settings']:
				path = config.config['settings']['csvpath']
			else:
				path = DEFAULT_CSV_PATH
			text, ok = QInputDialog.getText(self, '', 'Specify filename and path', QLineEdit.Normal, path + filename)
			
			if ok:
				pathList = text.split('/')
				filename = pathList.pop()
				path = '/'.join(pathList) + '/'
				set = setDict[self.listSet.currentItem().text()]
				if os.path.isfile(path + filename):
					messageBox = QMessageBox.question(self, '',
						'File already exists, overwrite?', QMessageBox.Yes, QMessageBox.No)
					if messageBox == QMessageBox.No:
						return
				if exportCSV(path, filename, set):
					msgBox = QMessageBox.information(self, '', '{} exported to file'.format(text))
				else:
					msgBox = QMessageBox.warning(self, 'Error', 'Error occurred exporting {}'.format(text))
		
	def btnRemoveTournamentClicked(self):
		if self.listTournament.currentItem() and self.listSet.currentItem():
			tournament = self.listTournament.currentItem().text()
			ok = QMessageBox.question(self, '',
				'Remove tournament {}?'.format(tournament), QMessageBox.Yes, QMessageBox.No)
			if ok == QMessageBox.Yes:
				setDict[self.listSet.currentItem().text()].removeTournament(tournament)
				rmItem = self.listTournament.takeItem(self.listTournament.currentRow())
				rmItem = None
				if self.listRankings.currentResults == tournament:
					self.listRankings.clear()
					self.listRankings.currentResults = None
				elif self.listRankings.currentResults == self.listSet.currentItem().text():
					self.btnShowSetRankingsClicked()
		
	def btnShowSetRankingsClicked(self): # Method may need to be updated when better data persistence implemented
		self.listRankings.clear()
		self.labelRankings.setText('')
		if self.listSet.currentItem():
			self.labelRankings.setText('Showing leaderboard for set {}'.format(self.listSet.currentItem().text()))
			setDict[self.listSet.currentItem().text()].calculateRankings()
			rankingsList = setDict[self.listSet.currentItem().text()].returnRankings()
			for r in rankingsList:
				item = '{}: {}'.format(r[0], str(r[1]))
				self.listRankings.addItem(item)
			self.listRankings.currentResults = self.listSet.currentItem().text()
		
	def btnShowTournamentRankingsClicked(self): # See above. Also formatting of results could be better
		self.listRankings.clear()
		self.labelRankings.setText('')
		if self.listTournament.currentItem():
			self.labelRankings.setText('Results for tournament {}'.format(self.listTournament.currentItem().text()))
			resultsList = tournamentDict[self.listTournament.currentItem().text()].returnResults()
			for player in resultsList:
				placing = ''
				if player[1] <= 13:
					placing = nthDict[player[1]]
				else:
					modulus = player[1] % 10
					if modulus == 1:
						placing = '{!s}st'.format(player[1])
					elif modulus == 2:
						placing = '{!s}nd'.format(player[1])
					elif modulus == 3:
						placing = '{!s}rd'.format(player[1])
					else:
						placing = '{!s}th'.format(player[1])
				item = '{} - {}'.format(placing, player[0])
				self.listRankings.addItem(item)
			self.listRankings.currentResults = self.listTournament.currentItem().text()
		
	def btnRemoveSetClicked(self):
		if self.listSet.currentItem():
			set = self.listSet.currentItem().text()
			ok = QMessageBox.question(self, '',
				'Remove set {}?'.format(set), QMessageBox.Yes, QMessageBox.No)
			if ok == QMessageBox.Yes:
				setDict[set].removeSet()
				item = self.listSet.takeItem(self.listSet.currentRow())
				item = None
				self.listTournament.clear()
				self.listRankings.clear()
			
	def btnAddTournamentClicked(self):
		if self.listSet.currentItem():
			window = AddTournamentWindow(self, self.listSet.currentItem())
			window.inputTournamentName.setFocus()
			window.show()
	
	def setClicked(self, item):
		self.listTournament.clear()
		set = item.text()
		for t in setDict[set].tournaments:
			i = QListWidgetItem(t)
			self.listTournament.addItem(i)
		
	def loadSetList(self):
		self.listSet.clear()
		for s in setDict:
			item = QListWidgetItem(s)
			self.listSet.addItem(item)

	def addToSetList(self, set):
		item = QListWidgetItem(set.name)
		self.listSet.addItem(item)

	def btnAddSetClicked(self):
		s, ok = QInputDialog.getText(self, 'Add Set', '')

		if ok:
			if s in setDict:
				errBox = QMessageBox.warning(self, 'Error', 'Set with name already exists')
			elif s.replace(' ', '') == '':
				errBox = QMessageBox.warning(self, 'Error', 'Invalid set name')
			else:
				newSet = Set(s)
				setDict[s] = newSet
				self.addToSetList(newSet)
				saveData()
		
	def btnEditSetClicked(self):
		if self.listSet.currentItem():
			editSetDialog = EditSetWindow(self, setDict[self.listSet.currentItem().text()])
			editSetDialog.show()
			saveData()
			
class AddTournamentWindow(QDialog):
	def __init__(self, parent, set):
		super(AddTournamentWindow, self).__init__(parent)
		self.set = set
		self.mainWindow = parent
		self.initUI()
		
	def initUI(self):
		self.setWindowTitle('Add Tournament')
		
		btnOK = QPushButton('OK', self)
		btnOK.clicked.connect(self.btnOKClicked)
		
		btnCancel = QPushButton('Cancel', self)
		btnCancel.clicked.connect(self.btnCancelClicked)
		
		self.inputTournamentName = QLineEdit()
		self.inputTournamentName.textChanged.connect(self.inputTournamentNameChangeEvent)
		
		self.dropDownMenu = QComboBox()
		self.dropDownMenu.addItem('')
		for key, t in tournamentDict.items():
			if setDict[self.set.text()] not in t.sets:
				self.dropDownMenu.addItem(key)
		self.dropDownMenu.activated.connect(self.dropDownMenuChangeEvent)

		self.resize(600, 300)
		
		grid = QGridLayout()
		
		grid.addWidget(btnOK, 1, 1)
		grid.addWidget(btnCancel, 1, 2)
		
		grid.addWidget(self.inputTournamentName, 0, 0, 1, 2)
		grid.addWidget(self.dropDownMenu, 0, 2)
		
		self.setLayout(grid)
		
	def inputTournamentNameChangeEvent(self, text):
		index = self.dropDownMenu.findText(text)
		if index == -1:
			self.dropDownMenu.setCurrentIndex(0)
		else:
			self.dropDownMenu.setCurrentIndex(index)	
				
	def dropDownMenuChangeEvent(self):
		t = self.dropDownMenu.currentText()
		self.inputTournamentName.setText(t)
		
	def btnOKClicked(self):
		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
		QApplication.processEvents()
		t = self.inputTournamentName.text()
		try:
			setDict[self.set.text()].addTournament(t)
			self.mainWindow.setClicked(self.set)
			QApplication.restoreOverrideCursor()
			if self.mainWindow.listRankings.currentResults == self.set.text():
				self.mainWindow.btnShowSetRankingsClicked()
			self.close()
		except urllib.error.HTTPError as e:
			QApplication.restoreOverrideCursor()
			self.showHTTPError(e)
		except ValueError as e:
			QApplication.restoreOverrideCursor()
			errBox = QMessageBox.warning(self, 'Error', str(e))
			
	def btnCancelClicked(self):
		self.close()
		
	def showHTTPError(self, err):
		msg = ''
		if err.code == 400:
			msg = 'HTTP Error 400: Bad request. Check URL.'
		elif err.code == 401:
			msg = 'HTTP Error 401: Challonge details incorrect or insufficient permissions.'
		elif err.code == 404:
			msg = 'HTTP Error 404: Object not found within your challonge account scope. Check URL.'
		elif err.code == 406:
			msg = 'HTTP Error 406: Requested format not supported - something has gone horribly wrong.'
		elif err.code == 422:
			msg = 'HTTP Error 422: Challonge validation error.'
		elif err.code == 500:
			msg = 'HTTP Error 500: Challonge service error.'
		else:
			msg = 'Unforeseen error: {}'.format(str(e))
		errBox = QMessageBox.warning(self, 'Error', msg)
		
class EditSetWindow(QDialog):
	def __init__(self, parent, set):
		super(EditSetWindow, self).__init__(parent)
		
		self.mainWidget = parent
		
		self.set = set
		
		self.initUI()
		
	def initUI(self):
		labelName = QLabel('Name:')
		labelScoring = QLabel('Scoring:')
		
		self.inputName = QLineEdit()
		self.inputScoring = QLineEdit()
		
		self.inputName.setText(self.set.name)
		self.inputScoring.setText(str(self.set.scoring))
		
		btnSetName = QPushButton('OK', self)
		btnSetName.clicked.connect(self.btnSetNameClicked)
		
		btnSetScoring = QPushButton('OK', self)
		btnSetScoring.clicked.connect(self.btnSetScoringClicked)
		
		btnDone = QPushButton('Done', self)
		btnDone.clicked.connect(self.btnDoneClicked)
		
		self.resize(600, 300)
		
		grid = QGridLayout()
		grid.setSpacing(3)
		
		grid.addWidget(labelName, 0, 0)
		grid.addWidget(self.inputName, 0, 1)
		grid.addWidget(btnSetName, 0, 2)
		
		grid.addWidget(labelScoring, 1, 0)
		grid.addWidget(self.inputScoring, 1, 1)
		grid.addWidget(btnSetScoring, 1, 2)
		
		grid.addWidget(btnDone, 3, 1)
		
		self.setLayout(grid)
		
	def btnSetNameClicked(self):
		if self.inputName.text() in setDict:
			self.inputName.setText(self.set.name)
			errBox = QMessageBox.warning(self, 'Error', 'Set with name already exists')
		elif self.inputName.text().replace(' ', '') == '':
			self.inputName.setText(self.set.name)
			errBox = QMessageBox.warning(self, 'Error', 'Invalid set name')
		else:
			del setDict[self.set.name]	# double check effect of this method on tournament.sets
			self.set.name = self.inputName.text()
			setDict[self.set.name] = self.set
			self.mainWidget.loadSetList()
			saveData()
		
		
	def btnSetScoringClicked(self):
		input = self.inputScoring.text()
		if input == '':
			self.inputScoring.setText(str(self.set.scoring))
			errBox = QMessageBox.warning(self, 'Error', 'Invalid input')
		input = re.sub(r'[\[\]]|\s+', '', input)
		input = input.split(',')
		scoring = []
		try:
			for x in input:
				scoring.append(int(x))
			self.set.scoring = scoring
			saveData()
			if self.mainWidget.listRankings.currentResults == self.set.name:
				self.mainWidget.btnShowSetRankingsClicked()
		except ValueError:
			self.inputScoring.setText(str(self.set.scoring))
			errBox = QMessageBox.warning(self, 'Error', 'Invalid input')
		
	def btnDoneClicked(self):
		self.close()
			
class ChallongeLoginWindow(QDialog):

	def __init__(self, parent):
		super(ChallongeLoginWindow, self).__init__(parent)
		
		self.initUI()
		
	def initUI(self):
		self.setWindowTitle('Challonge Login')
	
		labelUsername = QLabel('Username:')
		labelApi = QLabel('API Key:')
	
		self.inputUsername = QLineEdit()
		self.inputApi = QLineEdit()
		
		if 'challonge' in config.config:
			self.inputUsername.setText(config.config['challonge']['username'])
			self.inputApi.setText(config.config['challonge']['apiKey'])
		
		btnOK = QPushButton('OK', self)
		btnOK.clicked.connect(self.btnOKClicked)
		
		btnCancel = QPushButton('Cancel', self)
		btnCancel.clicked.connect(self.btnCancelClicked)
		
		btnClear = QPushButton('Clear', self)
		btnClear.clicked.connect(self.btnClearClicked)
		
		self.resize(600, 300)
		
		grid = QGridLayout()
		grid.setSpacing(2)
		
		grid.addWidget(labelUsername, 0, 0)
		grid.addWidget(labelApi, 1, 0)
		
		grid.addWidget(self.inputUsername, 0, 1, 1, 2)
		grid.addWidget(self.inputApi, 1, 1, 1, 2)
		
		grid.addWidget(btnOK, 2, 0)
		grid.addWidget(btnCancel, 2, 1)
		grid.addWidget(btnClear, 2, 2)
		
		self.setLayout(grid)
		
	def btnOKClicked(self):
		config.setConfigChallonge(self.inputUsername.text(), self.inputApi.text())
		challonge.set_credentials(self.inputUsername.text(), self.inputApi.text())
		self.close()
	
	def btnCancelClicked(self):
		self.close()
		
	def btnClearClicked(self):
		ok = QMessageBox.question(self, '',
			'Clear Challonge login details?', QMessageBox.Yes, QMessageBox.No)
		if ok == QMessageBox.Yes:
			config.clearChallongeConfig()
			self.inputUsername.setText('')
			self.inputApi.setText('')
				
class SettingsWindow(QDialog):
	def __init__(self, parent):
		super(SettingsWindow, self).__init__(parent)
		
		self.initUI()
		
	def initUI(self):
		self.setWindowTitle('Settings')
		
		labelCSVPath = QLabel('Default folder for CSV files')
		
		self.inputCSVPath = QLineEdit()
		if 'settings' in config.config and 'csvpath' in config.config['settings']:
			self.inputCSVPath.setText(config.config['settings']['csvpath'])
		else:
			self.inputCSVPath.setText(DEFAULT_CSV_PATH)
			
		btnSave = QPushButton('Save', self)
		btnSave.clicked.connect(self.btnSaveClicked)
		
		btnCancel = QPushButton('Cancel', self)
		btnCancel.clicked.connect(self.btnCancelClicked)
			
		self.resize(600, 300)
		
		grid = QGridLayout()
		
		grid.addWidget(labelCSVPath, 0, 0)
		grid.addWidget(self.inputCSVPath, 0, 1)
		
		grid.addWidget(btnSave, 1, 0)
		grid.addWidget(btnCancel, 1, 1)
		
		self.setLayout(grid)
		
	def btnSaveClicked(self):
		config.setConfigCSVPath(self.inputCSVPath.text())
		self.close()
		
	def btnCancelClicked(self):
		self.close()		

if __name__ == '__main__':

	app = QApplication(sys.argv)	
	loadConfig()
	if os.path.isfile('userdata/setlist.pickle'):
		loadData()
	w = MainWindow()	
	sys.exit(app.exec_())