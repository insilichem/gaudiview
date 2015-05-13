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
import os
# Chimera
import chimera
import Rotamers
# External dependencies
import yaml


def load(*args, **kwargs):
    return GaudiData(*args, **kwargs)


class GaudiData(object):

    def __init__(self, path):
        self.path = path
        self.basedir, self.file = os.path.split(path)
        self.data = self.parse()
        self.commonpath = self.basedir

    def parse(self):
        with open(self.path) as f:
            self.input = yaml.load(f)
        self.headers = self.input['GAUDI.results'][0].split()
        parsed = OrderedDict()
        for j, row in enumerate(self.input['GAUDI.results'][1:]):
            parsed[j] = OrderedDict((k, v)
                                    for (k, v) in zip(self.headers, row.split()))

        try:
            self.proteinpath = self.input['GAUDI.protein']
        except KeyError:
            self.proteinpath = None

        return parsed

    def update_protein(self, protein, ligand):
        if not protein:
            return
        mol2data = ligand[0].mol2data
        try:
            start = mol2data.index('GAUDI.rotamers')
            end = mol2data.index('/GAUDI.rotamers')
        except ValueError:
            print "Sorry, no rotamer info available in mol2"
        else:
            rotamers = mol2data[start + 1:end]
            # chimera.runCommand(
            # '~show ' + ' '.join(['#{}'.format(m.id) for m in protein]))
            for line in rotamers:
                line.strip()
                if line.startswith('#'):
                    continue
                self.update_rotamers(*line.split())

    @staticmethod
    def update_rotamers(pos, lib, restype, *chis):
        lib_dict = {'DYN': 'Dynameomics', 'DUN': 'Dunbrack'}
        res = chimera.specifier.evalSpec(':' + pos).residues()[0]
        all_rotamers = Rotamers.getRotamers(
            res, resType=restype, lib=lib_dict[lib])[1]

        try:
            rotamer = next(r for r in all_rotamers if
                           [round(n, 4) for n in r.chis] == [round(float(n), 4) for n in chis])
        except StopIteration:
            print "No rotamer found for {}{} with chi angles {}".format(
                pos, restype, ','.join(chis))
        else:
            Rotamers.useRotamer(res, [rotamer])
            for a in res.atoms:
                a.display = 1
