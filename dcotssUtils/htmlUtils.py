from datetime import datetime

from urllib.request import urlopen

import numpy
from metpy.units import units

from bs4 import BeautifulSoup as BS


URL = 'https://forecast.weather.gov/MapClick.php?lat=38.78&lon=-97.6442&unit=0&lg=english&FcstType=digital'

WINDDIR = { 
    'NW'  : 315.0,
    'NNW' : 337.5,
    'N'   :   0.0,
    'NNE' :  22.5,
    'NE'  :  45.0,

    'ENE' :  67.5,
    'E'   :  90.0,
    'ESE' : 112.5,

    'SE'  : 135.0,
    'SSE' : 157.5,
    'S'   : 180.0,
    'SSW' : 202.5,
    'SW'  : 225.0,

    'WSW' : 247.5,
    'W'   : 270.0,
    'WNW' : 292.5,
}

def downloadPage( url = URL ):
  try:
    res = urlopen( url )
  except Exception as err:
    print(err)
    return None

  data = None

  try:
    data = res.read()
  except Exception as err:
    print( err )

  try:
    res.close()
  except:
    pass

  return data

def makeDate( txt, year ):
  tmp = list( map( int, txt.split('/') ) )
  return datetime( year, tmp[0], tmp[1] )

def parseDates( cols, data, refDate ):
  key = 'date'
  for i in range( 1, len(cols) ):
    txt = cols[i].text
    if txt != '':
      newDate = makeDate( txt, refDate.year )
      if newDate.month < refDate.month:
        newDate = newDate.replace(year = newDate.year+1)
      refDate = newDate
    data[ key ].append( refDate ) 
  return refDate

def parseHours( cols, data, offset ):
  key = 'date'
  for i in range( 1, len(cols) ):
    hour = int( cols[i].text )
    data[key][ offset ] = data[key][offset].replace( hour = hour ) 
    offset += 1
  
  return offset

def parseVar( cols, data ):
  txt       = cols[0].text
  var, unit = getVarName_Units( txt )
  isWindDir = 'wind dir' in var.lower()

  if var not in data:
    data[var] = {'units' : unit, 'values' : []}

  var = data[var]
  key = 'values'

  for col in cols[1:]:
    txt = col.text
    if isWindDir:
      var[key].append( WINDDIR.get( txt, numpy.nan) ) 
    elif txt.isdigit():
      var[key].append( int(txt) )
    elif txt == '':
      var[key].append( numpy.nan )

def getVarName_Units( txt ):
  tmp = txt.split('(')
  if len(tmp) == 2:
    var  = tmp[0].strip()
    unit = units.parse_units( tmp[1][:-1] )
  else:
    var  = txt
    if 'wind dir' in txt.lower():
      unit = units.parse_units('degree')
    else:
      unit = 1.0
  return var, unit

def parseData( table, refDate, loc, update ):
  data    = { 'date' : [], 'location' : loc, 'update' : update }
  offset  = 0

  for row in table.find_all('tr'):
    cols = row.find_all('td')
    txt = cols[0].text.lower()
    if 'date' in txt:
      refDate = parseDates( cols, data, refDate )
    elif 'hour' in txt:
      offset = parseHours( cols, data, offset )
    elif txt != '':
      parseVar( cols, data )

  for key, val in data.items():
    if isinstance(val, dict):
      vals = numpy.asarray( val['values'] ) * val['units']
      data[key] = vals

  gst = 'Gust'
  srf = 'Surface Wind'
  if gst in data and srf in data:
    if not hasattr( data[gst], 'units' ):
      if hasattr( data[srf], 'units' ):
        data[gst] = data[gst] * data[srf].units

  return data

def getRefDate( col, fmt = '%H%p %a, %b %d %Y' ):
  """
  Find and parse date from given column

  Extract the selected date from an options menu and parse
  into a datetime object.

  Parameters
  ----------
  col : Tag
      A BeautifulSoup column element
  fmt : str
      Format for parsing the date string using datetime

  Returns
  -------
  datetime
      Datetime object

  """

  date = col.find_all( 'option', selected = True )
  if len(date) !=1: 
    raise Exception('Failed to find selected reference date!')
  txt = date[0].text
  return datetime.strptime( txt, fmt )

def getNWSData( url = URL, parser = 'html.parser' ):
  html = downloadPage( url )
  if html is None: return html

  loc    = ''
  update = ''

  soup   = BS( html, parser )
  tables = soup.find_all('table')
  for table in tables:
    for row in table.find_all('tr'):
      for col in row.find_all('td'):
        txt = col.text.lower()
        if 'point forecast' in txt:
          loc = ':'.join( col.text.split(':')[1:] )  
        elif 'last update' in txt:
          update = col.text
        elif 'period starting:' in txt:
          refDate = getRefDate( col )
        elif txt == 'date':                                          # We found a table with good data
          return parseData( table, refDate, loc, update ) 


if __name__ == "__main__":
  print( getNWSData() )

 
     
