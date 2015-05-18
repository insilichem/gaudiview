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

import abc
import importlib
import chimera
import Midas
import os

FORMATS = {
    'GAUDI results': 'gaudiview.extensions.gaudi',
    'GOLD results': 'gaudiview.extensions.gold'
}


def load_controller(path, format, gui=None):
    return importlib.import_module(FORMATS[format]).load(path=path, gui=gui)


class GaudiViewBaseController(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, model=None, path=None, gui=None, *args, **kwargs):
        self.path = path
        self.gui = gui
        self.model = model(path)
        self.molecules = self.model.molecules
        self.metadata = self.model.metadata
        self.selected = []
        self.displayed = []
        self.HAS_DETAILS = True
        self.HAS_SELECTION = True

    def update_selected(self):
        """
        Rebuild list of selected items, which are represented by
        their filenames, as displayed in the GUI table.
        """
        del self.selected[:]
        for row in self.gui.table.multiplerowlist:
            try:
                molpath = self.gui.table.model.data[
                    self.gui.table.model.getRecName(row)]['Filename']
            except IndexError:  # click out of boundaries
                pass
            else:
                self.selected.append(molpath)

    # GUI Handlers
    def double_click(self, trigger, data, row):
        """
        Handles double click in a row. Redirects to :meth:`self.process`.
        """
        try:
            key = self.gui.table.model.data[
                self.gui.table.model.getRecName(row)]['Filename']
        except IndexError:  # click out of boundaries
            pass
        else:
            self.process(key)

    def selection_changed(self, trigger, data, row):
        """
        Triggered when user clicks or select new entries.

        1. Update the list of selected items.
        2. Update the displayed elements in Chimera canvas.
        3. Update the details section in GUI.
        4. Update selected items in Chimera GUI (green outline)
        5. Run typed in commands in CLI field.
        """
        self.update_selected()
        self.update_displayed()
        if self.HAS_DETAILS:
            self.update_details_field()
        self.select_in_chimera()
        self.run_command()

    # GUI Actions
    def hide(self, *mols):
        """
        This hides molecules, but don't close them!
        """
        for m in mols:
            m.display = 0

    def show(self, *mols):
        """
        Reverts effects done by :meth:`self.hide`.
        """
        for m in mols:
            m.display = 1

    def run_command(self, *args, **kwargs):
        """
        Get the contents of the CLI field and run them in Chimera.
        """
        command = self.gui.clifield.get()
        try:
            chimera.runCommand(command)
        except Midas.MidasError as e:
            print e
            self.gui.error(e.__str__())

    def select_in_chimera(self, *args, **kwargs):
        """
        Gets active items in selection box and select the
        corresponding molecules in Chimera canvas.
        """
        chimera.selection.clearCurrent()
        if self.gui.selectionbool.get():
            if self.HAS_SELECTION:
                active = [self.gui.selection_listbox.get(i)
                          for i in self.gui.selection_listbox.curselection()]
                for m in self.selected:
                    mols = self.model.molecules[m]
                    for mol in mols:
                        if os.path.basename(mol.openedAs[0]) in active:
                            chimera.selection.addCurrent(mol)
            else:
                for m in self.selected:
                    mols = self.model.molecules[m]
                    chimera.selection.addCurrent(mols)

    def update_details_field(self):
        """
        Gets details from selected entries and
        sends them to the GUI handler, which will update
        the details area.
        """
        text = []
        for sel in self.selected:
            text.append(sel)
            text.append(self.model.details(sel))
            text.append("\n")
        self.gui.update_details_field("\n  ".join(text))

    def update_displayed(self):
        """
        Hides currently shown molecules, clear them from the list
        and display the newly selected items.
        """
        self.hide(*self.displayed)
        del self.displayed[:]
        self.display(*self.selected)
        self.show(*self.displayed)

    @abc.abstractmethod
    def display(self, *keys):
        """
        Given a list of keys (usually, the filenames), this method
        will handle opening the molecule files and bringing them to the
        canvas. It's interesting to use the built-in dictionary
        `self.molecules` to cache already opened files, using some
        `try/except/else` trickery. See `gaudi.py` for more details.

        This method must be defined in each subclass, since each will
        have a different behaviour to handle the input. For example,
        GAUDI output is zipped and can contain multiple molecules. GOLD
        offers a common protein and a number of ligands.
        """
        pass

    @abc.abstractmethod
    def process(self, *keys):
        """
        Given a list of keys (usually, the filenames), this method will
        handle further displaying of info in the GUI. For example, updating
        the protein to show the rotamers, drawing H bond interaction vectors,
        hydrophobic patches, and so on.

        This method must be defined in each subclass, since each will
        have a different behaviour to handle the input. For example,
        GAUDI output is zipped and can contain multiple molecules. GOLD
        offers a common protein and a number of ligands.
        """
        pass

    # Model handlers
    def get_table_dict(self):
        return self.model.table_data


class GaudiViewBaseModel(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def parse(self):
        pass

    @abc.abstractmethod
    def details(self, record=None):
        pass
