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
GaudiView is built with extensibility in mind. It is designed
around a MVC architecture, whose non-GUI components are located
in single modules.

Each of these modules must contain a controller class that
subclasses :class:`base.GaudiViewBaseController` and a model that
subclasses :class:`base.GaudiViewBaseModel`. These are pseudo
abstract base classes, so they implement concret methods which
you would not need to modify, normally, but also some ABCs that
you will HAVE to override.

For the controller, these are:

:meth:`display` Request displayable objects from model and take
                them to the Chimera canvas (called on single
                clicks).

:meth:`process` Get metadata from model and display it. (called
                on double clicks).

:meth:`get_table_dict:  Return a dict formatted as requested by
                        tkintertable.

For the model, there are no concrete methods. You must implement:

:meth:`__init__`    Get the file and pass it to :meth:`parse`

:meth:`parse`       Process the input file and extract headers,
                    table data, metadata, and so on.

:meth:`details`     Get metadata info for given key.

The new module MUST include a load function that returns an instance
of the controller. The call must include a reference to the corresponding
model. For example:

    def load(*args, **kwargs):
        return MyNewController(model=MyNewModel, *args, **kwargs)
"""
