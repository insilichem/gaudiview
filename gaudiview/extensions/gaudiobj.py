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
from __future__ import absolute_import
import os
import subprocess
import tempfile
import chimera
import Tkinter as tk
import Pmw
from importlib import import_module
# Internal dependencies
from gaudiview.extensions.base import GaudiViewBasePlugin
from libtangram.ui import TangramBaseDialog
if not chimera.nogui:
    from gaudiview.gui import error, info

try:
    import gaudi
    from gaudi.parse import Required
    from gaudi.base import Environment
    HAS_GAUDI = True
except ImportError:
    HAS_GAUDI = False


class GaudiObjectivePlugin(GaudiViewBasePlugin):

    """
    Add score columns using any Gaudi objective
    """
    KWARGS = {
        'dsx': dict(binary=None, potentials=None, proteins=('Protein',),
                    ligands=('Ligand',), terms=None, sorting=1, cofactor_mode=0,
                    with_covalent=False, with_metals=True),
        'gold': {},
        'ligscore': {'proteins': ('Protein',), 'ligands': ('ligand',)},
        'vina': {}
    }

    def do(self, proteinpath, ligandpath, objective, obj_kwargs):
        from gaudi.base import MolecularIndividual, expressed
        from gaudi.genes.molecule import Molecule
        individual = MolecularIndividual(dummy=True)
        individual.genes['Protein'] = protein = Molecule(path=proteinpath)
        individual.genes['Ligand'] = ligand = Molecule(path=ligandpath)
        individual.__ready__()
        individual.__expression_hooks__()
        obj = objective(**obj_kwargs)
        with expressed(individual):
            score = obj.evaluate(individual)
        individual.genes['Protein'].compound.destroy()
        individual.genes['Ligand'].compound.destroy()
        del individual
        return score

class GaudiObjectiveDialog(TangramBaseDialog):

    SUPPORTED_OBJECTIVES = ('dsx', 'gold', 'ligscore', 'vina')

    buttons = ("OK", "Close")

    def __init__(self, *args, **kwargs):
        self.title = 'Configure a GaudiMM objective'
        self.var_objective = tk.StringVar()
        self.var_objective.trace('w', self._fill_options)
        self.objective = None
        self.objective_kwargs = {}
        self._current_options = None
        self.obj_conf = {}
        self._returned_OK = False
        super(GaudiObjectiveDialog, self).__init__(with_logo=False, *args, **kwargs)

    def fill_in_ui(self, parent):
        self.ui_options = tk.LabelFrame(self.canvas, text='Options')
        self.ui_objectives = Pmw.OptionMenu(self.canvas, items=self.SUPPORTED_OBJECTIVES,
                                            initialitem=0,
                                            menubutton_textvariable=self.var_objective)
        self.ui_objectives.grid(row=0, column=0, sticky='we', padx=5, pady=5)
        self.ui_options.grid(row=1, column=0, sticky='we', padx=5, pady=5)
        self.canvas.columnconfigure(0, weight=1)
        self._fill_options()

    def _fill_options(self, *args):
        if self._current_options is not None:
            self._current_options.pack_forget()
            self._current_options.destroy()
        name = self.var_objective.get()
        module = import_module('gaudi.objectives.' + name)
        classname = module.enable.func_code.co_names[0]
        self.objective = obj = getattr(module, classname)
        defaults = {k: v for (k, v) in zip(obj.__init__.im_func.func_code.co_varnames[1:-2],
                                           obj.__init__.im_func.func_defaults)}
        options = self.objective._validate.copy()

        frame = tk.Frame(self.ui_options)
        self.obj_conf = {}
        for (key, validator) in options.items():
            label = str(key)
            value = defaults.get(label)
            kwargs = {'value': repr(value) if value else ''}
            if isinstance(key, Required):
                kwargs['validate'] = self._required_validator
            widget = Pmw.EntryField(frame, labelpos='w', label_text=label, **kwargs)
            widget.pack(expand=True, fill='x', padx=5, pady=5)
            self.obj_conf[key] = widget
        frame.pack(expand=True, fill='both', padx=5, pady=5)
        self._current_options = frame
        return frame

    def OK(self):
        kwargs = {}
        for k, v in self.obj_conf.items():
            parsed = self._parse_variable(v)
            if parsed is not None:
                kwargs[k] = parsed
        self.objective_kwargs = {str(k): v for (k,v) in
                                 self.objective.validate(kwargs, schema={}).items()}
        self._returned_OK = True
        self.Close()

    def enter(self):
        self._returned_OK = False
        super(GaudiObjectiveDialog, self).enter()

    @staticmethod
    def _parse_variable(var):
        value = var.getvalue()
        if not value:
            return
        try:
            evaluated = eval(value)
            if isinstance(evaluated, tuple):
                evaluated = list(evaluated)
            return evaluated
        except:
            return value

    @staticmethod
    def _required_validator(value):
        if not value:
            return Pmw.ERROR
        return Pmw.OK