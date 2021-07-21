import os
import datetime as dt

from qtpy.QtWidgets import QWidget, QLabel, QVBoxLayout
from qtpy.QtCore import QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvas
import matplotlib.dates as mplDates
from matplotlib.figure import Figure

import numpy as np

from metpy.calc import dewpoint_from_relative_humidity, wind_components
from metpy.units import units

from ..htmlUtils import getNWSForecastData

DEFAULT_KWARGS = {'marker' : 'o', 'linestyle' : '-', 'linewidth' : 1, 'markersize' : 2}
DEGSYM         = u'\xb0'

def calc_mslp(t, p, h):
    return p * (1 - (0.0065 * h) / (t + 0.0065 * h + 273.15)) ** (-5.257)

def roundUp( val, n=None ):
  tmp = round(val, n)
  if tmp < val: tmp += 10**(-n)
  return tmp

def roundDown( val, n=None ):
  tmp = round(val, n)
  if tmp > val: tmp -= 10**(-n)
  return tmp
 
# Make meteogram plot
class Meteogram( FigureCanvas ):
  """ Plot a time series of meteorological data from a particular station as a
  meteogram with standard variables to visualize, including thermodynamic,
  kinematic, and pressure. The functions below control the plotting of each
  variable.
  TO DO: Make the subplot creation dynamic so the number of rows is not
  static as it is currently. """

  def __init__(self, data = None, fig = None, time=None, axis=0):
    """
    Required input:
        fig: figure object
        dates: array of dates corresponding to the data
        probeid: ID of the station
    Optional Input:
        time: Time the data is to be plotted
        axis: number that controls the new axis to be plotted (FOR FUTURE)
    """
    fig = Figure( figsize=(10,8) ) if fig is None else fig

    super().__init__( fig )
    if not time:
        time      = dt.datetime.utcnow()
    self.axis_num = 0

    self.thermo = None
    self.winds  = None
    self.probs  = None

    if data is not None: self.replot( data )
#    self.dates = mpl.dates.date2num(dates)
#    self.time = time.strftime('%Y-%m-%d %H:%M UTC')
#    self.title = f'Latest Ob Time: {self.time}\nProbe ID: {probeid}'
    self.show()

  @property
  def dates(self):
    return self._dates

  @dates.setter
  def dates(self, val):
    self._dates = mplDates.date2num( val )
    self.start  = val[ 0]
    self.end    = val[-1]

  def addGrid(self, axis, **kwargs):
    axis.grid(
      b         = kwargs.get('b',         True), 
      which     = kwargs.get('which',     'both'),
      axis      = kwargs.get('axis',      'both'),
      color     = kwargs.get('color',     'gray'),
      linestyle = kwargs.get('linestyle', '-'),
      linewidth = kwargs.get('linewidth', 0.5)
    )

  def addLegend( self, axis ):
    axis.legend(loc='upper right', ncol=3, prop={'size': 9})

  def addDates( self, axis ):
    axis.xaxis.set_major_formatter(
      mplDates.DateFormatter('%m/%d/%H')
  )

  def addAnnotations(self, subplot, fmt, *variables):
    while len(subplot['text']) > 0:
      subplot['text'].pop().remove()
    for var in variables: 
      for i in range(2, len(var), 3):
        subplot['text'].append(
          subplot['axes'].annotate(
            fmt.format( var[i] ), (self.dates[i], var[i]),
            fontsize = 'small',
            horizontalalignment = 'center'
          )
        )

  def _init_winds(self, ws, wsmax, u, v):
    ax         = self.figure.add_subplot(4, 1, 2)
    self.winds = {'axes' : ax, 'text' : []}
    self.addGrid( ax )

    ln1  = ax.plot( self.dates, ws,    color='purple',   label='Wind Speed',  **DEFAULT_KWARGS)[0]
    ln2  = ax.plot( self.dates, wsmax, color='darkblue', label='Gust',        **DEFAULT_KWARGS)[0]
    ln3  = ax.barbs(self.dates, ws, u, v )
    #ax.set_ylabel( f'Wind Speed{os.linesep}({ws.units})', multialignment='center')
    self.addLegend( ax )
    self.addDates(  ax )

    self.winds.update( {'wind' : ln1, 'barbs' : ln3, 'gust' : ln2} )

  def plot_winds(self, ws, wd, wsmax):
      """
      Required input:
          ws: Wind speeds 
          wd: Wind direction 
          wsmax: Wind gust
      Optional Input:
          plot_range: Data range for making figure (list of (min,max,step))
      """

      ws    = ws.to('knots')
      wsmax = wsmax.to('knots')
      u, v  = wind_components( ws, wd ) 

      ws    = ws.magnitude
      wsmax = wsmax.magnitude

      pMax = np.nanmax( wsmax )
      if not np.isfinite( pMax ):
        pMax = ws.max()
      prange = [-10, roundUp(pMax, -1)+10, 10]

      # PLOT WIND SPEED AND WIND DIRECTION
      if self.winds is None:
        self._init_winds(ws, wsmax, u, v)
      else:
        self.winds['wind' ].set_data( self.dates, ws )
        try:
          self.winds['barbs'].remove()#set_data( self.dates, ws, u, v)
        except:
          pass
        else:
          self.winds['barbs'] = self.winds['axes'].barbs(self.dates, ws, u, v )
        self.winds['gust' ].set_data( self.dates, wsmax)
      self.addAnnotations( self.winds, '{:0.0f}', ws )

      self.winds['axes'].set_ylim( *prange )


  def _init_thermo( self, t, td, heat ):
    ax          = self.figure.add_subplot(4, 1, 1 )#, sharex=self.ax1)
    self.thermo = {'axes' : ax, 'text' : []}
    self.addGrid( ax )

    ln1 = ax.plot(self.dates, t,    color='red',    label=f'Temperature ({DEGSYM}F)', **DEFAULT_KWARGS)[0]
    ln2 = ax.plot(self.dates, td,   color='green',  label=f'Dewpoint ({DEGSYM}F)',    **DEFAULT_KWARGS)[0]
    ln3 = ax.plot(self.dates, heat, color='orange', label=f'Heat Index ({DEGSYM}F)',  **DEFAULT_KWARGS)[0]
    #ax.set_ylabel(f'Temperature{os.linesep}({t.units})', multialignment='center')
    self.addDates( ax )
    self.addLegend( ax )

    self.thermo.update( {'t' : ln1, 'td' : ln2, 'heat' : ln3} )

  def plot_thermo(self, t, td, heat):
    """
    Required input:
        T: Temperature 
        TD: Dewpoint
    Optional Input:
        plot_range: Data range for making figure (list of (min,max,step))
    """

    # Force units to degrees F
    t    = t.to(    units.degF ).magnitude 
    td   = td.to(   units.degF ).magnitude
    heat = heat.to( units.degF ).magnitude

    pMin, pMax = np.inf, -np.inf
    for i in [t, td, heat]:
      iMin = np.nanmin( i )
      iMax = np.nanmax( i )
      if iMin < pMin: pMin = iMin 
      if iMax > pMax: pMax = iMax
    prange = [roundDown(pMin, -1), roundUp(pMax, -1)+10, 10]

    # PLOT TEMPERATURE AND DEWPOINT
    if self.thermo is None:
      self._init_thermo( t, td, heat )
    else:
      self.thermo['t'   ].set_data(self.dates, t)
      self.thermo['td'  ].set_data(self.dates, td)
      self.thermo['heat'].set_data(self.dates, heat)
    self.addAnnotations( self.thermo, '{:0.0f}'+DEGSYM, t, td, heat )

    self.thermo['axes'].set_ylim( *prange )


  def _init_probs( self, rh, precip, sky):
    ax          = self.figure.add_subplot(4, 1, 3 )#, sharex=self.ax1)
    self.probs  = {'axes' : ax, 'text' : []}
    self.addGrid( ax )

    ln1 = ax.plot(self.dates, rh,     color='green', label='Relative Humidity',       **DEFAULT_KWARGS)[0]
    ln2 = ax.plot(self.dates, precip, color='brown', label='Precipitation Potential', **DEFAULT_KWARGS)[0]
    ln3 = ax.plot(self.dates, sky,    color='blue',  label='Sky Cover',               **DEFAULT_KWARGS)[0]

    #ax.set_ylabel( f'Probability{os.linesep}(%)', multialignment='center')
    self.addDates(  ax )
    self.addLegend( ax )

    self.probs.update( {'rh' : ln1, 'precip' : ln2, 'sky' : ln3} )


  def plot_probs(self, rh, precip, sky):

    rh     = rh.to(     units.percent ).magnitude
    precip = precip.to( units.percent ).magnitude
    sky    = sky.to(    units.percent ).magnitude

    if self.probs is None:
      self._init_probs( rh, precip, sky )
    else:
      self.probs['rh'    ].set_data(self.dates, rh)
      self.probs['precip'].set_data(self.dates, precip)
      self.probs['sky'   ].set_data(self.dates, sky)

    self.addAnnotations( self.probs, '{:0.0f}%', rh, precip, sky )

    self.probs['axes'].set_ylim( -10, 120, 20 ) 


  def replot(self, data):
    self.dates = data['date']
    self.figure.suptitle( data['location'], fontsize=12 )
    self.plot_thermo( data['Temperature'], data['Dewpoint'], data['Heat Index'] )
    self.plot_winds( data['Surface Wind'], data['Wind Dir'], data['Gust'] )
    self.plot_probs( data['Relative Humidity'], data['Precipitation Potential'], data['Sky Cover'] )

    for info in [self.thermo, self.winds, self.probs]:
      info['axes'].set_xlim(self.start, self.end)
    self.figure.tight_layout()
    self.draw()

class NWS_Forecast( QWidget ):

  def __init__(self, *args, **kwargs):
    data     = kwargs.pop('data', None)
    interval = kwargs.pop('interval', 10.0 )
    super().__init__(*args, **kwargs)

    self.fig      = Meteogram( data = data )
    self.update   = QLabel()
    self.download = QLabel()

    self._update()

    self._timer = QTimer()
    self._timer.timeout.connect( self._update )
    self._timer.start( interval * 1000 * 60  )
    #self._timer.start( 1000 )
    
    layout = QVBoxLayout()
    layout.addWidget( self.fig )
    layout.addWidget( self.update )
    layout.addWidget( self.download )

    self.setLayout( layout )
    self.show()

  def _update(self):
    try:
      data = getNWSForecastData()
    except Exception as err:
      print( f'Failed to get data: {err}' )
      return
    self.fig.replot( data )
    utc = dt.datetime.utcnow().strftime( '%I:%M %p UTC %b %d, %Y' )
    self.update.setText( data['update'] )
    self.download.setText( f'Download time: {utc}' )

