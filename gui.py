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
import Tkinter
# Chimera
import chimera
from chimera.baseDialog import ModelessDialog
# Internal dependencies
from . import tables
from .extensions.base import load_controller

ui = None


def showUI(callback=None):
    """
    Requested by Chimera way-of-doing-things
    """
    global ui
    if not ui:
        ui = GaudiViewDialog()
    ui.enter()
    if callback:
        ui.addCallback(callback)


class GaudiViewDialog(ModelessDialog):

    """
    Displays main GUI and initializes models and controllers
    for the respective file format.
    """

    buttons = ("OK", "Close")
    default = None
    help = "https://bitbucket.org/jrgp/gaudiview"
    SELECTION_CHANGED = "GaudiViewSelectionChanged"
    DBL_CLICK = "GaudiViewDoubleClick"
    EXIT = "GaudiViewExited"

    def __init__(self, path, format, *args, **kwarg):
        # GUI init
        self.title = 'GaudiView'
        self.controller = load_controller(path=path, format=format, gui=self)

        # Triggers
        self.triggers = chimera.triggerSet.TriggerSet()
        self.triggers.addTrigger(self.SELECTION_CHANGED)
        self.triggers.addTrigger(self.DBL_CLICK)
        self.triggers.addHandler(
            self.SELECTION_CHANGED, self.controller.selection_changed, None)
        self.triggers.addHandler(
            self.DBL_CLICK, self.controller.double_click, None)
        # Disable ksdssp
        chimera.triggers.addHandler("Model", self.suppressKsdssp, None)

        # Fire up
        ModelessDialog.__init__(self)
        chimera.extension.manager.registerInstance(self)

        # Handle resizing
        self.uiMaster().bind("<Configure>", self.on_resize)

    def fillInUI(self, parent):
        # Create main window
        self.tframe = Tkinter.Frame(parent)
        self.tframe.pack(expand=True, fill='both')
        self.tframe.bind(
            '<Enter>', lambda event, caller=self.tframe: self.give_focus(event, caller))
        # Fill data in and create table
        self.model = tables.TableModel()
        self.model.importDict(self.controller.get_table_dict())
        self.table = tables.Table(self.tframe, self.model, editable=False,
                                  gaudiparent=self)
        self.table.createTableFrame()
        self.table.createFilteringBar(parent)
        self.table.adjustColumnWidths()
        self.table.redrawTable()

        # Per-frame CLI input
        self.cliframe = Tkinter.Frame(parent)
        self.cliframe.grid_rowconfigure(0, weight=1)
        self.cliframe.grid_columnconfigure(0, weight=1)
        Tkinter.Label(self.cliframe, text="Command input").grid(
            row=0, column=0, sticky="ew")
        self.clifield = Tkinter.Entry(self.cliframe)
        self.clifield.grid(row=1, column=0, sticky='nsew')
        self.clifield.bind('<Return>', self.controller.run_command, None)
        self.clifield.bind('<KP_Enter>', self.controller.run_command, None)
        self.clibutton = Tkinter.Button(
            self.cliframe, text="Run", width=5, command=self.controller.run_command)
        self.clibutton.grid(row=1, column=1, sticky='news')

        # Enables selection of current entries in Chimera canvas
        # if format uses several molecules per entry (GAUDI)
        if self.controller.HAS_SELECTION:
            self.selection_listbox = Tkinter.Listbox(
                self.cliframe, selectmode=Tkinter.EXTENDED, height=5)
            self.selection_listbox.grid(row=2, column=0, sticky='nsew')
            self.selection_listbox.bind('<<ListboxSelect>>',
                                        self.controller.select_in_chimera)

            self.selectionbool = Tkinter.BooleanVar()
            self.selectioncheck = Tkinter.Checkbutton(
                self.cliframe, text="Select in Chimera", variable=self.selectionbool,
                command=self.controller.select_in_chimera)
            self.selectioncheck.grid(row=2, column=1, sticky='ew')
            self.selectioncheck.select()
        # for single-molecule-per-entry formats (GOLD),
        # a single tickbox is enough
        else:
            self.selectionbool = Tkinter.BooleanVar()
            self.selectioncheck = Tkinter.Checkbutton(
                self.cliframe, text="Select in Chimera", variable=self.selectionbool,
                command=self.controller.select_in_chimera)
            self.selectioncheck.grid(row=2, column=0, sticky='w')

        self.cliframe.pack(fill='x')

        # Details of selected solution
        if self.controller.HAS_DETAILS:
            self.details_frame = Tkinter.Frame(parent)
            self.details_frame.grid_rowconfigure(0, weight=1)
            self.details_frame.grid_columnconfigure(0, weight=1)
            Tkinter.Label(self.details_frame, text="Details").grid(
                row=0, column=0, sticky='new')

            self.details_scroll_x = Tkinter.Scrollbar(
                self.details_frame, orient=Tkinter.HORIZONTAL)
            self.details_scroll_x.grid(row=2, column=0, sticky='ew')
            self.details_scroll_y = Tkinter.Scrollbar(self.details_frame)
            self.details_scroll_y.grid(row=1, column=1, sticky='ns')

            self.details_field = Tkinter.Text(
                self.details_frame, state=Tkinter.DISABLED,
                font=('Monospace', 10), height=8, wrap=Tkinter.NONE)
            self.details_field.grid(row=1, column=0, sticky='nsew')
            self.details_field.config(yscrollcommand=self.details_scroll_y.set,
                                      xscrollcommand=self.details_scroll_x.set)
            self.details_scroll_x.config(command=self.details_field.xview)
            self.details_scroll_y.config(command=self.details_field.yview)
            self.details_frame.bind(
                '<Enter>', lambda event, caller=self.details_frame: self.give_focus(event, caller))
            self.details_frame.pack(fill='x')

        if self.controller.HAS_MORE_GUI:
            self.controller.extend_gui()

    def Apply(self):
        """
        Close unselected entries
        """
        chimera.openModels.close(
            [m_ for p in self.controller.molecules
             for m_ in self.controller.model.molecules[p]
             if p not in self.controller.selected])

    def OK(self):
        self.Apply()
        self.destroy()

    def Close(self):
        """
        Close everything amd exit
        """
        self.controller.close_all()
        self.destroy()

    def on_resize(self, event):
        self.width = event.width
        self.height = event.height

    def update_details_field(self, info=None):
        """
        Clears details_field and writes new content
        """
        if not info:
            info = "Not info available for selection"
        self.details_field.config(state=Tkinter.NORMAL)
        self.details_field.delete(1.0, Tkinter.END)
        self.details_field.insert(Tkinter.END, info)
        self.details_field.config(state=Tkinter.DISABLED)

    @staticmethod
    def give_focus(event, caller=None):
        """
        Gives focus (for keyboard bindings, mainly) to whatever
        widget/frame we put the cursor over
        """
        caller.focus_set()

    @staticmethod
    def info(text):
        chimera.statusline.show_message(text, color='black', blankAfter=3)

    @staticmethod
    def error(text):
        chimera.statusline.show_message(text, color='red', blankAfter=3)

    @staticmethod
    def suppressKsdssp(trigName, myData, molecules):
        for m in molecules.created:
            m.structureAssigned = True
