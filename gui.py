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
        self.triggers.addTrigger(self.DBL_CLICK)
        self.triggers.addHandler(
            self.SELECTION_CHANGED, self._sel_changed, None)
        self.uiMaster().bind("<Configure>", self.on_resize)
        self.uiMaster().bind("<Return>", self.cli_callback)

        # Open protein, if needed
        if self.parser.proteinpath:
            self.open_molecule_path(self.parser.proteinpath)
            self.protein = self.molecules[self.parser.proteinpath]
            # Add triggers
            self.triggers.addHandler(
                self.DBL_CLICK, self.update_protein, None)

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

        # Per-frame CLI input
        self.cliframe = Tkinter.Frame(parent)
        self.cliframe.pack(fill='x')
        Tkinter.Label(self.cliframe, text="Command input").pack()
        self.clifield = Tkinter.Entry(self.cliframe)
        self.clifield.pack(fill='x')
        self.clibutton = Tkinter.Button(
            self.cliframe, text="Run", width=5, command=self.cli_callback)
        self.clibutton.pack(side='right')
        self.selectionbool = Tkinter.BooleanVar()
        self.selectioncheck = Tkinter.Checkbutton(
            self.cliframe, text="Select in Chimera", variable=self.selectionbool,
            command=self.select_in_chimera)
        self.selectioncheck.pack(side='left')

        if self.parser.metadata:
            # Details of selected solution
            self.details_frame = Tkinter.Frame(parent)
            self.details_frame.pack(fill='x')
            Tkinter.Label(self.cliframe, text="Details").pack()
            self.details_field = Tkinter.Text(
                self.details_frame, state=Tkinter.DISABLED, font=(
                    'Monospace', 10),
                height=8, wrap=Tkinter.NONE)
            self.details_field.pack(side='left', fill='x')
            self.details_scroll = Tkinter.Scrollbar(self.details_frame)
            self.details_scroll.pack(side='right', fill='y')
            self.details_scroll.config(command=self.details_field.yview)
            self.details_field.config(yscrollcommand=self.details_scroll.set)

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
            except IndexError:  # click out of boundaries
                pass
            else:
                self.selected_molecules.append(
                    os.path.normpath(os.path.join(self.commonpath, molpath)))

    def update_details_field(self):
        self.details_field.config(state=Tkinter.NORMAL)
        self.details_field.delete(1.0, Tkinter.END)
        for m in self.selected_molecules:
            try:
                data = self.parser.metadata[m]
            except KeyError:
                data = "No metadata available for this file"
            else:
                self.details_field.insert(Tkinter.END, m + "\n")
                self.details_field.insert(Tkinter.END, data + "\n\n")

        self.details_field.config(state=Tkinter.DISABLED)

    def hide_molecules(self, *mols):
        for m in mols:
            m.display = 0

    def show_molecules(self, *mols):
        for m in mols:
            m.display = 1

    def _sel_changed(self, trigger, data, row):
        self.update_selected_molecules()
        self.update_displayed_molecules()
        if self.parser.metadata:
            self.update_details_field()
        if self.selectionbool.get():
            self.select_in_chimera()
        self.cli_callback()

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

    def cli_callback(self, *args, **kwargs):
        command = self.clifield.get()
        if command:
            chimera.runCommand(command)

    def select_in_chimera(self):
        chimera.selection.clearCurrent()
        for m in self.selected_molecules:
            chimera.selection.addCurrent(self.molecules[m])
