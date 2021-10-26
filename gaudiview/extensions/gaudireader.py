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

# Python
from __future__ import print_function
from collections import OrderedDict
import zipfile
import tempfile
import os
import Tkinter
# Chimera
import chimera
import Rotamers
# External dependencies
import yaml
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBaseModel, GaudiViewBaseController
from gaudiview.extensions import dsx


def load(*args, **kwargs):
    return GaudiController(model=GaudiModel, *args, **kwargs)


class GaudiModel(GaudiViewBaseModel):

    """
    Parses GAUDI output files and processes resulting Zip files.

    .. todo::

        Process metadata files (rotamers, h bonds, clashes).

        Cache the protein file if possible.

    """

    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.basedir = os.path.dirname(path)
        self.data, self.table_data, self.headers = self.parse()
        self.metadata = {}
        self.molecules = {}
        self.tempdir = tempfile.mkdtemp('gaudiview')
        try:
            self.index = max(a for (a, b) in chimera.openModels.listIds())
        except ValueError:
            self.index = -1

    def parse(self):
        """
        Since the output files are already YAML-formatted, we
        only need to load them with PyYaml. However, tkintertable
        requests a specific hierarchy of the data, so we provide that
        too.
        """
        with open(self.path) as f:
            data = yaml.load(f)
        headers = ['Filename'] + data['GAUDI.objectives']
        table_data = OrderedDict()
        for filename, score in data['GAUDI.results'].iteritems():
            table_data[os.path.join(self.basedir, filename)] = \
                OrderedDict((k, v)
                            for (k, v) in zip(headers, [filename] + score))

        return data, table_data, headers

    def parse_zip(self, path):
        """
        GAUDI zips its results files. We extract them on the fly to temp
        directories and feed those to the corresponding parsers (Chimera
        and YAML, as of now).
        """
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipfile:
            print("{} is not a valid GAUDI result".format(path))
        else:
            self.index += 1
            tmp = os.path.join(
                self.tempdir, os.path.splitext(os.path.basename(path))[0])
            try:
                os.mkdir(tmp)
            except OSError:  # Assume it exists
                pass
            z.extractall(tmp)
            mol2 = []
            meta = z.namelist()
            subid = 0
            for name in os.listdir(tmp):
                absname = os.path.join(tmp, name)
                if name.endswith(".mol2") or name.endswith(".pdb"):
                    mol2.extend(
                        m for m in chimera.openModels.open(absname, baseId=self.index,
                                                           subid=subid,
                                                           shareXform=True,
                                                           temporary=True))
                    subid += 1
                elif name.endswith(".yaml"):
                    meta.append(yaml.load(absname))
            z.close()
            return sorted(mol2, key=lambda m: m.numAtoms), meta

    def details(self, key=None):
        if key:
            data = "\n".join(self.metadata[key])
        else:
            try:
                data = self.data['Comments']
            except KeyError:
                data = ''

        return data

    def _extract_file_from_zip_if_contains(self, path, query):
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipfile:
            print("{} is not a valid GAUDI result".format(path))
        else:
            tmp = os.path.join(self.tempdir,
                               os.path.splitext(os.path.basename(path))[0])
            try:
                os.mkdir(tmp)
            except OSError:  # Assume it exists
                pass

            try:
                match = next(name for name in z.namelist() if query in name)
            except StopIteration:
                raise ValueError('{} does not contain any '
                                 'file with {} in its filename'.format(path, query))
            else:
                return z.extract(match, path=tmp)
            finally:
                z.close()


class GaudiController(GaudiViewBaseController):

    def __init__(self, *args, **kwargs):
        GaudiViewBaseController.__init__(self, *args, **kwargs)
        self.basedir = self.model.basedir
        self.HAS_MORE_GUI = True
        self._gaudi_obj_dialog = None

    def display(self, *keys):
        """
        Display molecules if already opened, else, open up
        the Zip container and get the molecules and metadata,
        saving those for later use.

        Also, update the selection box at the end of the loop.
        """
        for k in keys:
            try:
                self.show(*self.model.molecules[k])
            except KeyError:
                mol2, meta = self.model.parse_zip(
                    os.path.join(self.basedir, k))
                self.molecules[k] = mol2
                self.metadata[k] = meta
            finally:
                self.displayed.extend(self.molecules[k])
        else:
            active = self.gui.selection_listbox.curselection()
            self.gui.selection_listbox.delete(0, 'end')
            try:
                for m in sorted(self.molecules[k], key=lambda m: m.openedAs[0]):
                    self.gui.selection_listbox.insert(
                        'end', os.path.basename(m.openedAs[0]))
                for i in active:
                    self.gui.selection_listbox.selection_set(i)
            except UnboundLocalError:
                pass
            else:
                return self.molecules[keys[-1]]

    def process(self, key, **kwargs):
        """
        Display metadata for each solution.

        .. todo::

            Parse metadata files and display their info: H bonds,
            clashes, distances... and every objective.
        """
        pass

    def get_table_dict(self):
        return self.model.table_data

    def extend_gui(self):
        from gaudiview.extensions.gaudiobj import HAS_GAUDI
        if not HAS_GAUDI:
            return
        self.gui.add_column_btn = Tkinter.Button(
            self.gui.cliframe, text="Rescore",command=self._add_column)
        self.gui.add_column_btn.grid(row=2, column=1, sticky='sew')
        self.gui.cliframe.pack(fill='x')

    @staticmethod
    def _update_rotamers(pos, lib, restype, *chis):
        """ Since the individuals are expressed before writing them down,
        theoretically each protein already carries the applied rotamers.
        This won't be needed?
        """
        lib_dict = {'DYN': 'Dynameomics', 'DUN': 'Dunbrack'}
        res = chimera.specifier.evalSpec(':' + pos).residues()[0]
        all_rotamers = Rotamers.getRotamers(
            res, resType=restype, lib=lib_dict[lib])[1]

        try:
            rotamer = next(r for r in all_rotamers if
                           [round(n, 4) for n in r.chis] ==
                           [round(float(n), 4) for n in chis])
        except StopIteration:
            print("No rotamer found for {}{} "
                  "with chi angles {}".format(pos, restype, ','.join(chis)))
        else:
            Rotamers.useRotamer(res, [rotamer])
            for a in res.atoms:
                a.display = 1

    def _add_column(self):
        from gaudiview.extensions.gaudiobj import GaudiObjectiveDialog
        keys = self.selected or self.gui.table.model.data
        if len(keys) > 50:
            raise chimera.UserError('Too many solutions requested! Max 50.')
        self._gaudi_obj_dialog = GaudiObjectiveDialog(callback=self._add_column_cb)
        self._gaudi_obj_dialog.enter()

    def _add_column_cb(self):
        if self._gaudi_obj_dialog is None:
            return
        if not self._gaudi_obj_dialog._returned_OK:
            return
        if len(self.selected) > 1:
            data = {k: self.gui.table.model.data[k] for k in self.selected}
        else:
            data = self.gui.table.model.data
        from gaudiview.extensions.gaudiobj import GaudiObjectivePlugin
        objective = self._gaudi_obj_dialog.objective
        objective_kw = self._gaudi_obj_dialog.objective_kwargs
        objname = objective.__name__
        if objname not in self.gui.table.model.columnlabels:
            self.gui.table.addColumn(objname)
            self.gui.table.tablecolheader.reversedcols[objname] = 0
        total = len(data)
        for i, (k, d) in enumerate(data.iteritems(), 1):
            mols = sorted(self.display(k), key=lambda m: len(m.atoms))
            d[objname] = GaudiObjectivePlugin().do(objective=objective,
                proteinpath=mols[-1].openedAs[0],
                ligandpath=mols[0].openedAs[0], obj_kwargs=objective_kw)
            self.gui.status('Rescored {} out of {}'.format(i, total))
        self.gui.table.redrawTable()
