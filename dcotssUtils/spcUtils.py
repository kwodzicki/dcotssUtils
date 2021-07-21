import logging

import atexit

import re
from time import sleep
from datetime import datetime
from os.path import splitext
from io import BytesIO
from zipfile import ZipFile

from threading import Lock
 
from .htmlUtils import urlJoin, downloadPage

BASE_URL = 'https://www.spc.noaa.gov/'
LOCK     = Lock()

def threadSafe( func ):
  def wrappedThreadSafe(*args, **kwargs):
    with LOCK:
      return func( *args, **kwargs )
  return wrappedThreadSafe

def findShapefile( day ):
  url  = urlJoin( BASE_URL, 'products', 'outlook', f'day{day}otlk.html' )
  try:
    html = downloadPage( url ).decode()
  except:
    return None

  link = [ f for f in re.findall('href="([^"]+)"', html) if f.endswith('.zip')]
  if len(link) == 1:
    return downloadPage( urlJoin( BASE_URL, link[0] ) )
  return None


class SPC_Shapefiles( object ):
  def __init__(self, *args, **kwargs):
    super().__init__( *args, **kwargs )

    self.log            = logging.getLogger(__name__)
    self._categorical   = {}
    self._probabilistic = {}
    self._tornado       = {}
    self._wind          = {}
    self._hail          = {}

    self.getLatest()
 
  @property
  @threadSafe
  def Categorical(self):
    return self._categorical

  @property
  @threadSafe
  def Probabilistic(self):
    return self._probabilistic

  @property
  @threadSafe
  def Tornado(self):
    return self._tornado

  @property
  @threadSafe
  def Wind(self):
    return self._wind

  @property
  @threadSafe
  def Hail(self):
    return self._hail

  def __getitem__(self, index):
    out = {}
    if index in self._categorical:
      out['Categorical'  ] = self._categorical[   index]    
    if index in self._probabilistic:
      out['Probabilistic'] = self._probabilistic[ index]    
    if index in self._tornado:
      out['Tornado'      ] = self._tornado[       index]    
    if index in self._wind:
      out['Wind'         ] = self._wind[          index]    
    if index in self._hail:
      out['Hail'         ] = self._hail[          index]    
    return out

  @threadSafe
  def getLatest( self ):
    self.log.debug('Getting latest data from SPC')
    for day in range(1, 4): 
      data = findShapefile( day )
      if data is None:
        self.log.warning( f'Failed to get SPC Shapefile archive for outlook day : {day}' )
        continue 

      with ZipFile( BytesIO( data ) ) as zz:
        fnames = zz.namelist()
        for fname in fnames:
          if fname.endswith('.shp'):
            ref = splitext( fname )[0]
            shp = fname
            dbf = f'{ref}.dbf'
            if dbf in fnames:
              tmp = {'shp' : BytesIO(), 
                     'dbf' : BytesIO()}
              tmp['shp'].write( zz.read( shp) )
              tmp['dbf'].write( zz.read( dbf) )
              if ref.endswith('_cat'):
                self._categorical[ day ] = tmp  
              elif ref.endswith('_prob'):
                self._probabilistic[ day ] = tmp
              elif ref.endswith('_torn'):
                self._tornado[ day ] = tmp  
              elif ref.endswith('_wind'):
                self._wind[ day ] = tmp  
              elif ref.endswith('_hail'):
                self._hail[ day ] = tmp
 
