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

import chimera.extension
from OpenSave import OpenModeless

FILTERS = [
    ("GAUDI results", ["*.gaudi", "*.gaudi.yaml"]),
    ("GOLD results", ["*.conf"])
]


class GaudiViewEMO(chimera.extension.EMO):

    def name(self):
        return "GAUDIView"

    def description(self):
        return "Light interface to explore solutions from GAUDIasm and more"

    def categories(self):
        return ['GAUDI']

    def activate(self):
        OpenModeless(command=self._browse, title="Open input file",
                     filters=FILTERS, dialogKw={'oneshot': 1}, historyID="GaudiView")

    def _browse(self, okayed, dialog):
        if okayed:
            for path, format in dialog.getPathsAndTypes():
                self.module('gui').GaudiViewDialog(path, format)

emo = GaudiViewEMO(__file__)
chimera.extension.manager.registerExtension(emo)
