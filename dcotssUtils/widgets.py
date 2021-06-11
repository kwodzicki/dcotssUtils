import logging

from datetime import datetime, timedelta
from math import ceil

from qtpy.QtWidgets import  QWidget, QLabel, QLineEdit, QGridLayout
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt, QTimer

from . import KM2KFT 
from .atmos import StandardAtmos

ALTFONT   = QFont( 'courier new', 14)

CLOCKFONT = QFont('courier new', 36)
CLOCKFONT.setBold( True )

class Clock( QLabel ):
  FMT = '%H:%M:%S'
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setFont( CLOCKFONT )
    self._offset = ceil( (datetime.utcnow() - datetime.now()).total_seconds()/3600 )
    self._offset = timedelta( hours = self._offset ) 
    self._updateClock()

    self._timer = QTimer()
    self._timer.timeout.connect( self._updateClock )
    self._timer.start(1000)  # every 1,000 millisecond

  def _updateClock(self):
    gmt = datetime.utcnow()
    lt  = gmt - self._offset

    gmt = gmt.strftime( self.FMT )
    lt  =  lt.strftime( self.FMT )

    self.setText( f'{gmt} GMT<br>{lt} LT' )

class HeightConverter( QWidget ):
  """
  Widget for converting from different altitude units

  This widget contains entry boxes for km, kft, hPa, and potential temperature
  that are editable and will udpate all other fields using the standard 
  atmosphere.

  Atmospheric temperature values are also show, but can not be used to
  determine heights because of inversion in startosphere.

  """

  FMT    = '{:10.4f}'

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.log     = logging.getLogger(__name__)
    self.atmos   = StandardAtmos()
    self.oldVals = {}

    # Generate label objecs
    mainLabel    = QLabel('Altitude Converter')
    kmLabel      = QLabel('km')
    kftLabel     = QLabel('kft')
    hPaLabel     = QLabel('hPa')
    tempLabel    = QLabel('K')
    thetaLabel   = QLabel('<p>&Theta;</p>')

    # Generate text extry widgets
    self.km      = QLineEdit()
    self.kft     = QLineEdit()
    self.hPa     = QLineEdit()
    self.temp    = QLineEdit()
    self.theta   = QLineEdit()

    # Set font for text entry widgets
    self.km.setFont(    ALTFONT )
    self.kft.setFont(   ALTFONT )
    self.hPa.setFont(   ALTFONT )
    self.temp.setFont(  ALTFONT )
    self.theta.setFont( ALTFONT )

    # Make the temperature box read only
    self.temp.setReadOnly( True )

    # Connect methods to run when <Enter>/<Return> is pressed
    self.km.returnPressed.connect(    self.kmChanged )
    self.kft.returnPressed.connect(   self.kftChanged )
    self.hPa.returnPressed.connect(   self.hPaChanged )
    self.theta.returnPressed.connect( self.thetaChanged )

    # Set initial height to 0 km and update all other fields
    self.km.setText( '0' )
    self.kmChanged()

    # Initialize layout and add widgets to the layout 
    layout = QGridLayout()
    layout.addWidget( mainLabel,  0, 0, 1, 2, Qt.AlignCenter )
    layout.addWidget( kmLabel,    1, 0, 1, 1)
    layout.addWidget( self.km,    1, 1, 1, 1)
    layout.addWidget( kftLabel,   2, 0, 1, 1)
    layout.addWidget( self.kft,   2, 1, 1, 1)
    layout.addWidget( hPaLabel,   3, 0, 1, 1)
    layout.addWidget( self.hPa,   3, 1, 1, 1)
    layout.addWidget( tempLabel,  4, 0, 1, 1)
    layout.addWidget( self.temp,  4, 1, 1, 1)
    layout.addWidget( thetaLabel, 5, 0, 1, 1)
    layout.addWidget( self.theta, 5, 1, 1, 1)

    # Set layout for the QWidget and show the widget
    self.setLayout( layout )
    self.show()

  def kmChanged(self, *args):
    """Run when value in km QLineEdit changes"""

    try: 
      val = float( self.km.text() )
    except Exception as err:
      self.log.error( err )
      self.updateLabels( )
      return

    try:
      Pa, K, theta, d = self.atmos.fromKilometers( val )
    except Exception as err:
      self.log.error( f'Failed to convert altitude: {err}' )
      self.updateLabels( )
    else:
      self.updateLabels( km=val, hPa=Pa/100.0, temp=K, theta=theta)

  def kftChanged(self, *args):
    """Run when value in kft QLineEdit changes"""

    try: 
      val = float( self.kft.text() )
    except Exception as err:
      self.log.error( err )
      self.updateLabels( )
      return

    try:
      Pa, K, theta, d = self.atmos.fromKilofeet( val )
    except Exception as err:
      self.log.error( f'Failed to convert altitude: {err}' )
      self.updateLabels( )
    else:
      self.updateLabels( kft=val, hPa=Pa/100.0, temp=K, theta=theta)

  def hPaChanged(self, *args):
    """Run when value in hPa QLineEdit changes"""

    try: 
      val = float( self.hPa.text() )
    except Exception as err:
      self.log.error( err )
      self.updateLabels( )
      return
    
    try:
      m, K, theta, d = self.atmos.fromhPa( Pa )
    except Exception as err:
      self.log.error( f'Failed to convert altitude: {err}' )
      self.updateLabels( )
    else:
      self.updateLabels( km=m/1.0e3, hPa=val, temp=K, theta=theta)

  def thetaChanged(self, *args):
    """Run when value in theta QLineEdit changes"""
  
    try: 
      val = float( self.theta.text() )
    except Exception as err:
      self.log.error( err )
      self.updateLabels( )
      return

    try: 
      Pa, m, K, d = self.atmos.fromTheta( val )
    except Exception as err: 
      self.log.error( f'Failed to convert altitude: {err}' )
      self.updateLabels( )
    else:
      self.updateLabels( km=m/1.0e3, hPa=Pa/100.0, temp=K, theta=val)

  def updateLabels(self, **kwargs):
    """
    Update labels in the altitude converter

    Parameters:
    **kwargs
        Keywords who's names match those of the QLineEdit atributes 
        holding the corresponding values. For example, to update the
        line with km data in it, you would call:
            self.udpateLabels( km = new_km )

    """

    if len(kwargs) == 0:                                                        # If no keywords, use old values
      kwargs = self.oldVals
    elif 'kft' not in kwargs:                                                   # If kft NOT in args, then must computer from km
      kwargs['kft'] = kwargs['km'] * KM2KFT                                     # Computer kft from km
    else:                                                                       # Else, assume km is NOT in args
      kwargs['km']  = kwargs['kft'] / KM2KFT                                    # Compute km from kft

    for key, val in kwargs.items():                                             # Iterate over all keywords
      self.oldVals[key] = val                                                   # If made this far, then update the oldVals to current values
      txt = self.FMT.format(val)                                                # Format text
      getattr(self, key).setText( txt )                                         # Get corresponding class attribute and call setText method
