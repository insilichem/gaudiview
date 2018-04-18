#!/usr/bin/python

##############
# GAUDIView: Light interface to explore
# solutions from GaudiMM and more
# Authors:  Jaime Rodriguez-Guerra Pedregal
#            <jaime.rodriguezguerra@uab.cat>
#           Jean-Didier Marechal
#            <jeandidier.marechal@uab.cat>
# Web: https://github.com/insilichem/gaudiview
##############

"""
Defines base classes for new extensions. Subclass them and extend them
as needed. They are ABCs, so you will know what to override and what not.

Also, don't forget to extend the dict `FORMATS` to include you new extension.
"""

import abc
import importlib
import chimera
import Midas
import os
from functools import partial
try:
    from subalign import untransformed_rmsd as calculate_rmsd
except (ImportError, chimera.UserError):
    calculate_rmsd = lambda ref, probe: Midas.rmsd(ref.atoms, probe.atoms, log=False)

FORMATS = {
    'GaudiMM results': 'gaudiview.extensions.gaudireader',
    'GOLD results': 'gaudiview.extensions.gold',
    'Mol2 files': 'gaudiview.extensions.mol2'
}


def load_controller(path, format, gui=None):
    """
    Returns an instance of the needed parser for this format.
    """
    return importlib.import_module(FORMATS[format]).load(path=path, gui=gui)


class GaudiViewBaseController(object):

    """
    Base class that provides some built-in methods to the controllers.
    To use it, just inherit from it and override :meth:`display`, :meth:`process`,
    and :meth:`get_table_dict`.

    If you need to override some flags in `__init__`, don't forget to call
    `GaudiViewBaseController.__init__()`.
    """

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
        self.HAS_MORE_GUI = False

    def update_selected(self):
        """
        Rebuild list of selected items, which are represented by
        their filenames, as displayed in the GUI table.
        """
        del self.selected[:]
        for row in self.gui.table.multiplerowlist:
            try:
                molpath = self.gui.table.model.getRecName(row)
            except IndexError:  # click out of boundaries
                pass
            else:
                self.selected.append(molpath)

    # GUI Handlers
    def close_all(self):
        chimera.openModels.close(
            [m_ for m in self.model.molecules.values() for m_ in m])

    def double_click(self, trigger, data, row):
        """
        Handles double click in a row. Redirects to :meth:`self.process`.
        """
        try:
            key = self.gui.table.model.getRecName(row)
        except IndexError:  # click out of boundaries
            pass
        else:
            self.process(key, row=row)

    def extend_gui(self):
        """
        Adds more stuff to the GUI. Overwrite if needed, and set
        ``self.HAS_MORE_GUI`` to True.
        """
        pass

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
    def display(self, *keys, **kwargs):
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
    def process(self, *keys, **kwargs):
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
    @abc.abstractmethod
    def get_table_dict(self):
        pass

    def cluster(self):
        cutoff = float(self.gui.cluster_cutoff.get())
        column = self.gui.cluster_key.get()
        reverse = bool(self.gui.table.tablecolheader.reversedcols[column])

        if 'Cluster' not in self.gui.table.model.columnlabels:
            self.gui.table.addColumn('Cluster')
            self.gui.table.tablecolheader.reversedcols['Cluster'] = 0

        data = self.gui.table.model.data.items()
        data.sort(key=lambda item: item[1][column], reverse=not reverse)

        if self.HAS_SELECTION:
            marked = [self.gui.selection_listbox.get(i)
                      for i in self.gui.selection_listbox.curselection()]
        else:
            marked = None
        solutions = []
        # for key, row in data:
        #     if marked is not None:
        #         mols = [m for m in self.display(key) if m.openedAs[0] in marked]
        #     else:
        #         mols = self.display(key)
        #     if len(mols) == 1:
        #         solutions.append((key, mols[0]))
        #     else:
        #         raise chimera.UserError('Only one molecule must be selected '
        #                                 'for clustering')
        for key, row in data:
            solutions.append((key, self.display(key)[0]))
        seed = solutions.pop() + (None,)
        clusters = [[seed]]
        while solutions:
            seed_key, seed_mol = solutions.pop()
            for cluster in clusters:
                cluster_key, cluster_mol, _ = cluster[0]
                rmsd = calculate_rmsd(cluster_mol, seed_mol)
                if rmsd < cutoff:
                    cluster.append((seed_key, seed_mol, rmsd))
                    break
            else:
                clusters.append([(seed_key, seed_mol, None)])

        print('#\tSize\tRMSD\t{}'.format(column))
        for index, cluster in enumerate(clusters):
            rmsds = []
            column_values = []
            for key, molecule, rmsd in cluster:
                self.gui.table.model.data[key]['Cluster'] = index + 1
                column_values.append(float(self.gui.table.model.data[key][column]))
                if rmsd is not None:
                    rmsds.append(rmsd)
            avg_rmsd = round(sum(rmsds)/len(rmsds), 3) if rmsds else 0.0
            avg_column_values = round(sum(column_values)/len(column_values), 3)
            print('\t'.join(map(str, (index+1, len(cluster), avg_rmsd, avg_column_values))))

        self.gui.table.redrawTable()



class GaudiViewBaseModel(object):

    """
    Base class for new models. The model interfaces with the input file
    and extracts all relevant info: filenames of solutions, scores, metadata
    of interactions...

    Subclass :class:`GaudiViewBaseModel` and define all three methods below.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """
        The base controller requires these attributes to operate, so use them:

        :molecules: A dictionary that allocates already processed molecules, as
                    opened by Chimera. The key is the base filename, whose value
                    is a list of `chimera.Molecule` objects.

        :metadata:  A dictionary that allocates metadata about each processed
                    molecule. It's a parallel dict to `self.molecules`, so the
                    keys are the same. The values should be lists of strings,
                    since they will end up in the details field of the GUI.

        :data:      These holds the parsed input file. If it's not in the
                    format requested by tkintertable, use a second attribute called
                    `table_data` and remember to return it with
                    `controller.get_table_dict()`

        :headers:   A list of strings that will be used to populate the header
                    of the table.
        """
        pass

    @abc.abstractmethod
    def parse(self):
        pass

    @abc.abstractmethod
    def details(self, record=None):
        pass


class GaudiViewBasePlugin(object):

    """
    Base class for new behaviour plugins. These are classes that can be
    invoked in controllers to achieve new functionality.
    """
    pass
