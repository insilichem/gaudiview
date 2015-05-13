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


class GaudiViewEMO(chimera.extension.EMO):

    def name(self):
        return "GAUDIView"

    def description(self):
        return "Light interface to explore solutions from GAUDIasm and more"

    def categories(self):
        return ['GAUDI']

    def activate(self):
        self.module('gui').browse()
        return None

emo = GaudiViewEMO(__file__)
chimera.extension.manager.registerExtension(emo)
