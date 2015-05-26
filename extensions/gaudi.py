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
from collections import OrderedDict
import zipfile
import tempfile
import os
# Chimera
import chimera
import Rotamers
# External dependencies
import yaml
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBaseModel, GaudiViewBaseController


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
            table_data[filename] = OrderedDict((k, v) for (k, v) in
                                               zip(headers, [filename] + score))

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
            print "Not a valid GAUDI result"
        else:
            tmp = os.path.join(
                self.tempdir, os.path.splitext(os.path.basename(path))[0])
            try:
                os.mkdir(tmp)
            except OSError:  # Assume it exists
                pass
            z.extractall(tmp)
            mol2 = []
            meta = z.namelist()
            for name in os.listdir(tmp):
                absname = os.path.join(tmp, name)
                if name.endswith(".mol2"):
                    mol2.extend(
                        m for m in chimera.openModels.open(absname, shareXform=True))
                elif name.endswith(".yaml"):
                    meta.append(yaml.load(absname))
            return mol2, meta
        finally:
            z.close()

    def details(self, key=None):
        if key:
            data = "\n".join(self.metadata[key])
        else:
            try:
                data = self.data['Comments']
            except KeyError:
                data = ''

        return data


class GaudiController(GaudiViewBaseController):

    def __init__(self, *args, **kwargs):
        GaudiViewBaseController.__init__(self, *args, **kwargs)
        self.basedir = self.model.basedir

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
                for m in self.molecules[k]:
                    self.gui.selection_listbox.insert(
                        'end', os.path.basename(m.openedAs[0]))
                for i in active:
                    self.gui.selection_listbox.selection_set(i)
            except UnboundLocalError:
                pass

    def process(self, key):
        """
        Display metadata for each solution.

        .. todo::

            Parse metadata files and display their info: H bonds,
            clashes, distances... and every objective.
        """
        pass
        # if not protein:
        #     return
        # mol2data = ligand[0].mol2data
        # try:
        #     start = mol2data.index('GAUDI.rotamers')
        #     end = mol2data.index('/GAUDI.rotamers')
        # except ValueError:
        #     print "Sorry, no rotamer info available in mol2"
        # else:
        #     rotamers = mol2data[start + 1:end]
        #     for line in rotamers:
        #         line.strip()
        # if line.startswith('#'):
        #             continue
        #         self.update_rotamers(*line.split())

    def get_table_dict(self):
        return self.model.table_data

    @staticmethod
    def update_rotamers(pos, lib, restype, *chis):
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
            print "No rotamer found for {}{} with chi angles {}".format(
                pos, restype, ','.join(chis))
        else:
            Rotamers.useRotamer(res, [rotamer])
            for a in res.atoms:
                a.display = 1
