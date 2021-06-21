from qtpy.QtWidgets import QWidget, QLineEdit, QLabel, QVBoxLayout
from qtpy.QtCore import QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
#import matplotlib.dates as mplDates

import numpy 

from metpy.calc import wind_components
from metpy.io import parse_metar_to_dataframe
from metpy.units import units 
from metpy.plots import StationPlot, StationPlotLayout, sky_cover

METAR_UNITS = {'air_temperature'       : units.degC,
               'dew_point_temperature' : units.degC }

def parseMETAR( METAR ):
  metar = parse_metar_to_dataframe( METAR )
  u, v  = wind_components( metar['wind_speed'    ].values * units('knots'),
                           metar['wind_direction'].values * units.degree )
  data = {'u_wind' : u, 'v_wind' : v}
  for var, unit in METAR_UNITS.items():
    data[var] = metar[var] * unit

  key = 'cloud_coverage'
  data[key] = metar[key].values

  return data

class StationFigure( FigureCanvas ):
  STATION_LAYOUT = StationPlotLayout()
  STATION_LAYOUT.add_barb('u_wind', 'v_wind', 'knot',        length=15, linewidth=5)
  STATION_LAYOUT.add_value( (-4,  4), 'air_temperature',       fmt='.1f', units='degF')
  STATION_LAYOUT.add_value( (-4, -4), 'dew_point_temperature', fmt='.1f', units='degF')
  STATION_LAYOUT.add_symbol( (0, 0), 'cloud_coverage', sky_cover, fontsize=28)

  def __init__(self, fig = None):
    fig = Figure( figsize=(10,8) ) if fig is None else fig
    super().__init__( fig )

    self.axes = self.figure.add_subplot(1, 1, 1)
    self.axes.set_xlim(0, 10)
    self.axes.set_ylim(0, 10)
    self.axes.axis('off')
    #self.station = None
    self.station = StationPlot( self.axes, [5], [5], fontsize = 12 )

  def plotData( self, data ):
    #if self.station is not None:
    #  self.station.remove()
    print( 'updating' )
    self.STATION_LAYOUT.plot( self.station, data )
    self.draw()

class StationWidget( QWidget):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.stationID   = QLineEdit()
    self.stationPlot = StationFigure()
    self.time        = QLabel()

    self.updateStation()

    layout = QVBoxLayout()
    layout.addWidget( self.stationID )
    layout.addWidget( self.stationPlot )
    layout.addWidget( self.time )
    
    self.setLayout( layout )
    self.show()

    self._timer = QTimer()
    self._timer.timeout.connect( self.updateStation )
    self._timer.start( 1000 * 60 * 30 )

  def updateStation(self):
    station = self.stationID.text()
    METAR = 'KSLN 211953Z 35012G26KT 10SM FEW075 28/08 A3004 RMK AO2 PK WND 35026/1922 SLP158 T02830083'
    data  = parseMETAR( METAR )
    
    #data  = {'temp_c'     : numpy.random.random( (1,) ) * 20 * units.degC, 
    #         'dewpoint_c' : numpy.random.random( (1,) ) * 20 * units.degC, 
    #         'u_wind'     : numpy.random.random( (1,) ) * 10 * units.mph, 
    #         'v_wind'     : numpy.random.random( (1,) ) * 10 * units.mph,
    #         'cloud_fraction' : 5}
    self.stationPlot.plotData( data )
 
