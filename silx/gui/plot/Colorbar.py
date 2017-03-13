# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016-2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
"""A widget displaying a colorbar linked to a :class:`PlotWidget`.

It is a wrapper over matplotlib :class:`ColorbarBase`.

It uses a description of colormaps as dict compatible with :class:`Plot`.

To run the following sample code, a QApplication must be initialized.

>>> import numpy
>>> from silx.gui.plot import Plot2D
>>> from silx.gui.plot.Colorbar import ColorbarWidget

>>> plot = Plot2D()  # Create a plot widget
>>> plot.show()

>>> colorbar = ColorbarWidget(plot=plot)  # Associate the colorbar with it
>>> colorbar._setLabel('Colormap')
>>> colorbar.show()
"""

__authors__ = ["H. Payno", "T. Vincent"]
__license__ = "MIT"
__date__ = "10/03/2017"


import logging
import numpy
from silx.gui.plot import PlotWidget


from .. import qt
from silx.gui.plot import Colors

_logger = logging.getLogger(__name__)


class ColorbarWidget(qt.QWidget):
    """Colorbar widget displaying a colormap

    This widget is using matplotlib.

    :param parent: See :class:`QWidget`
    :param plot: PlotWidget the colorbar is attached to (optional)
    """

    def __init__(self, parent=None, plot=None):
        super(ColorbarWidget, self).__init__(parent)
        self._plot = plot
        self.setContentsMargins(0, 0, 0, 0);
        # self.setEnabled(False)

        self.colorbar = None  # matplotlib colorbar this will be an object

        self._label = ''  # Text label to display
        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)

        layout = qt.QVBoxLayout()
        self.setLayout(layout)
        self.layout().addWidget(self.__buildMainColorMap())
        self.layout().addWidget(self.__buildAutoscale())
        self.layout().addWidget(self.__buildNorm())

        if self._plot is not None:
            self._plot.sigActiveImageChanged.connect(self._activeImageChanged)
            self._activeImageChanged(
                None, self._plot.getActiveImage(just_legend=True))

    def __buildMainColorMap(self):
        widget = qt.QWidget(self)
        widget.setLayout(qt.QVBoxLayout())
        widget.layout().addWidget(self.__buildGradationAndLegend())
        return widget

    def __buildNorm(self):
        group = qt.QGroupBox('Normalization', parent=self)
        group.setLayout(qt.QHBoxLayout())

        self._linearNorm = qt.QRadioButton('linear', group)
        group.layout().addWidget(self._linearNorm)

        self._logNorm = qt.QRadioButton('log', group)
        group.layout().addWidget(self._logNorm)

        return group

    def __buildAutoscale(self):
        self._autoscaleCB = qt.QCheckBox('autoscale', parent=self)
        return self._autoscaleCB
        
    def __buildGradationAndLegend(self):
        widget = qt.QWidget(self)
        widget.setLayout(qt.QHBoxLayout())
        widget.layout().setContentsMargins(0, 0, 0, 0)
        # create gradation
        self._gradation = GradationBar(parent=widget, 
                                       colormap=self._plot.getDefaultColormap(),
                                       ticks=[0.0, 0.5, 1.0])
        widget.layout().addWidget(self._gradation)

        self.legend = VerticalLegend('test 1 2 3 4 5 6 7 8', self)
        widget.layout().addWidget(self.legend)

        widget.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Preferred)
        return widget

    def getColormap(self):
        """Return the colormap displayed in the colorbar as a dict.

        It returns None if no colormap is set.
        See :class:`Plot` documentation for the description of the colormap
        dict description.
        """
        return self._colormap.copy()

    def setColormap(self, name, normalization='linear',
                    vmin=0., vmax=1., colors=None, autoscale=False):
        """Set the colormap to display in the colorbar.

        :param str name: The name of the colormap or None
        :param str normalization: Normalization to use: 'linear' or 'log'
        :param float vmin: The value to bind to the beginning of the colormap
        :param float vmax: The value to bind to the end of the colormap
        :param colors: Array of RGB(A) colors to use as colormap
        :type colors: numpy.ndarray
        """
        if name is None and colors is None:
            self.colorbar = None
            self._colormap = None
            return

        if normalization == 'linear':
            self._setLinearNorm()
        elif normalization == 'log':
            self._setLogNorm()
            if vmin <= 0 or vmax <= 0:
                _logger.warning(
                    'Log colormap with bound <= 0: changing bounds.')
                vmin, vmax = 1., 10.
            pass
        else:
            raise ValueError('Wrong normalization %s' % normalization)

        self.colorbar = None # TODO : get colorma
        self._setAutoscale(autoscale)

        self.legend.setText(self._label)
        # if normalization == 'linear':
        #     formatter = matplotlib.ticker.FormatStrFormatter('%.4g')
        #     self.colorbar.formatter = formatter
        #     self.colorbar.update_ticks()

        self._colormap = {'name': name,
                          'normalization': normalization,
                          'autoscale': autoscale,
                          'vmin': vmin,
                          'vmax': vmax,
                          'colors': colors}

    def getLabel(self):
        """Return the label of the colorbar (str)"""
        return self._label

    def _setLogNorm(self):
        self._logNorm.setChecked(True)

    def _setLinearNorm(self):
        self._linearNorm.setChecked(True)

    def _setAutoscale(self, b):
        self._autoscaleCB.setChecked(b)

    def _setLabel(self, label):
        """Set the label displayed along the colorbar

        :param str label: The label
        """
        self._label = str(label)
        if self.colorbar is not None:
            self.colorbar.set_label(self._label)

    def _activeImageChanged(self, previous, legend):
        """Handle plot active curve changed"""
        if legend is None:  # No active image, display default colormap
            self._syncWithDefaultColormap()
            return

        # Sync with active image
        image = self._plot.getActiveImage()[0]

        # RGB(A) image, display default colormap
        if image.ndim != 2:
            self._syncWithDefaultColormap()
            return

        # data image, sync with image colormap
        cmap = self._plot.getActiveImage()[4]['colormap']
        if cmap['autoscale']:
            if cmap['normalization'] == 'log':
                data = image[
                    numpy.logical_and(image > 0, numpy.isfinite(image))]
            else:
                data = image[numpy.isfinite(image)]
            vmin, vmax = data.min(), data.max()
        else:  # No autoscale
            vmin, vmax = cmap['vmin'], cmap['vmax']

        self.setColormap(name=cmap['name'],
                         normalization=cmap['normalization'],
                         vmin=vmin,
                         vmax=vmax,
                         colors=cmap.get('colors', None))

    def _defaultColormapChanged(self):
        """Handle plot default colormap changed"""
        if self._plot.getActiveImage() is None:
            # No active image, take default colormap update into account
            self._syncWithDefaultColormap()

    def _syncWithDefaultColormap(self):
        """Update colorbar according to plot default colormap"""
        cmap = self._plot.getDefaultColormap()
        if cmap['autoscale']:  # Makes sure range is OK
            vmin, vmax = 1., 10.
        else:
            vmin, vmax = cmap['vmin'], cmap['vmax']

        self.setColormap(name=cmap['name'],
                         normalization=cmap['normalization'],
                         vmin=vmin,
                         vmax=vmax,
                         colors=cmap.get('colors', None))


class VerticalLegend(qt.QLabel):
    """Display vertically the given text

    :param text: the legend
    :param parent: the Qt parent if any
    """
    def __init__(self, text, parent=None):
        qt.QLabel.__init__(self, text, parent)
        self.layout().setContentsMargins(0, 0, 0, 0)

    def paintEvent(self, event ):
        painter = qt.QPainter(self)
        painter.setFont(self.font())

        painter.translate(0, self.rect().height())
        painter.rotate(270)
        newRect = qt.QRect(0, 0, self.rect().height(), self.rect().width())
        # painter.drawText(self.rect(),
        painter.drawText(newRect,
                         qt.Qt.AlignHCenter,self.text())

        fm = qt.QFontMetrics(self.font())
        preferedHeight = fm.width(self.text())
        preferedWidth = fm.height()
        self.setFixedWidth(preferedWidth)
        self.setMinimumHeight(preferedHeight)

class GradationBar(qt.QWidget):
    """The object grouping the Gradation and ticks associated to the Gradation

    :param colormap: the colormap to be displayed
    :param ticks: tuple or list of the values to be diaplyed as ticks
    :param parent: the Qt parent if any
    """
    def __init__(self, colormap, ticks, parent=None):
        """

        :param ticks: list or tuple registering the ticks to displayed.
            TODO : add behavior
        """
        super(GradationBar, self).__init__(parent)

        self.setLayout(qt.QHBoxLayout())
        self.leftGroup = qt.QWidget(self)
        self.layout().addWidget(self.leftGroup)
        self.rightGroup = qt.QWidget(self)
        self.layout().addWidget(self.rightGroup)

        self.leftGroup.setLayout(qt.QVBoxLayout())
        self.rightGroup.setLayout(qt.QVBoxLayout())

        # create the left side group (Gradation)
        self.rightGroup.layout().addWidget(self.getBottomDownWidget())
        self.rightGroup.layout().addWidget(Gradation(colormap=colormap, parent=self))
        self.rightGroup.layout().addWidget(self.getBottomDownWidget())

        # create the right side group (Gradation)
        self.leftGroup.layout().addWidget(TickBar(ticks=ticks, parent=self))

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.leftGroup.layout().setContentsMargins(0, 0, 0, 0)
        self.rightGroup.layout().setContentsMargins(0, 0, 0, 0)

    def getBottomDownWidget(self):
        w = qt.QWidget(self)
        return w


class Gradation(qt.QWidget):
    """Simple widget wich display the colormap gradation and update the tooltip
    to return the value equivalence for the color

    :param colormap: the colormap to be displayed
    :param parent: the Qt parent if any
    """
    def __init__(self, colormap, parent=None):
        qt.QWidget.__init__(self, parent)
        self.setLayout(qt.QVBoxLayout())
        self.colormap = MyColorMap(colormap)

        self.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
        self.layout().setContentsMargins(0, 0, 0, 0)

        # needed to get the mouse event without waiting for button click
        self.setMouseTracking(True)

    def paintEvent(self, event):
        
        qt.QWidget.paintEvent(self, event)

        painter = qt.QPainter(self)
        gradient = qt.QLinearGradient(0, 0, 0, self.rect().height());
        for pt in numpy.arange(0, 256):
            position = pt/256.0
            gradient.setColorAt( position, self.colormap.getColor(position))

        painter.setBrush(gradient)
        painter.drawRect(self.rect())

    def mouseMoveEvent(self, event):
        self.setToolTip(str(self.getValueFromRelativePostion(self._getRelativePosition(event.y()))))
        super(Gradation, self).mouseMoveEvent(event)

    def _getRelativePosition(self, yPixel):
        """yPixel : pixel position into Gradation widget reference
        """
        # widgets are bottom-top referencial but we display in top-bottom referential
        return 1.0-float(yPixel)/float(self.height())

    def getValueFromRelativePostion(self, value):
        """Return the value in the colorMap from a relative position in the 
        GradationBar (y)

        :param val: float value in [0, 1]
        :return: the value in [minVal, maxVal]
        """
        if not ((value >=0) and (value <=1)):
            raise ValueError('invalid value given, should be in [0.0, 1.0]')
        #TODO : deal with log type
        return self.colormap.vmin + (self.colormap.vmax-self.colormap.vmin)*value


class MyColorMap(object):
    """
    Temporaty object, will be removed soon
    """
    def __init__(self, colormap):
        self.name = colormap['name']
        self.normalization = colormap['normalization']
        self.autoscale = colormap['autoscale']
        self.vmin = colormap['vmin']
        self.vmax = colormap['vmax']

        # for now only deal with matplotlib colorbar
        from silx.gui.plot import Colors
        cmap = Colors.getMPLColormap(self.name)
        print(type(cmap))
        import matplotlib.cm
        norm = matplotlib.colors.Normalize(0, 255)
        self.scalarMappable = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)

    def getColor(self, val):
        color = self.scalarMappable.to_rgba(val*255)
        return qt.QColor(color[0]*255, color[1]*255, color[2]*255)


class TickBar(qt.QWidget):
    """Bar grouping the tickes displayed

    :param ticks: values to be displayed. All values will be displayed in
        equidistance positions. If only one, will be presented at the center
        of the bar.
        If two will be displayed at the bottom and up positions
    :param parent: the Qt parent if any
    """
    def __init__(self, ticks, parent=None):
        super(TickBar, self).__init__(parent)
        self.ticks = ticks
        self.__buildGUI()       

    def __buildGUI(self):
        self.setLayout(qt.QVBoxLayout())

        for iTick, tick in enumerate(reversed(self.ticks)):
            alignement = qt.Qt.AlignCenter
            if len(self.ticks) > 1:
                if iTick is 0:
                    alignement = qt.Qt.AlignTop
                if iTick is len(self.ticks)-1:
                    alignement = qt.Qt.AlignBottom

            tickWidget = qt.QLabel(text=(str(tick) + '-'), parent=self)
            tickWidget.layout().setContentsMargins(0, 0, 0, 0)
            tickWidget.setAlignment(alignement)
            # insert because we are in top-bottom reference and not bottom-top
            self.layout().addWidget(tickWidget)

        self.setSizePolicy(qt.QSizePolicy.Minimum, qt.QSizePolicy.Expanding)
        self.layout().setContentsMargins(0, 0, 0, 0)

