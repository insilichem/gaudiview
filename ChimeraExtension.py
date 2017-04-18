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

import chimera
from OpenSave import OpenModeless

FILTERS = [
    ("GaudiMM results", ["*.gaudi-output"]),
    ("GOLD results", ["*.conf"])
]


class GaudiViewEMO(chimera.extension.EMO):

    def name(self):
        return "GAUDIView"

    def description(self):
        return "Light interface to explore solutions from GaudiMM and GOLD"

    def categories(self):
        return ['InsiliChem']

    def activate(self):
        OpenModeless(command=self._browse, title="Open input file",
                     filters=FILTERS, dialogKw={'oneshot': 1}, historyID="GaudiView")

    def _browse(self, okayed, dialog):
        if okayed:
            for path, filetype in dialog.getPathsAndTypes():
                self.gaudiview_open(path, filetype)

    def gaudiview_open(self, path, filetype):
        self.module('gui').GaudiViewDialog(path, filetype)

    def gaudiview_open_gaudi(self, path):
        self.module('gui').GaudiViewDialog(path, "GAUDI results")

    def gaudiview_open_gold(self, path):
        self.module('gui').GaudiViewDialog(path, "GOLD results")

emo = GaudiViewEMO(__file__)
chimera.extension.manager.registerExtension(emo)
chimera.fileInfo.register("GAUDI output", emo.gaudiview_open_gaudi, ['.gaudi-output'],
                          ['GAUDI output'], category=chimera.FileInfo.STRUCTURE)
chimera.fileInfo.register("GOLD output", emo.gaudiview_open_gold, ['.conf'],
                          ['GOLD output'], category=chimera.FileInfo.STRUCTURE)
