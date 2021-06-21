import logging

from datetime import datetime, timedelta
from math import ceil

from qtpy.QtWidgets import  QLabel
from qtpy.QtGui import QFont
from qtpy.QtCore import QTimer

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

    self.setText( f'{gmt} UTC<br>{lt} LT' )
