

import chimera, os.path
import SimpleSession
from chimera.baseDialog import ModelessDialog
from chimera import tkgui, triggerSet
import Tkinter, Pmw, Tix, Rotamers
import tables
import yaml
from collections import OrderedDict

ui = None
def showUI(callback=None):
	global ui
	if not ui:
		ui = GaudiView()
	ui.enter()
	if callback:
		ui.addCallback(callback)

Filters = [
	("GAUDI results", ["*.gaudi"]),
	("GOLD results", ["*.conf"])
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
	DBL_CLICK = "GaudiViewDoubleClick"
	EXIT = "GaudiViewExited"

	def __init__(self, path, format, *args, **kw):
		self.path = path
		self.basedir, self.file = os.path.split(path)
		self.format = format

		# Triggers
		self.triggers = triggerSet.TriggerSet()
		self.triggers.addTrigger(self.SELECTION_CHANGED)
		self.triggers.addHandler(self.SELECTION_CHANGED, self._sel_changed, None)
		self.triggers.addTrigger(self.DBL_CLICK)

		# DATA init
		self.input, self.data = None, None
		if self.format == 'GAUDI results':
			self.parse_gaudi()
			self.triggers.addHandler(self.DBL_CLICK, self._update_protein_gaudi, None)
		elif self.format == 'GOLD results':
			self.parse_gold()
			self.triggers.addHandler(self.DBL_CLICK, self._update_protein_gold, None)
		else:
			raise UserError("Unknown format {}".format(self.format))

		# Open protein
		try:
			self.protein = chimera.openModels.open(self.proteinpath)
		except:
			self.protein = None

		self.molecules = {}
		self.displayed_molecules = []
		self.selected_molecules = []
		
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

	## PARSERS
	def open_molecule_path(self, *paths):
		for p in paths:
			try:
				self.show_molecules(*self.molecules[p])
			except KeyError:
				self.molecules[p] = chimera.openModels.open(p, shareXform=True)

	def parse_gaudi(self):
		with open(self.path) as f:
			self.input = yaml.load(f)
		self.headers = self.input['GAUDI.results'][0].split()
		parsed = OrderedDict()
		for j, row in enumerate(self.input['GAUDI.results'][1:]):
			parsed[j] = OrderedDict((k,v) for (k,v) in zip(self.headers, row.split()))
		self.data = parsed
		try:
			self.proteinpath = self.input['GAUDI.protein']
		except KeyError:
			self.proteinpath = None

	def parse_gold(self):
		import glob, itertools
		ligand_basepaths = []
		basedirs = []
		self.proteinpath = None
		with open(self.path) as f:
			for line in f.readlines():
				if line.startswith('ligand_data_file'):
					ligand_basepaths.append(line.split()[1][:-5])
				elif line.startswith('directory'):
					basedirs.append(line.split('=')[-1].strip())
				elif line.startswith('protein_datafile'):
					proteinpath = line.split('=')[-1].strip()
					self.proteinpath = os.path.join(self.basedir, proteinpath)
		parsed = OrderedDict()
		i = 0
		for base, ligand in itertools.product(basedirs, ligand_basepaths):
			path = os.path.normpath(os.path.join(self.basedir, base, '*_'+ligand+'_*_*.mol2'))
			solutions = glob.glob(path)
			for mol2 in solutions:
				with open(mol2) as f:
					lines = f.read().splitlines()
					j = lines.index('> <Gold.Score>')
					self.headers = ['Filename'] + lines[j+1].strip().split()
					data = [mol2] + lines[j+2].split()
					parsed[i] = OrderedDict(OrderedDict((k,v) for (k,v) in 
								zip(self.headers, data)))
					i += 1
		print parsed
		self.data = parsed
		
	# HANDLERS
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

	# PROTEIN UPDATERS
	def _update_protein_gaudi(self, trigger, data, r):
		if not self.protein:
			return
		molpath =  self.table.model.data[self.table.model.getRecName(r)]['Filename']
		molecule = self.molecules[os.path.join(self.basedir,molpath)][0]
		mol2data = molecule.mol2data
		try: 
			start = mol2data.index('GAUDI.rotamers')
			end = mol2data.index('/GAUDI.rotamers')
		except ValueError:
			print "Sorry, no rotamer info available in mol2"
		else:
			rotamers = mol2data[start+1:end]
			chimera.runCommand('~show ' + ' '.join(['#{}'.format(m.id) for m in self.protein]))
			for line in rotamers:
				line.strip()
				if line.startswith('#'):
					continue
				self._update_rotamer_gaudi(*line.split())
	
	def _update_rotamer_gaudi(self, pos, lib, restype, *chis):
		lib_dict = {'DYN': 'Dynameomics', 'DUN': 'Dunbrack'}
		res = chimera.specifier.evalSpec(':'+pos).residues()[0]
		all_rotamers = Rotamers.getRotamers(res, resType=restype, lib=lib_dict[lib])[1]
		
		try:
			rotamer = next(r for r in all_rotamers if 
				[round(n,4) for n in r.chis] == [round(float(n),4) for n in chis])
		except StopIteration:
			print "No rotamer found for {}{} with chi angles {}".format(
											pos,restype,','.join(chis))
		else:
			Rotamers.useRotamer(res, [rotamer])
			for a in res.atoms: 
				a.display = 1

	def _update_protein_gold(self, trigger, data, r):
		if not self.protein:
			return
		molpath =  self.table.model.data[self.table.model.getRecName(r)]['Filename']
		molecule = self.molecules[os.path.join(self.basedir,molpath)][0]
		mol2data = molecule.mol2data
		try: 
			start = mol2data.index('> <Gold.Protein.RotatedAtoms>')
		except ValueError:
			print "Sorry, no rotamer info available in mol2"
		else:
			rotamers = mol2data[start+1:]
			chimera.runCommand('~show ' + ' '.join(['#{}'.format(m.id) for m in self.protein]))
			modified_residues = set()
			for line in rotamers:
				if line.startswith('> '):
					break
				fields = line.strip().split()
				atom = self._update_rotamer_gold(fields[0:3], fields[18])
				if atom:
					modified_residues.add(atom.residue)

			for res in modified_residues:
				for a in res.atoms:
					a.display = 1

	def _update_rotamer_gold(self, xyz, atomnum):
		try:
			atom = next(a for prot in self.protein for a in prot.atoms 
					if a.serialNumber==int(atomnum))
		except StopIteration:
			pass
		else:
			atom.setCoord(chimera.Point(*map(float, xyz)))
			return atom