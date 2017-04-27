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

# External dependencies
import chimera
from tkintertable.Tables import TableCanvas, ColumnHeader, RowHeader, AutoScrollbar
from tkintertable.Filtering import *
from tkintertable.TableModels import TableModel
from tkintertable.Tables_IO import TableImporter


class Table(TableCanvas):

    def set_defaults(self):
        """Set default settings"""
        self.cellwidth = 60
        self.maxcellwidth = 1000
        self.rowheight = 20
        self.horizlines = 1
        self.vertlines = 0
        self.alternaterows = 1
        self.autoresizecols = 1
        self.inset = 2
        self.x_start = 0
        self.y_start = 1
        self.linewidth = 1.0
        self.rowheaderwidth = 0
        self.showkeynamesinheader = False
        self.thefont = ('Arial', -15)
        self.cellbackgr = '#EEEEEE'
        self.entrybackgr = 'white'
        self.grid_color = '#ABB1AD'
        self.selectedcolor = 'yellow'
        self.rowselectedcolor = '#DDDDDD'
        self.multipleselectioncolor = '#DDDDDD'
    
    def adjustColumnWidths(self):
        """Optimally adjust col widths to accomodate the longest entry
            in each column - usually only called  on first redraw"""
        #self.cols = self.model.getColumnCount()
        try:
            fontsize = self.thefont[1]
        except:
            fontsize = self.fontsize
        dpi = chimera.tkgui.app.winfo_fpixels('1i')/72.0
        scale = 8.5 * float(abs(fontsize))/(12+2*dpi)
        for col in range(self.cols):
            colname = self.model.getColumnName(col)
            if self.model.columnwidths.has_key(colname):
                w = self.model.columnwidths[colname]
            else:
                w = self.cellwidth
            maxlen = self.model.getlongestEntry(col)
            size = maxlen * scale
            if size < w:
                continue
            #print col, size, self.cellwidth
            if size >= self.maxcellwidth:
                size = self.maxcellwidth
            self.model.columnwidths[colname] = size + float(fontsize)/12*6
        return

    def do_bindings(self):
        self.bind("<Button-1>", self.handle_left_click)
        self.bind("<Double-Button-1>", self.handle_double_click)
        self.bind("<ButtonRelease-1>", self.handle_left_release)
        self.bind("<MouseWheel>", self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)
        self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
        self.bind("<Shift-Button-1>", self.handle_left_shift_click)
        self.bind("<Up>", self.handle_arrow_keys)
        self.bind("<Down>", self.handle_arrow_keys)
        self.bind("<Control-c>", self.handle_ctrl_c)
        # self.focus_set()

    def handle_left_click(self, event):
        self.clearSelected()
        self.delete('rowrect')

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        self.focus_set()
        self.startrow = row
        self.endrow = row
        self.startcol = col
        self.endcol = col
        # reset multiple selection list
        self.multiplerowlist = []
        self.multiplerowlist.append(row)

        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.setSelectedRow(row)
            self.drawSelectedRow()

    def handle_left_release(self, event):
        self.endrow = self.get_row_clicked(event)
        self.gaudiparent.triggers.activateTrigger(
            self.gaudiparent.SELECTION_CHANGED, None)

    def handle_arrow_keys(self, event):
        """Handle arrow keys press"""
        x, y = self.getCanvasPos(self.currentrow, 0)
        if x is None:
            return
        if event.keysym == 'Up':
            if self.currentrow == 0:
                return
            else:
                self.currentrow = self.currentrow - 1
        elif event.keysym == 'Down':
            if self.currentrow >= self.rows - 1:
                return
            else:
                self.currentrow = self.currentrow + 1

        self.multiplerowlist = []
        self.multiplerowlist.append(self.currentrow)
        self.setSelectedRow(self.currentrow)
        self.drawSelectedRow()
        self.gaudiparent.triggers.activateTrigger(
            self.gaudiparent.SELECTION_CHANGED, None)

    def handle_double_click(self, event):
        """Do double click stuff. Selected row/cols will already have
           been set with single click binding"""

        row = self.get_row_clicked(event)
        self.gaudiparent.triggers.activateTrigger(
            self.gaudiparent.DBL_CLICK, row)

    def handle_ctrl_c(self, event):
        clipboard = []
        for key in self.gaudiparent.controller.selected:
            clipboard.append('\t'.join(self.model.data[key].values()))
        self.gaudiparent._toplevel.master.clipboard_clear()
        self.gaudiparent._toplevel.master.clipboard_append('\n'.join(clipboard))

    def createTableFrame(self, callback=None):
        self.tablerowheader = RowHeader(
            self.parentframe, self, width=self.rowheaderwidth)
        self.tablecolheader = Headers(self.parentframe, self, height=self.rowheight)
        self.Yscrollbar = AutoScrollbar(
            self.parentframe, orient=VERTICAL, command=self.set_yviews)
        self.Yscrollbar.grid(
            row=1, column=2, rowspan=1, sticky='news', pady=0, ipady=0)
        self.Xscrollbar = AutoScrollbar(
            self.parentframe, orient=HORIZONTAL, command=self.set_xviews)
        self.Xscrollbar.grid(row=2, column=1, columnspan=1, sticky='news')
        self['xscrollcommand'] = self.Xscrollbar.set
        self['yscrollcommand'] = self.Yscrollbar.set
        self.tablecolheader['xscrollcommand'] = self.Xscrollbar.set
        self.tablerowheader['yscrollcommand'] = self.Yscrollbar.set
        self.parentframe.rowconfigure(1, weight=1)
        self.parentframe.columnconfigure(1, weight=1)

        self.tablecolheader.grid(
            row=0, column=1, rowspan=1, sticky='news', pady=0, ipady=0)
        self.tablerowheader.grid(
            row=1, column=0, rowspan=1, sticky='news', pady=0, ipady=0)
        self.grid(row=1, column=1, rowspan=1, sticky='news', pady=0, ipady=0)

        self.adjustColumnWidths()
        self.redrawTable(callback=callback)
        self.parentframe.bind("<Configure>", self.redrawVisible)
        self.tablecolheader.xview("moveto", 0)
        self.xview("moveto", 0)

    def resizeColumn(self, col, width):
        """Resize a column by dragging"""
        # print 'resizing column', col
        # recalculate all col positions..
        colname = self.model.getColumnName(col)
        self.model.columnwidths[colname] = width
        self.setColPositions()
        self.redrawTable()

    def createFilteringBar(self, parent=None, fields=None):
        """Add a filter frame"""
        if parent is None:
            parent = Toplevel()
            parent.title('Filter Records')
            x, y, w, h = self.getGeometry(self.master)
            parent.geometry('+%s+%s' % (x, y + h))
        if fields is None:
            fields = self.model.columnNames

        self.filterframe = Filters(parent, fields, self.doFilter, self.showAll)
        self.filterframe.pack()
        return parent

    def doFilter(self, event=None):
        """Filter the table display by some column values.
        We simply pass the model search function to the the filtering
        class and that handles everything else.
        See filtering frame class for how searching is done.
        """
        if self.model is None:
            return
        names = self.filterframe.doFiltering(searchfunc=self.model.filterBy)
        if not names:
            self.filtered = False
            return
        # create a list of filtered recs
        self.model.filteredrecs = names
        self.filtered = True
        self.redrawTable()
        return

    def setSelectedRow(self, row):
        """Set currently selected row and reset multiple row list"""
        self.currentrow = row
        self.multiplerowlist = []
        self.multiplerowlist.append(row)

        return

    def drawSelectedRect(self, row, col, color=None):
        pass

    def drawSelectedCol(self, col=None, delete=1):
        pass

    def drawMultipleCells(self):
        pass

    def drawSelectedRow(self, row=None):
        """Draw the highlight rect for the currently selected row"""
        if not row:
            row = self.currentrow
            self.delete('rowrect')

        x1, y1, x2, y2 = self.getCellCoords(row, 0)
        x2 = self.tablewidth
        rect = self.create_rectangle(x1, y1, x2, y2,
                                     fill=self.rowselectedcolor,
                                     outline=self.rowselectedcolor,
                                     tag='rowrect')
        self.lower('rowrect')
        self.lower('fillrect')
        self.tablerowheader.drawSelectedRows(self.currentrow)

    def drawMultipleRows(self, rowlist):
        """Draw more than one row selection"""
        self.delete('multiplesel')
        for r in rowlist:
            if r not in self.visiblerows or r > self.rows - 1:
                continue
            self.drawSelectedRow(r)
        self.lower('multiplesel')
        self.lower('fillrect')
        return


class Headers(ColumnHeader):

    def __init__(self, parent=None, table=None, width=500, height=20):
        Canvas.__init__(self, parent, bg='gray25', width=width, height=height)
        self.thefont = ('Arial', -15)
        if table is not None:
            self.table = table
            self.height = height
            self.model = self.table.getModel()
            self.config(width=self.table.width)
            self.columnlabels = self.model.columnlabels
            self.bind('<Button-1>', self.handle_left_click)
            self.bind("<ButtonRelease-1>", self.handle_left_release)
            self.bind('<B1-Motion>', self.handle_mouse_drag)
            self.bind('<Motion>', self.handle_mouse_move)
            self.thefont = self.table.thefont
            self.reversedcols = dict((colname_, 0)
                                     for colname_ in self.model.columnNames)
        return

    def handle_left_click(self, event):
        """Does cell selection when mouse is clicked on canvas"""
        self.delete('rect')
        self.table.delete('entry')
        self.table.delete('multicellrect')
        colclicked = self.table.get_col_clicked(event)
        if colclicked is None:
            return
        # set all rows selected
        self.table.allrows = True
        self.table.setSelectedCol(colclicked)

        if self.atdivider == 1:
            return
        # also draw a copy of the rect to be dragged
        self.draggedcol = None
        self.drawRect(self.table.currentcol, tag='dragrect',
                      color='red', outline='white')
        if hasattr(self, 'rightmenu'):
            self.rightmenu.destroy()

    def handle_left_release(self, event):
        """When mouse released implement resize or col move"""
        self.delete('dragrect')
        if self.atdivider == 1:
            #col = self.table.get_col_clicked(event)
            x = int(self.canvasx(event.x))
            col = self.table.currentcol
            x1, y1, x2, y2 = self.table.getCellCoords(0, col)
            newwidth = x - x1
            if newwidth < 5:
                newwidth = 5
            self.table.resizeColumn(col, newwidth)
            self.table.delete('resizeline')
            self.delete('resizeline')
            self.delete('resizesymbol')
            self.atdivider = 0
            return
        self.delete('resizesymbol')
        # move column
        if self.draggedcol is not None and self.table.currentcol != self.draggedcol:
            self.model.moveColumn(self.table.currentcol, self.draggedcol)
            self.table.redrawTable()
        elif not self.draggedcol:  # sort!
            try:
                former_selected_row = self.table.get_currentRecordName()
            except IndexError:
                former_selected_row = -1
            sortkey = self.model.getColumnName(self.table.currentcol)
            self.reversedcols[sortkey] = not self.reversedcols[sortkey]
            self.columnlabels[sortkey] = '{} {}'.format((u'\u25B2', u'\u25BC')[int(self.reversedcols[sortkey])],
                                                        sortkey)
            self.table.sortTable(self.table.currentcol, reverse=self.reversedcols[sortkey])
            self.table.currentrow = self.table.model.getRecordIndex(former_selected_row)
            self.table.drawSelectedRow()
            self.table.redrawTable()


class Filters(FilterFrame):

    def __init__(self, parent, fields, callback=None, closecallback=None):
        """Create a filtering gui frame.
        Callback must be some method that can accept tuples of filter
        parameters connected by boolean operators """
        Frame.__init__(self, parent)
        self.parent = parent
        self.callback = callback
        self.closecallback = closecallback
        self.fields = fields
        self.filters = []
        self.gobutton = Button(
            self, text='Filter', command=self.callback, state=DISABLED)
        self.gobutton.grid(row=0, column=0, sticky='news', padx=2, pady=2)
        addbutton = Button(self, text='+Add', command=self.addFilterBar)
        addbutton.grid(row=0, column=1, sticky='news', padx=2, pady=2)
        self.cbutton = Button(
            self, text='Reset', command=self.resetFiltering, state=DISABLED)
        self.cbutton.grid(row=0, column=2, sticky='news', padx=2, pady=2)
        self.resultsvar = IntVar()
        self.results = Label(self, text='Results:', state=DISABLED,
                             disabledforeground=parent.cget('bg'))
        self.results.grid(row=0, column=3, sticky='nes')
        self.resultsnum = Label(self, textvariable=self.resultsvar, state=DISABLED,
                                disabledforeground=parent.cget('bg'))
        self.resultsnum.grid(row=0, column=4, sticky='nws', padx=2, pady=2)

    def addFilterBar(self):
        """Add filter"""
        index = len(self.filters)
        f = FilterBar_(self, index, self.fields)
        self.filters.append(f)
        f.grid(row=index + 1, column=0, columnspan=5,
               sticky='news', padx=2, pady=2)
        self.gobutton.config(state=NORMAL)
        self.cbutton.config(state=NORMAL)

    def updateResults(self, i):
        self.resultsvar.set(i)
        self.results.config(state=NORMAL)
        self.resultsnum.config(state=NORMAL)

    def resetFiltering(self):
        for f in self.filters:
            f.close()
        self.closecallback()


class FilterBar_(FilterBar):

    """Class providing filter widgets"""
    operators = ['=', '!=', '>', '<', '>=', '<=', 'contains']
    booleanops = ['AND', 'OR', 'NOT']

    def __init__(self, parent, index, fields):
        Frame.__init__(self, parent)
        self.parent = parent
        self.index = index
        self.filtercol = StringVar()
        initial = fields[0]
        filtercolmenu = Pmw.OptionMenu(self,
                                       menubutton_textvariable=self.filtercol,
                                       items=fields,
                                       initialitem=initial,
                                       menubutton_width=10)
        filtercolmenu.grid(row=0, column=1, sticky='news', padx=2, pady=2)
        self.operator = StringVar()
        operatormenu = Pmw.OptionMenu(self,
                                      menubutton_textvariable=self.operator,
                                      items=self.operators,
                                      initialitem=self.operators[0],
                                      menubutton_width=2)
        operatormenu.grid(row=0, column=2, sticky='news', padx=2, pady=2)
        self.filtercolvalue = StringVar()
        valsbox = Entry(
            self, textvariable=self.filtercolvalue, width=20, bg='white')
        valsbox.grid(row=0, column=3, sticky='news', padx=2, pady=2)
        valsbox.bind("<Return>", self.parent.callback)
        valsbox.bind("<KP_Enter>", self.parent.callback)
        self.booleanop = StringVar()
        booleanopmenu = Pmw.OptionMenu(self,
                                       menubutton_textvariable=self.booleanop,
                                       items=self.booleanops,
                                       initialitem='AND',
                                       menubutton_width=6)
        booleanopmenu.grid(row=0, column=0, sticky='news', padx=2, pady=2)
        # disable the boolean operator if it's the first filter
        if self.index == 0:
            booleanopmenu.component('menubutton').configure(state=DISABLED)
        cbutton = Button(self, text='-', command=self.close)
        cbutton.grid(row=0, column=5, sticky='news', padx=2, pady=2)

    def close(self):
        """Destroy and remove from parent"""
        self.parent.filters.remove(self)
        if not self.parent.filters:
            self.parent.gobutton.config(state=DISABLED)
            self.parent.cbutton.config(state=DISABLED)
            self.parent.results.config(state=DISABLED)
            self.parent.resultsnum.config(state=DISABLED)
        self.destroy()


class OrderedTableImporter(TableImporter):

    def ImportTableModel(self, filename, sep=','):
        from collections import OrderedDict
        import os
        import csv

        if not os.path.isfile(filename):
            return None
        dictreader = csv.DictReader(open(filename, "rb"), delimiter=sep)
        dictdata = OrderedDict()
        for i, rec in enumerate(dictreader):
            dictdata[i] = OrderedDict((f, rec[f])
                                      for f in dictreader.fieldnames)
        return dictdata
