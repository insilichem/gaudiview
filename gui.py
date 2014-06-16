

import chimera, os.path
import SimpleSession
from chimera.baseDialog import ModelessDialog
from chimera import tkgui, triggerSet
import Tkinter, Pmw, Tix
import tables
import yaml

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
		self.parse()
		self.molecules = {}
		self.displayed_molecules = []
		self.selected_molecules = []

		# Triggers
		self.triggers = triggerSet.TriggerSet()
		self.triggers.addTrigger(self.SELECTION_CHANGED)
		self.triggers.addHandler(self.SELECTION_CHANGED, self._sel_changed, None)
		self.triggers.addTrigger(self.DBL_CLICK)
		self.triggers.addHandler(self.DBL_CLICK, self._update_protein, None)
		
		# GUI init
		self.title = 'GaudiView - {}'.format(path)
		ModelessDialog.__init__(self)
		chimera.extension.manager.registerInstance(self)

		# Open protein
		try:
			self.protein = chimera.openModels.open(self.input['GAUDI.protein'])
		except (KeyError, IOError):
			self.protein = None


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
	def open_molecule_path(self, *paths):
		for p in paths:
			try:
				self.show_molecules(*self.molecules[p])
			except KeyError:
				self.molecules[p] = chimera.openModels.open(p, shareXform=True)

	def parse(self):
		from collections import OrderedDict
		with open(self.path) as f:
			self.input = yaml.load(f)
		self.headers = self.input['GAUDI.results'][0].split()
		parsed = OrderedDict()
		for j, row in enumerate(self.input['GAUDI.results'][1:]):
			parsed[j] = OrderedDict((k,v) for (k,v) in zip(self.headers, row.split()))
		self.data = parsed

	def update_displayed_molecules(self):
		self.hide_molecules(*self.displayed_molecules)

		self.open_molecule_path(*self.selected_molecules)
		self.displayed_molecules.extend([m for p in self.selected_molecules
			for m in self.molecules[p]])

	def update_selected_molecules(self):
		self.selected_molecules = []
		for row in self.table.multiplerowlist:
			try: 
				molpath = self.table.model.data[self.table.model.getRecName(row)]['Filename']
				self.selected_molecules.append(os.path.join(self.basedir,molpath))
			except IndexError: #click out of boundaries
				pass

	def hide_molecules(self, *mols):
		for m in mols:
			m.display = 0
	def show_molecules(self, *mols):
		for m in mols:
			m.display = 1

	def _sel_changed(self, trigger, data, f):
		self.update_selected_molecules()
		self.update_displayed_molecules()

	def _update_protein(self, trigger, data, r):
		path =  self.table.model.data[self.table.model.getRecName(r)]['Filename']
		print path
		# protein_info = self.input['GAUDI.rotamers'][path]
		#
