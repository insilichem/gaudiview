

import chimera, os.path
import SimpleSession
from chimera.baseDialog import ModelessDialog
from chimera import tkgui, triggerSet
import Tkinter, Pmw, Tix
import tables

ui = None
def showUI(callback=None):
	global ui
	if not ui:
		ui = GaudiView()
	ui.enter()
	if callback:
		ui.addCallback(callback)

Filters = [
	("Gaudi results", ["*.gaudi"]),
	("Gaudi Mol2", ["*.gaudi.mol2"])
]

def browse():
	from OpenSave import OpenModeless
	OpenModeless(command=_browse, title="Open Gaudi results file",
		filters=Filters, dialogKw={'oneshot': 1}, historyID="GaudiView")

def _browse(okayed, dialog):
	if not okayed:
		return
	for path, type in dialog.getPathsAndTypes():
		GaudiViewDialog(path, type)
################################		
class GaudiViewDialog(ModelessDialog):
	buttons = ("OK", "Close")
	default = None
	help = "https://bitbucket.org/jrgp/gaudiview"
	SELECTION_CHANGED = "GaudiViewSelectionChanged"
	EXIT = "GaudiViewExited"

	def __init__(self, path, format, *args, **kw):
		self.path = path
		self.basedir, self.file = os.path.split(path)
		self.format = format

		# DATA init
		self.data = self.parseGaudi(self.path)
		self.molecules = self.parseMolPaths(self.data)
		self.selected_molecules = []

		# Triggers
		self.triggers = triggerSet.TriggerSet()
		self.triggers.addTrigger(self.SELECTION_CHANGED)
		self.triggers.addHandler(self.SELECTION_CHANGED, self._sel_changed, None)

		# GUI init
		self.title = 'GaudiView - {}'.format(path)
		ModelessDialog.__init__(self)
		chimera.extension.manager.registerInstance(self)

	def fillInUI(self, parent):
		# Create main window
		self.tframe = Tkinter.Frame(parent)
		self.tframe.pack()

		# Fill data in and create table
		self.model = tables.TableModel()
		self.model.importDict(self.data)
		self.table = tables.Table(self.tframe, self.model, editable=False, 
								gaudiparent=self)
		self.table.createTableFrame()
		self.table.createFilteringBar(parent)
		self.table.autoResizeColumns()
		self.table.redrawTable()

	def Apply(self):
		chimera.openModels.close([ m_ for p in self.molecules 
			for m_ in self.molecules[p] if p not in self.selected_molecules ])

	def OK(self):
		self.Apply()
		self.destroy()

	def Close(self):
		chimera.openModels.close([mol for mol in chimera.openModels.list() 
			if mol in [ m_ for m in self.molecules.values() for m_ in m ]])
		self.destroy()

	## Parsing and click events
	def parseGaudi(self, path):
		from collections import OrderedDict
		f = open(path, 'r')
		readlines = f.read().splitlines()
		try:
			self.proteinpath = readlines[readlines.index('>>GAUDI.protein')+1]
		except:
			self.proteinpath = ''
		i = readlines.index('>>GAUDI.results')
		self.headers = readlines[i+1].split()
		parsed = {}
		for j, row in enumerate(readlines[i+2:]):
			parsed[j] = OrderedDict((k,v) for (k,v) in zip(self.headers, row.split()))
		return parsed

	def parseMolPaths(self, data):
		paths = [ os.path.join(self.basedir,r['Filename']) for r in data.values() ]
		mols = {}
		for p in paths:
			mols[p] = chimera.openModels.open(p, type='Mol2', shareXform=True)
		# chimera.openModels.remove([ mols[p][0] for p in paths[1:] ])
		[self.hideMolecule(mols[p][0]) for p in paths[1:] ]
		try:
			self.protein = chimera.openModels.open(self.proteinpath)[0]
		except:
			self.protein = None
		return mols

	def updateDisplayedMolecules(self):
		# chimera.openModels.remove([ m for m in 
		# 				chimera.openModels.list(modelTypes=[chimera.Molecule])
		# 				if m != self.protein ])
		[ self.hideMolecule(m) for m in chimera.openModels.list(modelTypes=[chimera.Molecule])
						if m != self.protein ]
		if self.selected_molecules:
			# chimera.openModels.add([m_ for m in self.selected_molecules 
			# 			for m_ in self.molecules[m]], shareXform=True)
			[self.showMolecule(m_) for m in self.selected_molecules 
						for m_ in self.molecules[m]]

	def updateSelectedMolecules(self):
		self.selected_molecules = []
		for row in self.table.multiplerowlist:
			try: 
				molpath = self.table.model.data[self.table.model.getRecName(row)]['Filename']
				self.selected_molecules.append(os.path.join(self.basedir,molpath))
			except IndexError: #click out of boundaries
				pass
	
	def hideMolecule(self, m):
		m.display = 0
	def showMolecule(self, m):
		m.display = 1

	def _sel_changed(self, trigger, data, f):
		self.updateSelectedMolecules()
		self.updateDisplayedMolecules()