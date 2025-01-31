#import SimpleGUI Framework to use in the project 
import PySimpleGUI as sg
from deckWrapper import DeckWrapper
from typing import List
import pandas as pd
import numpy as np
import csvManip as csvManip
import os
from cardDB import *
from clusters import *
import csv
import subprocess
from tkinter import *
import json
import random
from copy import deepcopy #we want new values not reference 
import time
import threading
from deleteFiles import *
from testClassify import *

def makedir(name):
	try:
		os.mkdir(name)
	except:
		pass

makedir('outputs')
makedir('outputs/labels')
makedir('outputs/outputCSV')
makedir('outputs/tmp')
makedir('outputs/labels/NEW_labels')



CLASSES=["DEMONHUNTER", 'DRUID', 'HUNTER', 'MAGE', 'PALADIN', 'PRIEST', 'ROGUE', 'SHAMAN', 'WARLOCK', 'WARRIOR']

def updateTextWindow(window, id, text):
	window[id].update(text)

def getNRandomItems(myList, n):
	return random.sample(myList, n)


def print_pretty_decks(player_class, clusters):
	#print("Printing Clusters For: %s" % player_class)
	i = 0
	L = []
	for cluster in clusters:
		#print("%s" % str(cluster))
		j = 0
		for deck in cluster.decks:
			#print("\t%s" % deck.deckCode)
			L.append(("c{}.{}".format(i,j),deck.deckCode))
			j+=1
		i+=1

	#write to CSV
	uniqueID = "{}{}".format(player_class, i)
	directName = "outputs/{}".format(player_class)
	if not os.path.exists("{}".format(directName)):
		os.mkdir("{}".format(directName))
	if not os.path.exists("{}/{}".format(directName, i)):
		os.mkdir("{}/{}".format(directName, i))
	df = pd.DataFrame(L, columns=['K', 'D'])
	df.to_csv("{}/{}/{}.csv".format(directName,i, uniqueID), encoding='utf-8', index=False, mode='w')

def toClassify():

	labelData = ""
	testData = ""

	layout = [[sg.Text("Welcome To Deck Classifier!")],
			[sg.Text("2 Items are required, labelDirect is folder of labels from a previous Clustering")],
			[sg.Text("and deckCSV is input CSV to classify using those labels")],
			[sg.Text("Input labelDirect"), sg.InputText(size=(50,1), enable_events=True, key="-FILE_LABEL-"), sg.FolderBrowse()],
			[sg.Text("Input deckCSV"), sg.InputText(size=(50,1), enable_events=True, key="-FILE_DECK-"), sg.FileBrowse(file_types=(("CSVs","*.csv"),))],
			[sg.Text("Output:"), sg.Text(size=(40,1), key='-OUTPUT-')],
			[sg.Text("")],
			[sg.Text("Next will Classify your decks, this may take some time")],
			[sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]]

	window = sg.Window("Deck Classification Tool", layout)
	myOutput = ""
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Cancel': 
		# if user closes window or clicks cancel
			window.close()
			quit()
		# if next is clicked go next
		if event == "Next" and labelData != "" and testData != "":
			break

		# Get File name
		if event == "-FILE_LABEL-":
			labelData = values["-FILE_LABEL-"]

		if event == "-FILE_DECK-":
			testData = values["-FILE_DECK-"]
	window.close()
	#Run classification
	layout = [[sg.Text("Classifyings: This will take some time",key="-MOTION-")],
				[sg.Text("Setting Up for Clustering", key="-UPDATE-", size=(100, 2))]]
	window = sg.Window("Deck Cluster Tool", layout, size=(500,500))
	window.read(timeout=0.00001)



	deckDict = {}
	classLists = []
	deckDict, classLists, linecount = parseDeckInput(testData, deckDict, classLists)

	for labelIn, classList, hero in zip(os.listdir(labelData),classLists, CLASSES):
		window["-UPDATE-"].update("Classifying {} {} decks".format(len(classList), hero))
		window.read(timeout=0.00001)
		classList = testClassify("{}/{}".format(labelData, labelIn), classList, hero)

	window.close()
	#regeneate default Dict for output
	layout=[ [sg.Text("Classification Complete")],
			[sg.Text("Exporting Data")]]
	window = sg.Window("Deck Cluster Tool", layout)
	window.read(timeout=0.0001)

	outputDeckDict = {}
	outputList = []

	for dataPoints in classLists:
		for dp in dataPoints:
			if dp.teamName not in outputDeckDict:
				outputDeckDict[dp.teamName] = []
			outputDeckDict[dp.teamName].append(deepcopy(dp))

	# list the output
	for name in outputDeckDict:
		subList = []
		subList.append(name)
		for deck in outputDeckDict[name]:
			subList.append("{} {}".format(deck.classification, deck.ingameClass))
		outputList.append(subList)

	



	classifyDict = {}
	classCountDict={}
	for name in outputDeckDict:
		#PDict[name] = []
		for x in outputDeckDict[name]:
			y = "{} {}".format(x.classification, x.ingameClass)
			if x.ingameClass not in classCountDict:
				classCountDict[x.ingameClass.lower()] = 0
			if y not in classifyDict:
				classifyDict[y] = 0
			classifyDict[y] +=1
			classCountDict[x.ingameClass.lower()]+=1

	with open("outputs/outputCSV/{}_counts.csv".format(os.path.splitext(os.path.basename(testData))[0]), "w+", encoding='utf-8') as f:
		for class_ in classCountDict:
			f.write("{},{}\n".format(class_, classCountDict[class_]))
		f.write("\n\n")

		for deck in classifyDict:
			f.write("{},{}\n".format(deck, classifyDict[deck]))

	#for q, t in zip(QDict, PDict):
		#print("{} wrong on {} : \n\t actual:  {} \t\t  output:{}\n".format(q, list(set(PDict[q])-set(QDict[q])),list(QDict[q]),list(PDict[q])))
		#w+= len( list(set(PDict[q])-set(QDict[q])))

	#print(float(1-(w/(36*4))))

	df = pd.DataFrame(outputList)
	df.to_csv("outputs/outputCSV/{}_archetypes.csv".format(os.path.splitext(os.path.basename(testData))[0]), encoding='utf-8', index=False, mode='w+')

	window.close()


def toCluster():
	cluster_counts = []
	filename=""
	#layout for first page
	layout = [[sg.Text("Welcome To Deck Clusterer Tool!")],
			[sg.Text("Input CSV"), sg.InputText(size=(50,1), enable_events=True, key="-FILE-"), sg.FileBrowse(file_types=(("CSVs","*.csv"),))],
			[sg.Text("Next will start parsing the CSV, this may take some time")],
			[sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]]


	#create teh window
	window = sg.Window("Deck Cluster Tool", layout)
	myOutput = ""
	#Event Loop to Gather Inputs for Cluster Count
	#event loop to process "events" that get "values" of inputs
	while True:
		event, values = window.read()
		if (event == sg.WIN_CLOSED or event == 'Cancel') and filename != "": 
		# if user closes window or clicks cancel
			window.close()
			quit()
		# if next is clicked go next
		if event == "Next":
			
			break



		# Get File name
		if event == "-FILE-":
			filename= values["-FILE-"]
		



	window.close()

	layout = [[sg.Text("Parsing CSV",key="-MOTION-")],
				[sg.Text("Loading From File, This may take some time", key="-UPDATE-")]]
	window = sg.Window("Deck Cluster Tool", layout, finalize=True)

	# DEBUG ONLY
	#filename = "CSVs/MTQ_IF_1to24.csv"


	# Parse CSV

	deckDict = {}
	classLists = []
	linecount = 0
	deckDict, classLists, linecount = csvManip.parse_csv(filename, deckDict, classLists, window)
	#for name in deckDict:
		#if len(deckDict[name]) != 3 or len(deckDict[name]) != 4:
			#print(name)
			#print(deckDict[name])
	deckCount = 0
	for i in classLists:
		deckCount+= len(i)

	window.close()

	#make next window
	layout=[ [sg.Text("Stage 2 Deck Parsing Complete!!")],
			 [sg.Text("Total Teams: {}".format(linecount)), sg.Text("Total Valid Decks: {}, Class Totals Below".format(deckCount))],
			 [sg.Text("DH: {}, Druid: {}, Hunter: {}, Mage: {}, Paladin: {}".format(len(classLists[0]), len(classLists[1]), len(classLists[2]), len(classLists[3]), len(classLists[4])))],
			 [sg.Text("Priest: {}, Rogue: {}, Shaman: {}, Warlock: {}, Warrior: {}".format(len(classLists[5]), len(classLists[6]), len(classLists[7]), len(classLists[8]), len(classLists[9])))],
			 [sg.Text("")],
			[sg.Text("Enter integer Cluster Counts for Each Class in form")],
			[sg.Text("DH"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Druid"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Hunter"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Mage"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Paladin"), sg.InputText('1', size=(5,1),  enable_events=True)],
			[sg.Text("Priest"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Rogue"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Shaman"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Warlock"), sg.InputText('1', size=(5,1),  enable_events=True), sg.Text("Warrior"), sg.InputText('1', size=(5,1),  enable_events=True)],
			 [sg.Text("")],
			 [sg.Text("Output:"), sg.Text(size=(40,1), key='-OUTPUT-')],
			[sg.Text("")],
			 [sg.Text("Press Next to Start Clustering, This may take some time")],
			 [sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]
			 												]

	window = sg.Window("Deck Cluster Tool", layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Cancel': 
		# if user closes window or clicks cancel
			window.close()
			break
		# if next is clicked go next
		if event == "Next":
			cluster_counts = []
			for i in range(0,10):
				cluster_counts.append(int(values[i]))
			break
		cluster_counts = []
		myOutput = ""
		#parse Cluster Counts
		
		for i in range(0,10):
			myOutput += (" {}".format(values[i]))
			
		window['-OUTPUT-'].update(myOutput)
	
		
	window.close()

	layout = [[sg.Text("Clustering Decks: This will take some time",key="-MOTION-")],
				[sg.Text("Setting Up for Clustering", key="-UPDATE-")]]
	window = sg.Window("Deck Cluster Tool", layout)
	window.read(timeout=0.00001)


#Start Clustering Phase

	
	superCluster = createSuperCluster(classLists, clusterNumbers=cluster_counts, window=window)


	window.close()

	#Get Layout
	layout=[ [sg.Text("Stage 3 Deck Clustering Complete!!")],
			 [sg.Text("")],
			 [sg.Text("Press Next to Start Stage 4: Classifictaion")],
			 [sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]]

	window = sg.Window("Deck Cluster Tool", layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Cancel': 
		# if user closes window or clicks cancel
			window.close()
			break
		if event == "Next":
			break
	window.close()

	layout = [[sg.Text("Stage 4 Classification:",key="-MOTION-")],
			[sg.Text("Generating Images: May take some Time", key="-UPDATE-")]]
	window = sg.Window("Deck Cluster Tool", layout)
	window.read(timeout=0.0001)

	L=[]
	#Generate frames to view sample decks
	#First we must generate a selection of decks to display
	for class_ in CLASSES:
		count = 0
		aCC = superCluster.getClassClusterByName(class_)
		for cluster in aCC.clusters:
			if len(cluster.decks) <= 3:
				# Case for each so we always have 3 decks in csv
				if len(cluster.decks) == 3:
					L.append(("{} {}".format(class_,count), cluster.decks[0].deckCode, cluster.decks[1].deckCode, cluster.decks[2].deckCode))
				if len(cluster.decks) == 2:
					L.append(("{} {}".format(class_,count), cluster.decks[0].deckCode, cluster.decks[1].deckCode, ""))
				if len(cluster.decks) == 1:
					L.append(("{} {}".format(class_,count), cluster.decks[0].deckCode, "", ""))
			else:
				#Randomly Select 3 to display
				randomSelection = getNRandomItems(cluster.decks, 3)
				L.append(("{} {}".format(class_,count), randomSelection[0].deckCode, randomSelection[1].deckCode, randomSelection[2].deckCode))
			count += 1

	df = pd.DataFrame(L, columns=['K','D','D','D'])
	df.to_csv("outputs/tmp/tmp.csv", encoding = 'utf-8', index=False, mode='w')
	

	#run decktoImagePNG so we have images to display
	cmd = "python decktoImagePNG.py deckcsv outputs/tmp/tmp.csv outputs/tmp"
	os.system(cmd)
	window.close()
	#os.mkdir("outputs/tmp")
	imageColumn = [ 
						[sg.Image(key="-IMAGE-", filename="", size=(1400,3000))]
		]
	textColumn = [			[sg.Text("Stage 4 Declaring Names on ", key="-CLASS-",size =(50,1))],
							[sg.Text("Next to Continue to Next Deck/Class/Stage")],
							[sg.Text("Decks in Cluster:      !", key="-DECKS-", size =(30,1) )],
							[sg.Text("Define this Deck: "), sg.InputText("", key="-INPUT-")],
					 		[sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]]
	layout = [ 
						[sg.Column(textColumn), sg.VSeparator(), sg.Column(imageColumn, scrollable=True, size=(1350,900))]
					 ]
	window = sg.Window("Cluster Classification", layout, size = (1400,900))
	window.read(timeout=0.001)
	for class_ in CLASSES:
		#define layout to display
		window['-CLASS-'].update("Stage 4 Declaring Names on {}".format(class_))

		#acctually display
		i=0
		aCC = superCluster.getClassClusterByName(class_)
		
		for cluster in aCC.clusters:
			window['-DECKS-'].update("Decks in Cluster: {}".format(len(cluster.decks)))
			window['-IMAGE-'].update(filename="outputs/tmp/{} {}.png".format(class_,i))
			event, values = window.read()
			if event == sg.WIN_CLOSED or event == 'Cancel': 
				# if user closes window or clicks cancel
				window.close()
				quit()
				break
			if event == "Next":
				if values["-INPUT-"] == "":
					cluster.name = "other"
				else:
					cluster.name = values["-INPUT-"]
				window['-INPUT-'].update("")
				
			
			#print(cluster)
			i+=1
			window.refresh()

			#update every deck in the cluster to its new name
			cluster.updateNames()
	window.close()

	#remove images for storage space
	
	deleteFiles("outputs/tmp/", "png")
	deleteFiles("outputs/tmp/", "csv")

	#End Stage 4

	#Export results and finish
	layout=[ [sg.Text("Stage 4 Deck Classification Complete!!")],
			[sg.Text("")],
			 [sg.Text("Press Next to Start Stage 5: Data Export")],
			 [sg.Button('Next', bind_return_key=True), sg.Button('Cancel')]]
	window = sg.Window("Deck Cluster Tool", layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Cancel': 
		# if user closes window or clicks cancel
			window.close()
			break
		if event == "Next":
			break
	window.close()

	layout = [[sg.Text("Outputting Results",key="-MOTION-")],
			[sg.Text("Outputting Results: May take some Time", key="-UPDATE-")]]
	window = sg.Window("Deck Cluster Tool", layout)
	window.read(timeout=0.01)

	#CSV Write of Archetypes
	outputList = []
	outputDeckDict = {}

	#remake deck dictionary for output
	for class_ in CLASSES:
		aCC = superCluster.getClassClusterByName(class_)
		for cluster in aCC.clusters:
			for deck in cluster.decks:
				if deck.teamName not in outputDeckDict:
					outputDeckDict[deck.teamName] = []
				outputDeckDict[deck.teamName].append(deepcopy(deck))

	window["-UPDATE-"].update("Outputting Results May take Some Time")
	window.read(timeout=0.01)

	for name in outputDeckDict:
		subList = []
		subList.append(name)
		for deck in outputDeckDict[name]:
			subList.append(deck.classification)
		outputList.append(subList)
	
	df_out = pd.DataFrame(outputList)
	df_out.to_csv("outputs/outputCSV/{}_archetypes.csv".format(os.path.splitext(os.path.basename(filename))[0]), encoding='utf-8', index=False, mode='w+')

	for class_ in CLASSES:
		aCC = superCluster.getClassClusterByName(class_)
		X = []
		for cluster in aCC.clusters:
			X.append(cluster.name)
		X = np.unique(X)

	countDict = {}
	classTotals = []
	for class_ in CLASSES:
		aCC = superCluster.getClassClusterByName(class_)
		x = 0
		for cluster in aCC.clusters:
			name = "{} {}".format(cluster.name, class_.lower())
			if name not in countDict:
				countDict[name] = 0
			count = cluster.getCount()
			countDict[name]+= count
			x+= count
		classTotals.append(x)

	with open("outputs/outputCSV/{}_counts.csv".format(os.path.splitext(os.path.basename(filename))[0]), "w+", encoding='utf-8') as f:
		for class_, i in zip(CLASSES, classTotals):
			f.write("{},{}\n".format(class_,i))

		f.write("\n\n")

		for deck in countDict:
			f.write("{},{}\n".format(deck, countDict[deck]))


	#Make Json of SuperCluster

	#window["-UPDATE-"].update("Outputting JSON")
	#window.Refresh()
	#with open('outputs/saved_superClusters/{}_cluster.json'.format(os.path.splitext(os.path.basename(filename))[0]), 'w+') as outfile:
	#	json.dump(superCluster.jsonify(), outfile)

	window["-UPDATE-"].update("Outputting Results May take Some Times")
	window.read(timeout=0.01)
	#update Labels to new names
	for class_ in CLASSES:
		df = pd.read_csv("outputs/labels/NEW_labels/{}_labels.csv".format(class_))
		aCC = superCluster.getClassClusterByName(class_)
		classifies = []
		for cluster in aCC.clusters:
			for deck in cluster.decks:
				classifies.append(deck.classification)
		del df['cluster']
		df['cluster']= classifies

		df = df.sort_values("cluster")
		df.to_csv("outputs/labels/NEW_labels/{}_labels.csv".format(class_), mode="w+", encoding='utf-8', index=False)

	j = superCluster.chartifyData()
	window.close()
	#end to CLUSTER





# Main process
if __name__== "__main__":
	#add the layout start
	

	#TensorFlow Variable that needs to be done
	#os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
	#Do we Cluster or Do we Classify?
	# True = Cluster, False = Classify
	ClusterOrClassify = True
	layout= [
			[sg.Text("Welcome to Deck Clusterer")],
			[sg.Text("Please Select an Option")],
			[sg.Text("")],
			[sg.Text("Classify Decks using previously clustered labels")], 
			[sg.Button('Just Classify')],
			[sg.Text("")],
			[sg.Text("Cluster Data and then Classify Decks")], 
			[sg.Button('Cluster and Classify')],
			[sg.Text("")],
			[sg.Button('Cancel')]
			]
	window = sg.Window("Deck Cluster Tool", layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Cancel': 
		# if user closes window or clicks cancel
			window.close()
			quit()
			break
		if event == 'Just Classify':
			ClusterOrClassify= False
			break
		if event == 'Cluster and Classify':
			ClusterOrClassify=True
			break
	window.close()
	if ClusterOrClassify:
		toCluster()
	else:
		toClassify()

	layout=[ [sg.Text("Program Complete")],
		[sg.Text("")],
		[sg.Text("Press Finish")],
		[sg.Button('Finish', bind_return_key=True)]]
	window = sg.Window("Deck Cluster Tool", layout)
	while True:
		event, values = window.read()
		if event == sg.WIN_CLOSED or event == 'Finish': 
		# if user closes window or clicks cancel
			window.close()
			break


