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
from __future__ import division, print_function
from collections import OrderedDict
import glob
import itertools
import os
import Tkinter
# Chimera
import chimera
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBaseModel, GaudiViewBaseController
from gaudiview.extensions import dsx
from gaudiview.gui import info, error


def load(*args, **kwargs):
    return GoldController(model=GoldModel, *args, **kwargs)


class GoldModel(GaudiViewBaseModel):

    """
    Parses and processes GOLD `*.conf` input files to
    display all the mol2 output files.

    .. todo::

        Display covalent bonds

        More user-friendly metadata

    """

    def __init__(self, path, *args, **kwargs):
        self.path = path
        self.basedir, self.file = os.path.split(path)
        self.molecules = {}
        self.data = None
        self.metadata = None
        self.commonpath = None
        self.proteinpath = None
        self.rotamers = None
        # parse() sets all this 'None' names
        self.parse()
        self.protein = None
        if self.proteinpath:
            self.protein = chimera.openModels.open(self.proteinpath, shareXform=True, temporary=True)[0]
            for pos in self.rotamers:
                try:
                    residue = next(r for r in self.protein.residues if r.id.position == pos)
                except StopIteration:
                    continue
                else:
                    self.rotamers[pos] = [(a.serialNumber, a.coord().data()) for a in residue.atoms]

    def parse(self):
        """
        Opens a `gold.conf` input file and locates key parameters.

        :ligand_data_file:  Location of input ligand for GOLD.
                            We get the input name from here.

        :directory: Location of output files

        :protein_datafile: Location of the main protein file, usually
                            next to the `gold.conf` file.

        :rotamer_lib:   Indicates the essay contains rotamers. Flag that
                        and retrieve involved residues.

        With those parameters, we can retrieve all the solutions from the
        experiment, since they are mol2 files tagged with `ligand_data_file`.

        However, some essays contain multiple instances of these parameters,
        so we must exhaust all the options with itertools.product.

        We also get rid of ranked symlinks and save the comment section from
        each mol2.
        """
        ligand_basepaths = []
        basedirs = []
        proteinpath = None
        rotamers = {}
        with open(self.path) as f:
            for line in f:
                if line.startswith('ligand_data_file'):
                    ligand, ext = os.path.splitext(' '.join(line.split()[1:-1]))
                    ligand_basepaths.append(ligand)
                elif line.startswith('directory'):
                    basedirs.append(line.split('=')[-1].strip())
                elif line.startswith('protein_datafile'):
                    proteinpath = line.split('=')[-1].strip()
                    proteinpath = os.path.join(self.basedir, proteinpath)
                elif line.startswith('rotamer_lib'):
                    residue = next(f).split()[-1]
                    resname, respos = residue[:3], residue[3:]
                    try:
                        respos = int(respos)
                    except ValueError:
                        continue
                    rotamers[respos] = None

        parsed = OrderedDict()
        parsed_filenames = set()
        metadata = {}
        for base, ligand in itertools.product(basedirs, ligand_basepaths):
            path = os.path.normpath(os.path.join(self.basedir, base,
                                                 '*_' + os.path.basename(ligand) + '_*_*.mol2'))
            solutions = glob.glob(path)
            if not solutions:
                raise chimera.UserError("Solution set for {} was not found. "
                                        "Check paths in your gold.conf".format(ligand))
            for mol2 in solutions:
                mol2 = os.path.realpath(mol2)  # discard symlinks
                if mol2 in parsed_filenames:
                    continue
                with open(mol2) as f:
                    lines = f.read().splitlines()
                    j = lines.index('> <Gold.Score>')
                    self.headers = ['Filename'] + lines[j + 1].strip().split()
                    data = [mol2] + map(float, lines[j + 2].split())
                    # This the hierarchy requested by tkintertable
                    # Each entry must be tagged by its header, such as:
                    # {row_id(abspath): {column: value, column2: value, ...}}
                    parsed[mol2] = OrderedDict(
                        OrderedDict((k, v) for (k, v) in zip(self.headers, data)))
                    parsed_filenames.add(mol2)
                    # Since the file is open, why not get metadata now?
                    k = lines.index('@<TRIPOS>COMMENT')
                    metadata[mol2] = lines[k + 1:]

        commonpath = common_path_of_filenames(parsed_filenames)
        for v in parsed.values():
            # Get rid of the common path in absolute name
            # This leaves a short unique name, adequate for GUI
            v['Filename'] = os.path.relpath(v['Filename'], commonpath)

        self.data = parsed
        self.metadata = metadata
        self.commonpath = commonpath
        self.proteinpath = proteinpath
        self.rotamers = rotamers

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
        self.HAS_SELECTION = False  # disable selection box in GUI
        self.HAS_MORE_GUI = True

    def close_all(self):
        chimera.openModels.close([m_ for m in self.model.molecules.values()
                                  for m_ in m] + [self.model.protein])

    def display(self, *keys):
        for k in keys:
            try:
                self.show(*self.molecules[k])
            except KeyError:
                path = os.path.join(self.model.commonpath, k)
                self.molecules[k] = chimera.openModels.open(path, shareXform=True, temporary=True)
            finally:
                self.displayed.extend(self.molecules[k])

        if keys:
            return self.molecules[keys[-1]]

    def process(self, *keys, **kwargs):
        """
        As of now, we only process rotamer info. We do so by parsing
        the annotated coordinates in section `Gold.Protein.RotatedAtoms`
        and applying the transformation in a per-atom basis. Pretty rough,
        but fast!
        """
        if not keys:
            keys = self.model.data
        self.display(*keys)
        start, rotamers_block_size = 0, 0
        modified_residues = set()
        for key in keys:
            ligand = self.molecules[key]
            mol2data = ligand[0].mol2data
            if self.model.rotamers:
                try:
                    start = mol2data.index('> <Gold.Protein.RotatedAtoms>')
                except ValueError:
                    self.gui.error("Sorry, no rotamer info available in mol2.")
                    for (pos, (atomnum, coords)) in self.model.rotamers.iteritems():
                        self.update_rotamers(self.model.protein, coords, atomnum)
                else:
                    rotamers = mol2data[start + 1:]
                    for i, line in enumerate(rotamers):
                        if line.startswith('> '):
                            rotamers_block_size = i
                            break
                        fields = line.strip().split()
                        atom = self.update_rotamers(
                            self.model.protein, fields[0:3], fields[18])
                        if atom:
                            modified_residues.add(atom.residue)
            # Continue
            in_hbonds = False
            for line in mol2data[start+rotamers_block_size:]:
                line = line.strip()
                if line.endswith('.Hbonds>'):
                    print("HBonds in {}:".format(key))
                    print(" Donor -- Acceptor: score, distance")
                    in_hbonds = True
                elif line.startswith('> '):
                    in_hbonds = False
                elif in_hbonds and line and not line.startswith('donor'):
                    fields = line.split()
                    donor_mol = self.model.protein if fields[0].startswith('P') else ligand[0]
                    donor_serial = int(fields[3])
                    acceptor_mol = self.model.protein if fields[4].startswith('P') else ligand[0]
                    acceptor_serial = int(fields[5])
                    value = float(fields[6])
                    pb = self.draw_hbond(donor_mol, donor_serial, 
                                         acceptor_mol, acceptor_serial, value,
                                         distance=True)
                    if pb:
                        print(pb.atoms[0], '--', pb.atoms[1], ':', pb.label)
                        for a in pb.atoms:
                            modified_residues.add(a.residue)

                    
        # hide already displayed residues
        for res in self.model.protein.residues:
            res.label = ''
            for a in res.atoms:
                a.display = 0
        # display modified residues
        for res in modified_residues:
            if res.molecule is self.model.protein:
                res.label = '{}{}'.format(res.type, res.id.position)
            for a in res.atoms:
                a.display = 1

        # self._get_dsx_score(keys=keys)

    def get_table_dict(self):
        return self.model.data

    def extend_gui(self):
        self.gui.dsx_bool = Tkinter.BooleanVar()
        self.gui.dsx_check = Tkinter.Checkbutton(self.gui.cliframe, text="Get DSX Score",
                                                 variable=self.gui.dsx_bool, 
                                                 command=self.process)
        self.gui.dsx_check.grid(row=2, column=0, sticky='e')

        self.gui.cliframe.pack(fill='x')

    def _get_dsx_score(self, keys=None):
        if 'DSX_score' not in self.gui.table.model.columnlabels:
            self.gui.table.addColumn('DSX_score')
            self.gui.table.tablecolheader.reversedcols['DSX_score'] = 0
        if keys is None:
            data = self.gui.table.model.data.iteritems()
        else:
            data = ((k, self.gui.table.model.data[k]) for k in keys)
        for k, d in data:
            if 'DSX_score' not in d:
                mol, = self.display(k)
                dsx_score = dsx.DSXPlugin()
                score = dsx_score.do(self.model.proteinpath, mol.openedAs[0])
                d['DSX_score'] = score
                self.gui.table.redrawTable()

    @staticmethod
    def update_rotamers(protein, xyz, atomnum):
        """
        Apply new coordinates `xyz` to selected atom with
        serialNumber `atomnum` in `protein`.
        """
        try:
            atom = next(a for a in protein.atoms
                        if a.serialNumber == int(atomnum))
        except StopIteration:
            pass
        else:
            atom.setCoord(chimera.Point(*map(float, xyz)))
            return atom

    @staticmethod
    def draw_hbond(donor_mol, donor_serial, acceptor_mol, acceptor_serial,
                   label=None, distance=True):
        try:
            donor = next(a for a in donor_mol.atoms 
                         if a.serialNumber == donor_serial)
            acceptor = next(a for a in acceptor_mol.atoms 
                            if a.serialNumber == acceptor_serial)
        except StopIteration:
            return
        else:
            if distance and label:
                distance = donor.xformCoord().distance(acceptor.xformCoord())
                distance = round(distance, 3)
                label = '{}, {}'.format(label, distance)
            return pseudobond(donor, acceptor, 'HBonds', (0, 0.5, 1.0, 1.0), label)


def common_path(directories):
    norm_paths = [os.path.abspath(p) + os.path.sep for p in directories]
    return os.path.dirname(os.path.commonprefix(norm_paths))


def common_path_of_filenames(filenames):
    return common_path([os.path.dirname(f) for f in filenames])

def pseudobond(atom1, atom2, group, color=None, label=None):
    pbg = chimera.misc.getPseudoBondGroup(group)
    pb = pbg.newPseudoBond(atom1, atom2)
    if color is not None:
        pb.color = chimera.MaterialColor(*color)
    if label is not None:
        pb.label = str(label)
    return pb
