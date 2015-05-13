#!/usr/bin/python

##############
# GAUDIView: Light interface to explore
# solutions from GAUDIasm and more
# Authors:  Jaime Rodriguez-Guerra Pedregal
#            <jaime.rodriguezguerra@uab.cat>
#           Jean-Didier Marechal
#            <jeandidier.marechal@uab.cat>
# Web: https://bitbucket.org/jrgp/gaudiview
##############

# Python
import os
import Tkinter
import importlib
# Chimera
import chimera
from chimera.baseDialog import ModelessDialog
# External dependencies
import tables

ui = None


def showUI(callback=None):
    global ui
    if not ui:
        ui = GaudiViewDialog()
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
    for path, format in dialog.getPathsAndTypes():
        GaudiViewDialog(path, format)


class GaudiViewDialog(ModelessDialog):
    buttons = ("OK", "Close")
    default = None
    help = "https://bitbucket.org/jrgp/gaudiview"
    SELECTION_CHANGED = "GaudiViewSelectionChanged"
    DBL_CLICK = "GaudiViewDoubleClick"
    EXIT = "GaudiViewExited"
    FORMATS = {
        'GAUDI results': 'gaudiview.gaudi',
        'GOLD results': 'gaudiview.gold'
    }

    def __init__(self, path, format, *args, **kw):
        self.path = path
        self.basedir, self.file = os.path.split(path)
        self.format = format

        module = importlib.import_module(self.FORMATS[format])
        self.parser = module.load(path)
        self.data = self.parser.data
        self.commonpath = self.parser.commonpath

        self.molecules = {}
        self.displayed_molecules = []
        self.selected_molecules = []
        self.protein = None

        # GUI init
        self.title = 'GaudiView - {}'.format(path)
        ModelessDialog.__init__(self)
        chimera.extension.manager.registerInstance(self)

        # Triggers
        self.triggers = chimera.triggerSet.TriggerSet()
        self.triggers.addTrigger(self.SELECTION_CHANGED)
        self.triggers.addHandler(
            self.SELECTION_CHANGED, self._sel_changed, None)
        self.triggers.addTrigger(self.DBL_CLICK)
        self.triggers.addHandler(
            self.DBL_CLICK, self.update_protein, None)
        self.uiMaster().bind("<Configure>", self.on_resize)

        # Open protein, if needed
        if self.parser.proteinpath:
            self.open_molecule_path(self.parser.proteinpath)
            self.protein = self.molecules[self.parser.proteinpath]

    def fillInUI(self, parent):
        # Create main window
        self.tframe = Tkinter.Frame(parent)
        self.tframe.pack(expand=True, fill='both')

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
        chimera.openModels.close([m_ for p in self.molecules
                                  for m_ in self.molecules[p] if p not in self.selected_molecules])

    def OK(self):
        self.Apply()
        self.destroy()

    def Close(self):
        chimera.openModels.close(
            [m_ for m in self.molecules.values() for m_ in m])
        self.destroy()

    # HANDLERS
    def open_molecule_path(self, *paths):
        for p in paths:
            try:
                self.show_molecules(*self.molecules[p])
            except KeyError:
                self.molecules[p] = chimera.openModels.open(
                    p, shareXform=True)

    def update_displayed_molecules(self):
        self.hide_molecules(*self.displayed_molecules)

        self.open_molecule_path(*self.selected_molecules)
        self.displayed_molecules.extend([m for p in self.selected_molecules
                                         for m in self.molecules[p]])

    def update_selected_molecules(self):
        self.selected_molecules = []
        for row in self.table.multiplerowlist:
            try:
                molpath = self.table.model.data[
                    self.table.model.getRecName(row)]['Filename']
                self.selected_molecules.append(
                    os.path.normpath(os.path.join(self.commonpath, molpath)))
            except IndexError:  # click out of boundaries
                pass

    def hide_molecules(self, *mols):
        for m in mols:
            m.display = 0

    def show_molecules(self, *mols):
        for m in mols:
            m.display = 1

    def _sel_changed(self, trigger, data, row):
        self.update_selected_molecules()
        self.update_displayed_molecules()

    def on_resize(self, event):
        self.width = event.width
        self.height = event.height
        self.tframe.pack(expand=True, fill='both')

    def update_protein(self, trigger, data, row):
        molpath = self.table.model.data[
            self.table.model.getRecName(row)]['Filename']
        ligand = self.molecules[
            os.path.normpath(os.path.join(self.commonpath, molpath))]
        self.parser.update_protein(self.protein, ligand)
