import logging

import re
from datetime import datetime, timedelta
from itertools import chain

from qtpy.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure
from matplotlib.patches import Patch

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

def flip(items, ncol):
  """Flip data for legend so fills across row instead of down column"""

  return chain(*[items[i::ncol] for i in range(ncol)])

def convert2Percent(val):
  """
  Convert fractional string value to percent value

  """

  if FLOAT.match( val ):                                                        # If val matches the FLOAT regex pattern
    return str(int(float(val)*100))                                             # Convert val to float, multiply by 100, convert to int, convert to string
  return val                                                                    # Just return val

def parseRecord(fields, record):
  """
  Parse information from shapefile record

  Get information such as issue datetime, expire datetime, colors, etc
  from a recond in the shape file

  Arguments:
    fields (list) : Field names
    record (list) : Record information

  Returns:
    tuple : starting datetime, ending datetime, issued datetime, dict of 
      other informaiton

  """

  start = end = issued = None                                                   # Initialize start, end, and issued to None
  out = {}                                                                      # Emtpy dict
  for ID, field in enumerate( fields ):                                         # Iterate over all fields
    key = None                                                                  # Set key to None by default
    val = record[ID-1]                                                          # Set val to record that corresponds with field
    if field == 'VALID':                                                        # If field is VALID
      start = datetime.strptime(val, DATEFMT)                                   # Parse start time
    elif field == 'EXPIRE':
      end = datetime.strptime(val, DATEFMT)                                     # Parse end time
    elif field == 'ISSUE':
      issued = datetime.strptime(val, DATEFMT)                                  # Parse issued time
    elif field == 'LABEL':
      key = 'label'                                                             # Set key value
      val = convert2Percent( val )                                              # Update val value
    elif field == 'stroke':
      key = 'edgecolor'                                                         # Set key val
    elif field == 'fill':
      key = 'facecolor'                                                         # Set key val
    if key:                                                                     # If the key is set
      out[key] = val                                                            # Add value to the out dict

  label = out.get('label', None)
  if label == 'SIGN':
    out.update( {'fill' : False, 'hatch' : '..', 'linestyle' : '--'} )

  return start, end, issued, out                                                # Return values

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



class SPCWidget( SPC_Shapefiles, QWidget ):

  PLOT_OPTS    = {
    'Categorical'   : {'ncol' : 3},
    'Probabilistic' : {'ncol' : 6, 'minProb' : 5},
    'Tornado'       : {'ncol' : 8, 'minProb' : 2},
    'Wind'          : {'ncol' : 6, 'minProb' : 5},
    'Hail'          : {'ncol' : 6, 'minProb' : 5}
  }

  """Widget for displaying SPC Outlook maps"""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    

    self.ax           = None                                                    # Will be used to reference map axes later
    self.artists      = []                                                      # List to store all matploblib artists that will be updated
    self.dayButtons   = {}                                                      # Dictionary to hold references to buttons to change outlook day
    self.catButtons   = {}                                                      # Dictionary to store references to buttons that will change outlook type (categorical, tornado, etc.)

    labelFont = self.font()                                                     # Get font for self
    labelFont.setPointSize(28)                                                  # Update size
    labelFont.setBold(True)                                                     # Set bold

    self.dateLabel = QLabel()                                                   # Main Outlook banner with issued date and outlook day
    self.dateLabel.setFont( labelFont )                                         # Set font
    self.dateLabel.setAlignment( Qt.AlignCenter )                               # Set alignment to center

    canvas = self._initCanvas()                                                 # Initialize the plot canvas; draws base map
    navBar = NavigationToolbar( canvas, self )                                  # Add matploblib toolbar to map

    self.dayWidget = QWidget()                                                  # Make a widget
    layout         = QGridLayout()                                              # Define a grid layout
    layout.setColumnStretch(1, 10)                                              # Set middle column stretch to large number
    self.dayWidget.setLayout( layout )                                          # Set widget layout

    self.catWidget = QWidget()                                                  # Initialize widget
    layout         = QHBoxLayout()                                              # Initialize layout
    self.catWidget.setLayout( layout )                                          # Set widget layout

    self.currentDay  = 1                                                        # Set current day to day one (1); this will trigger the _updateCatWidget method

    layout = QVBoxLayout()                                                      # Layout for top widget
    layout.setAlignment( Qt.AlignHCenter )                                      # Set alignment to center in horizontal
    layout.addWidget( self.dayWidget )                                          # Add widgets to layout
    layout.addWidget( self.dateLabel )
    layout.addWidget( self.catWidget )
    layout.addWidget( canvas )
    layout.addWidget( navBar )

    self.setLayout( layout )                                                    # Apply layout to self

    self.show()                                                                 # Show

    self._timer = QTimer()                                                      # Initialize timer
    self._timer.timeout.connect( self.updateOutlook )                           # Run updateOutlook method on timer time out
    self._timer.start( 1000 * 60 * 5 )                                          # Start timer with 5 minute run time

  # Property for valid start time of outlook; used to return in 'fancy' format
  @property
  def start(self):
    return self._start.strftime( '%H%MZ %a %m/%d' )
  @start.setter
  def start(self, val):
    self._start = val

  # Property for valid end time of outlook; used to return in 'fancy' format
  @property
  def end(self):
    return self._end.strftime( '%H%MZ %a %m/%d' )
  @end.setter
  def end(self, val):
    self._end = val

  # Property for issued time of outlook
  @property
  def issued(self):
    return self._issued.strftime( '%H%MZ %m/%d/%Y' )                            # Return issued time as fancy format
  @issued.setter
  def issued(self, val):
    if not isinstance(val, datetime):                                           # If input value is NOT datetime
      return                                                                    # Return
    self._issued = val                                                          # Update hidden issued
    if (val.minute % 30) > 0:                                                   # If minutes NOT multiple of 30
      val += timedelta(minutes=30)                                              # Increment time by 30 minutes
      val = val.replace(minute = 30 if val.minute >= 30 else 0)                 # Set mintues to 0 or 30 based on new minuets

    outlook = 'Convective' if self.currentDay < 3 else 'Severe Thunderstorm' 
    label   = val.strftime('%b %d, %Y %H%M UTC')                                # Start building new label text with fancy date
    label   = f'{label} Day {self.currentDay} {outlook} Outlook'                # Add more text to label text
    self.dateLabel.setText( label )                                             # Update the dateLabel text

  @property
  def outlookType(self):
    return self._outlookType                                                    # Return hidden outlook type
  @outlookType.setter
  def outlookType(self, val):
    self._outlookType = val                                                     # Update hidden outlook type
    for key, val in self.catButtons.items():
      val.setChecked( key == self._outlookType )
    self._draw()                                                                # Redraw map

  @property
  def currentDay(self):
    return self._currentDay
  @currentDay.setter
  def currentDay(self, val):
    if not isinstance(val, int): return
    self._currentDay = val                                                      # Update current day
    layout = self.dayWidget.layout()                                            # Get layout from dayWidget
    for i in range( len(layout) ):                                              # Iterate over all elements in layout
      layout.itemAt(i).widget().deleteLater()                                   # Delete each object

    if self.currentDay > 1:                                                     # If current day greater than one (1)
      button = QPushButton( f'Day {self.currentDay-1} Outlook' )                # Add button to go back one (1) day
      button.clicked.connect( self._dayBackward )                               # Connect the _dayBackward method
      layout.addWidget( button, 0, 0 )                                          # Add widget to first row, first column
    if self.currentDay < 3:                                                     # If current day less than 3
      button = QPushButton( f'Day {self.currentDay+1} Outlook' )                # Add button to go forward one (1) day
      button.clicked.connect( self._dayForward )                                # Connec the _dayForward method
      layout.addWidget( button, 0, 2 )                                          # Add widget to first row, third column

    self._updateCatWidget()                                                     # Call the _updateCatWidget method

  def _dayForward(self):
    """Increment outlook day one (1) day"""

    self.currentDay += 1

  def _dayBackward(self):
    """Decncrement outlook day one (1) day"""

    self.currentDay -= 1

  def _on_outlookType_Select(self, cat):
    """Method connected to outlook type buttons"""

    self.outlookType = cat                                                      # Change the outlook type

  def _initCanvas(self):
    canvas      = FigureCanvas( Figure( figsize = (10,8), tight_layout=True ) ) # Initialize figure canvas
    self.ax     = canvas.figure.add_subplot( projection = ccrs.LambertConformal() )# Initialize map axes

    shpfilename = shpreader.natural_earth(resolution=RESOLUTION,
                                          category='cultural',
                                          name='admin_0_countries')             # Get path to cartopy shape file file cultural boundaries
    reader = shpreader.Reader(shpfilename)                                      # Open the shape file
    extent = Polygon.from_bounds( EXTENT[0], EXTENT[2], EXTENT[1], EXTENT[3] )  # Generate polygon using the extent of the map
    for country in reader.records():                                            # Iterate over each country in the shape file records
      if country.geometry.intersects( extent ):                                 # If the geometry of the country intersects the map domain
        if country.attributes['NAME'] != 'United States of America':            # If the name of the country is NOT the USA
          geo = country.geometry                                                # Get country geometry
          if not isinstance( geo, (tuple, list) ): geo = [geo]                  # If the geometry is NOT a list or tuple, convert to list
          self.ax.add_geometries(geo, ccrs.PlateCarree(),
                            facecolor = NOT_USA, zorder=1)                      # Color in the country
    reader.close()                                                              # Close the shape file

    self.ax.add_feature( cfeature.OCEAN.with_scale(RESOLUTION), color = WATER)  # Color oceans
    self.ax.add_feature( cfeature.LAKES.with_scale(RESOLUTION), color = WATER)  # Color lakes
    self.ax.add_feature( cfeature.STATES.with_scale(RESOLUTION), linewidth = 0.5)# Show state borders
    self.ax.coastlines( resolution = RESOLUTION, linewidth = 0.5 )              # Show coastlines
    self.ax.set_extent( EXTENT )                                                # SEt the map extent
    self.timeInfoText = self.ax.text(0.025, 0.025, ' ', 
      transform       = self.ax.transAxes,
      zorder          = 10, 
      backgroundcolor = 'white' )                                               # Initialize a text object that will display the vaild/issed date information

    return canvas                                                               # Return the figure canvas
    
  def _updateCatWidget(self):
    """
    Update widget for changing outlook type

    On a given outlook day, there are a few different outlook types; i.e.,
    Categorical, Tornado, etc. The widget created by this method holds
    the various buttons to change the outlook type

    """

    self.log.debug( 'Updating the outlook type widget' )
    layout = self.catWidget.layout()                                            # Get layout from widget
    for key in list(self.catButtons.keys()):                                    # Iterate over all keys in the catButtons attribute
      self.catButtons.pop( key ).deleteLater()                                  # Pop key from dictionary and remove from the gui

    for i, key in enumerate( self[ self.currentDay ] ):                         # Iterate over all keys in current day
      self.log.debug( f'Adding button: {key}' )
      button = QPushButton( key )                                               # Create button for current day
      button.setCheckable( True )                                               # Set checkable
      button.clicked.connect(
        lambda state, arg = key: self._on_outlookType_Select( arg )
      )                                                                         # Connect method to run on button click
      layout.addWidget( button )                                                # Add button to widget layout
      self.catButtons[key] = button                                             # Add button to the catButtons dictioanry
      if i == 0:                                                                # If first button
        self.outlookType = key                                                  # Set the outlook type to type of key; this will trigger draw of map

  def _draw( self, **kwargs ):
    """
    Update the map

    The outlookType and currentDay attributes are used to determine
    how the map is to be draw.
    """

    day           = kwargs.pop('day', self.currentDay)
    shapeFileInfo = getattr( self, self.outlookType )
    if day not in shapeFileInfo:
      return
    shapeFileInfo = shapeFileInfo[day]

    self.log.info( f'Drawing {self.outlookType} for day : {day}' )

    opts = self.PLOT_OPTS.get( self.outlookType, {} )
    for key, val in opts.items():
      if key not in kwargs:
        kwargs[key] = val
    minProb = kwargs.pop('minProb', '')

    while len(self.artists) > 0:
      self.artists.pop().remove()

    self.log.debug('Reading data from shapefile')
    with ShapeReader( **shapeFileInfo ) as shp:
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
        handles = []                                                            # Handles for legend
        for record in shp.shapeRecords():
          self.start, self.end, self.issued, info = parseRecord(fields, record.record)
          poly  = PolygonPatch( record.shape.__geo_interface__, **info,
                    alpha     = 0.7, 
                    zorder    = 5,  
                    linewidth = 1.5,
                    transform = ccrs.PlateCarree())
          self.artists.append( self.ax.add_patch( poly ) )
          handles.append( Patch( facecolor=info.get('facecolor', None),
                                 edgecolor=info.get('edgecolor', None),
                                 label    =info.get('label',     None) ) )      # Build object for legend; this is done to ensure that any hatched areas on map appear as filled box in legend

        if self.outlookType.startswith('Cat'):                                  # If workin got Categorical
          handles = flip(handles, kwargs['ncol'])                               # Flip the handles
        legend = self.ax.legend( handles=handles, **kwargs,
              loc        = 'lower right',
              framealpha = 1, 
              title      = self.getLegendTitle()
        )                                                                       # Build legend
        legend.set_zorder( 10 )                                                 # Set zorder of legend os is ALWAYS on top
        self.artists.append( legend )                                           # Append legend artist to the list of artists

      self.timeInfoText.set_text( self.getTimeInfo() )                          # Get time info and use it to set the time info text label
  
    self.ax.figure.canvas.draw_idle()                                           # Trigger redraw of the map

  def getTimeInfo(self):
    """Construct outlook time information text"""

    txt = [
      f'SPC DAY {self.currentDay} {self.outlookType.upper()} OUTLOOK',
      f'ISSUED: {self.issued}',
      f'VALID: {self.start} - {self.end}']
    return '\n'.join( txt )

  def getLegendTitle(self):
    """Construct title for legend based on outlook type"""

    if self.outlookType.startswith( 'Cat' ):
      return 'Categorical Outlook Legend'
    elif self.outlookType.startswith( 'Prob' ):
      return 'Total Severe Probability Legend (in %)'
    return f'{self.outlookType} Probability Legend (in %)'

  def updateOutlook(self):
    """Download lastest data and refresh maps"""

    self.getLatest()
    self._draw()
