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
import glob
import itertools
import os
# Chimera
import chimera
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBaseModel, GaudiViewBaseController


def load(*args, **kwargs):
    return GoldController(model=GoldModel, *args, **kwargs)


class GoldModel(GaudiViewBaseModel):

    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.basedir, self.file = os.path.split(path)
        self.molecules = {}
        self.data, self.metadata, self.commonpath, self.proteinpath = self.parse()
        self.protein = None
        if self.proteinpath:
            self.protein = chimera.openModels.open(
                self.proteinpath, shareXform=True)

    def parse(self):
        ligand_basepaths = []
        basedirs = []
        proteinpath = None
        with open(self.path) as f:
            for line in f.readlines():
                if line.startswith('ligand_data_file'):
                    ligand_basepaths.append(line.split()[1][:-5])
                elif line.startswith('directory'):
                    basedirs.append(line.split('=')[-1].strip())
                elif line.startswith('protein_datafile'):
                    proteinpath = line.split('=')[-1].strip()
                    proteinpath = os.path.join(self.basedir, proteinpath)
        parsed = OrderedDict()
        parsed_filenames = set()
        metadata = {}
        i = 0
        for base, ligand in itertools.product(basedirs, ligand_basepaths):
            path = os.path.normpath(
                os.path.join(self.basedir, base, '*_' + ligand + '_*_*.mol2'))
            solutions = glob.glob(path)
            for mol2 in solutions:
                mol2 = os.path.realpath(mol2)
                if mol2 in parsed_filenames:
                    continue
                with open(mol2) as f:
                    lines = f.read().splitlines()
                    j = lines.index('> <Gold.Score>')
                    self.headers = ['Filename'] + lines[j + 1].strip().split()
                    data = [mol2] + lines[j + 2].split()
                    parsed[i] = OrderedDict(OrderedDict((k, v) for (k, v) in
                                                        zip(self.headers, data)))
                    i += 1
                    parsed_filenames.add(mol2)
                    k = lines.index('@<TRIPOS>COMMENT')
                    metadata[os.path.basename(mol2)] = lines[k + 1:]

        commonpath = common_path_of_filenames(parsed_filenames)
        for v in parsed.values():
            v['Filename'] = os.path.relpath(v['Filename'], commonpath)

        return parsed, metadata, commonpath, proteinpath

    def details(self, key=None):
        if key:
            data = "\n  ".join(self.metadata[key])
        else:
            try:
                data = "\n  ".join(self.data['Comments'])
            except KeyError:
                data = ''
        return data


class GoldController(GaudiViewBaseController):

    def __init__(self, *args, **kwargs):
        GaudiViewBaseController.__init__(self, *args, **kwargs)
        self.HAS_SELECTION = False

    def display(self, *keys):
        for k in keys:
            try:
                self.show(*self.molecules[k])
            except KeyError:
                path = os.path.join(self.model.commonpath, k)
                self.molecules[k] = chimera.openModels.open(
                    path, shareXform=True)
            finally:
                self.displayed.extend(self.molecules[k])

    def process(self, key):
        if not self.model.protein:
            return
        ligand = self.molecules[key]
        mol2data = ligand[0].mol2data
        try:
            start = mol2data.index('> <Gold.Protein.RotatedAtoms>')
        except ValueError:
            print "Sorry, no rotamer info available in mol2"
        else:
            rotamers = mol2data[start + 1:]
            modified_residues = set()
            for line in rotamers:
                if line.startswith('> '):
                    break
                fields = line.strip().split()
                atom = self.update_rotamers(
                    self.model.protein, fields[0:3], fields[18])
                if atom:
                    modified_residues.add(atom.residue)
            for res in modified_residues:
                for a in res.atoms:
                    a.display = 1

    def get_table_dict(self):
        return self.model.data

    @staticmethod
    def update_rotamers(protein, xyz, atomnum):
        try:
            atom = next(a for prot in protein for a in prot.atoms
                        if a.serialNumber == int(atomnum))
        except StopIteration:
            pass
        else:
            atom.setCoord(chimera.Point(*map(float, xyz)))
            return atom


def common_path(directories):
    norm_paths = [os.path.abspath(p) + os.path.sep for p in directories]
    return os.path.dirname(os.path.commonprefix(norm_paths))


def common_path_of_filenames(filenames):
    return common_path([os.path.dirname(f) for f in filenames])
