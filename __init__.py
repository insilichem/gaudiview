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

"""
GaudiView is a lightweight interface to explore
solutions from molecular design programs, such as GAUDI,
GOLD docking, and so on.

It is built with extensibility in mind following a MVC
architecture (Model-View-Controller), so it's easy to
use it for custom formats while keeping the same GUI.
Go to `extensions` for further info on the subject.

The GUI (View) features a multi-sortable and filterable
table capable of holding thousands of entries, since the
actual files are lazy-loaded on request.

A single click displays the item(s), while a double click
applies further processing, such as displaying interactions
and other metadata.

*GaudiView uses UCSF Chimera, PyYaml, and tkintertable.*
"""
