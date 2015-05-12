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

import imp


class GetData(object):

    FORMATS = {
        'GAUDI results': 'gaudi',
        'GOLD results': 'gold'
    }

    def __init__(self, path, format):
        module = imp.load_module(FORMATS[format])
        self.data = module.load(path)
        self.data.parse()

    def open_molecule_path(self, *paths):
        for p in paths:
            try:
                self.show_molecules(*self.molecules[p])
            except KeyError:
                self.molecules[p] = chimera.openModels.open(p, shareXform=True)

        # Open protein
        try:
            self.protein = chimera.openModels.open(self.proteinpath)
        except:
            self.protein = None

        # DATA init
        self.input, self.data = None, None
        if self.format == 'GAUDI results':
            self.parse_gaudi()
            self.triggers.addHandler(
                self.DBL_CLICK, self._update_protein_gaudi, None)
        elif self.format == 'GOLD results':
            self.parse_gold()
            self.triggers.addHandler(
                self.DBL_CLICK, self._update_protein_gold, None)
        else:
            raise UserError("Unknown format {}".format(self.format))
