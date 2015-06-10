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
import os
import subprocess
import tempfile
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBasePlugin


class DSXPlugin(GaudiViewBasePlugin):

    """
    Scores given system using DrugScoreX binaries
    """

    def __init__(self):
        self.binary = os.environ.get('DSX_BINARY')
        self.potentials = os.environ.get('DSX_POTENTIALS')
        self.oldworkingdir = os.getcwd()
        self.tempdir = tempfile.gettempdir()

    def do(self, protein, ligand,
           I='1', S='1', T0='1.0', T1='1.0', T2='0.0', T3='1.0'):
        # Since DSX outputs to working dir, we better not pollute it
        # Use tempdir instead and restore later
        os.chdir(self.tempdir)
        command = [self.binary, '-P', protein, '-L', ligand, '-I', I,
                   '-S', S, '-T0', T0, '-T1', T1, '-T2', T2, '-T3', T3,
                   '-D', self.potentials]
        try:
            stream = subprocess.check_output(command, universal_newlines=True)
        except subprocess.CalledProcessError:
            print "Could not run", command
        else:
            # 1. Get output filename from stdout (located at working directory)
            # 2. Find line '@RESULTS' and go to sixth line below
            # 3. The score is in the first row of the table, at the third field
            with open(os.path.join(os.getcwd(), stream.splitlines()[-2].split()[-1])) as f:
                lines = f.read().splitlines()
                i = lines.index('@RESULTS')
                score = lines[i + 4].split('|')[3].strip()
                print "DSX score is", score
                return float(score)
        finally:
            os.chdir(self.oldworkingdir)
