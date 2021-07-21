import logging

import re
from datetime import datetime, timedelta

from qtpy.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

from shapefile import Reader
from shapely.geometry import Polygon
from descartes import PolygonPatch

from ..spcUtils import SPC_Shapefiles
  
EXTENT     = [-120, -72, 20, 50]
RESOLUTION = '50m'
WATER      = [0.78823529, 0.8745098 , 0.94509804]
NOT_USA    = [0.75] * 3

FLOAT      = re.compile( '\d+\.?\d*' )
DATEFMT    = '%Y%m%d%H%M'

class ShapeReader( Reader ):
  def close(self):
    """
    Overload close method so that it doesn't close files

    In this code, we don't want the the files to close because we may
    read them again. We do NOT need to seek back to beginning of file
    because seek to beginnging is done on class initialization, so would
    be redundant.

    """

    pass

def convert2Percent(val):
  if FLOAT.match( val ):
    return str(int(float(val)*100))
  return val

def parseRecord(fields, record):
  start = end = issued = None
  out = {}
  for ID, field in enumerate( fields ):
    key = None
    val = record[ID-1]
    if field == 'VALID':
      start = datetime.strptime(val, DATEFMT) 
    elif field == 'EXPIRE':
      end = datetime.strptime(val, DATEFMT) 
    elif field == 'ISSUE':
      issued = datetime.strptime(val, DATEFMT) 
    elif field == 'LABEL':
      key = 'label'
      val = convert2Percent( val )
    elif field == 'stroke':
      key = 'edgecolor'
    elif field == 'fill':
      key = 'facecolor'
    if key:
      out[key] = val
  return start, end, issued, out


class SPCWidget( SPC_Shapefiles, QWidget ):
  PROB_MINPROB = 5
  TORN_MINPROB = 2
  WIND_MINPROB = 5
  HAIL_MINPROB = 5

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    self._currentFunc = None
    self.outlookType  = None
    self.currentDay   = 1

    self.ax           = None
    self.artists      = []

    self.dayButtons   = {}
    self.dayWidget    = None
    self._initDayWidget()

    canvas = self._initCanvas()
    navBar = NavigationToolbar( canvas, self )

    self.catButtons = {}
    self.catWidget  = None
    self._initCatWidget()

    layout = QVBoxLayout()
    layout.addWidget( self.dayWidget )
    layout.addWidget( self.catWidget )
    layout.addWidget( canvas )
    layout.addWidget( navBar )

    self.setLayout( layout )
    self.show()

    self._timer = QTimer()
    self._timer.timeout.connect( self.updateOutlook )
    self._timer.start( 1000 * 60 * 5 )

  @property
  def start(self):
    return self._start.strftime( '%H%MZ %a %m/%d' )
  @start.setter
  def start(self, val):
    self._start = val

  @property
  def end(self):
    return self._end.strftime( '%H%MZ %a %m/%d' )
  @end.setter
  def end(self, val):
    self._end = val

  @property
  def issued(self):
    return self._issued.strftime( '%H%MZ %m/%d/%Y' )
  @issued.setter
  def issued(self, val):
    if not isinstance(val, datetime):
      return
    self._issued = val
    if (val.minute % 30) > 0:
      val += timedelta(minutes=30)
      val = val.replace(minute = 30 if val.minute >= 30 else 0)

    label = val.strftime('%b %d, %Y %H%M UTC')
    label = f'{label} Day {self.currentDay} Convective Outlook'
    self.dateLabel.setText( label )

  @property
  def currentFunc(self):
    return self._currentFunc
  @currentFunc.setter
  def currentFunc(self, val):
    self._currentFunc = getattr( self, f'draw{val}' )
    

  def updateOutlook(self):
    self.getLatest()    
    self.currentFunc()

  def _initCanvas(self):
    canvas        = FigureCanvas( Figure( figsize = (10,8), tight_layout=True ) )
    self.ax       = canvas.figure.add_subplot( projection = ccrs.LambertConformal() )

    shpfilename = shpreader.natural_earth(resolution=RESOLUTION,
                                          category='cultural',
                                          name='admin_0_countries')
    reader = shpreader.Reader(shpfilename)
    extent = Polygon.from_bounds( EXTENT[0], EXTENT[2], EXTENT[1], EXTENT[3] ) 
    for country in reader.records():
      if country.geometry.intersects( extent ):
        if country.attributes['NAME'] != 'United States of America':
          geo = country.geometry
          if not isinstance( geo, (tuple, list) ): geo = [geo]
          self.ax.add_geometries(geo, ccrs.PlateCarree(),
                            facecolor = NOT_USA, zorder=1)
    reader.close()

    self.ax.add_feature( cfeature.OCEAN.with_scale(RESOLUTION), color = WATER)
    self.ax.add_feature( cfeature.LAKES.with_scale(RESOLUTION), color = WATER)
    self.ax.add_feature( cfeature.STATES.with_scale(RESOLUTION), linewidth = 0.5)
    self.ax.coastlines( resolution = RESOLUTION, linewidth = 0.5 ) 
    self.ax.set_extent( EXTENT )   
    self.timeInfoText = self.ax.text(EXTENT[0]+0.5, EXTENT[2]+0.5, ' ', 
      transform       = ccrs.PlateCarree(),
      backgroundcolor = 'white' )

    return canvas

  def _dayForward(self):
    self.currentDay += 1
    self._dayChange()
    self._initCatWidget()

  def _dayBackward(self):
    self.currentDay -= 1
    self._dayChange()
    self._initCatWidget()
    
  def _dayChange(self):
    layout = self.dayWidget.layout()
    for i in range( len(layout) ):
      widget = layout.itemAt(i).widget()
      if isinstance(widget, QPushButton):
        widget.deleteLater()      

    if self.currentDay > 1:
      button = QPushButton( f'Day {self.currentDay-1} Outlook' )
      button.clicked.connect( self._dayBackward )      
      layout.addWidget( button, 0, 0 )
    if self.currentDay < 3:
      button = QPushButton( f'Day {self.currentDay+1} Outlook' )
      button.clicked.connect( self._dayForward )      
      layout.addWidget( button, 0, 2 )

  def _initDayWidget(self):

    labelFont = self.font()
    labelFont.setPointSize(28)
    labelFont.setBold(True)

    self.dateLabel = QLabel()
    self.dateLabel.setFont( labelFont )

    layout  = QGridLayout()
    layout.setColumnStretch(1, 10)
    layout.addWidget( self.dateLabel, 1, 0, 1, 3, alignment=Qt.AlignCenter )

    self.dayWidget = QWidget()
    self.dayWidget.setLayout( layout )

    self._dayChange()

  def _changeCat(self, cat):
    for key, val in self.catButtons.items():
      if key != cat:
        val.setChecked( False )
    self.currentFunc = cat
    self.currentFunc()

  def _initCatWidget(self):
    if self.catWidget is None:
      layout  = QHBoxLayout()
      self.catWidget = QWidget()
      self.catWidget.setLayout( layout )
    else:
      layout = self.catWidget.layout()
      for key in list(self.catButtons.keys()):
        self.catButtons.pop( key ).deleteLater()
      #for i in range( len(layout) ):
      #  layout.itemAt(i).widget().deleteLater()      

    for i, key in enumerate( self[ self.currentDay ] ):
      button = QPushButton( key )
      button.setCheckable( True )
      button.clicked.connect( lambda state, arg = key: self._changeCat( arg ) )
      layout.addWidget( button )
      if i == 0: 
        self.currentFunc = key
        button.setChecked(True)
        
      self.catButtons[key] = button

    self.drawCategorical()

  def _draw( self, shp=None, dbf=None, **kwargs ):
    minProb = kwargs.pop('minProb', None)
    labelID = edgeID = faceID = None

    while len(self.artists) > 0:
      self.artists.pop().remove()

    self.log.debug('Reading data from shapefile')
    with ShapeReader( shp=shp, dbf=dbf ) as shp:
      fields = [field[0] for field in shp.fields]

      if 'LABEL' not in fields:
        self.log.debug( 'No polygons to draw' )
        txt = f'LESS THAN {minProb}% ALL AREAS' if minProb else 'LOW RISK'
        txt = self.ax.annotate( txt, (0.5, 0.5), 
                xycoords            = 'figure fraction', 
                verticalalignment   = 'center',
                horizontalalignment = 'center',
                fontsize            = 'xx-large') 

        self.artists.append( txt )
      else: 
        self.log.debug('Drawing shapes')
        for record in shp.shapeRecords():
          self.start, self.end, self.issued, info = parseRecord(fields, record.record)
          poly  = PolygonPatch( record.shape.__geo_interface__, **info,
                    alpha     = 0.7, 
                    zorder    = 10,  
                    linewidth = 1.5,
                    transform = ccrs.PlateCarree())
          self.artists.append( self.ax.add_patch( poly ) )
        self.artists.append(
            self.ax.legend( loc = 'lower right', framealpha=1, **kwargs )
        )
      self.timeInfoText.set_text( self.getTimeInfo() )
  
    self.log.debug('Updating plot')
    self.ax.figure.canvas.draw_idle()

  def getTimeInfo(self):
    txt = [
      f'SPC DAY {self.currentDay} {self.outlookType} OUTLOOK',
      f'ISSUED: {self.issued}',
      f'VALID: {self.start} - {self.end}']
    return '\n'.join( txt )

  def drawCategorical( self, *args, **kwargs ):
    day = kwargs.get('day', self.currentDay)
    self.outlookType = 'CATEGORICAL'
    self.log.debug( f'Drawing categorical for day : {day}' )
    if day in self.categorical:
      self._draw( **self.categorical[day], ncol = 3, title='Categorical Outlook Legend')

  def drawProbabilistic( self, *args, **kwargs ):
    day = kwargs.get('day', self.currentDay)
    self.outlookType = 'PROBABILISTIC'
    self.log.debug( f'Drawing probabilistic for day : {day}' )
    if day in self.probabilistic:
      self._draw( **self.probabilistic[day], 
        minProb = self.PROB_MINPROB, ncol = 6, title='Total Severe Probability Legend (in %)')

  def drawTornado( self, *args, **kwargs):
    day = kwargs.get('day', self.currentDay)
    self.outlookType = 'TORNADO'
    self.log.debug( f'Drawing tornado for day : {day}' )
    if day in self.tornado:
      self._draw( **self.tornado[day], 
        minProb = self.TORN_MINPROB, ncol = 8, title='Tornado Probability Legend (in %)')

  def drawWind( self, *args, **kwargs):
    day = kwargs.get('day', self.currentDay)
    self.outlookType = 'WIND'
    self.log.debug( f'Drawing wind for day : {day}' )
    if day in self.wind:
      self._draw( **self.wind[day],
        minProb = self.WIND_MINPROB, ncol = 6, title='Wind Probability Legend (in %)' )

  def drawHail( self, *args, **kwargs):
    day = kwargs.get('day', self.currentDay)
    self.outlookType = 'HAIL'
    self.log.debug( f'Drawing hail for day : {day}' )
    if day in self.hail:
      self._draw( **self.hail[day],
        minProb = self.HAIL_MINPROB, ncol = 6, title='Hail Probability Legend (in %)' )


