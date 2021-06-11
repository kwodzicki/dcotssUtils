import logging

import math

from . import KM2KFT

class StandardAtmos():
  g  =    9.80665
  R  =  287.00
  Cp = 1005.7   # From AMS Glossary

  def __init__(self):
    self.log = logging.getLogger(__name__)

    self.a      = [-0.0065, 0, 0.001, 0.0028]
    self.h      = [11000, 20000, 32000, 47000]
    self.p0     = 101325
    self.t0     =  288.15
    self.theta0 = self.t2theta( self.t0, self.p0 )
    self.p      = []
    self.t      = []
    self.theta  = [] 
    prevh       = 0

    for i in range(4):
      pres, temp, theta, den = self.fromMeters( self.h[i] )      
      self.p.append( pres )
      self.t.append( temp )
      self.theta.append( theta )

  def t2theta(self, temp, pres):
    """Get potential temperature from air temperature and pressure"""

    return temp * (1.0e5 / pres)**(self.R / self.Cp)

  def theta2t(self, temp, pres):
    """Get temperature from potential temperature and pressure"""

    return temp / (1.0e5 / pres)**(self.R / self.Cp)

  def density(self, temp, pres):
    """Get density from air temperature and pressure"""

    return pres / ( self.R * temp )

  def cal(self, p0, t0, a, h0, h1):
    """Used to calculate pressure and air temperature at give altitude"""

    if a != 0:
      t1 = t0 + a * (h1 - h0)
      p1 = p0 * (t1 / t0) ** (-self.g / a / self.R)
    else:
      t1 = t0
      p1 = p0 * math.exp(-self.g / self.R / t0 * (h1 - h0))
    return p1, t1

  def fromKilometers(self, alt):
    """Same as fromMeters(), but input is in units of km"""

    return self.fromMeters( alt * 1.0e3 )

  def fromKilofeet(self, alt):
    """Same as fromMeters(), but input is in units of kft"""

    return self.fromMeters( alt / KM2KFT * 1.0e3 )

  def fromMeters(self, alt):  
    """
    Get pressure, temperature, potential temperature, and density from altitude 

    Parameters
    ----------
    alt : float:
       Altitude in m to get information for 

    Returns
    -------
    float
        Pressure in Pa
    float
        Air temperatue in K
    float
        Potential temperature in K
    float
        Density in kg m**-3
 
    """

    if alt < 0 or alt > 47000:
      raise Exception("altitude must be in [0, 47000] m")
    p0    = self.p0 
    t0    = self.t0
    prevh = 0
    for i in range(4):
      if alt <= self.h[i]:
        pres, temp = self.cal(p0, t0, self.a[i], prevh, alt)
        theta      = self.t2theta( temp, pres )
        return pres, temp, theta, self.density(temp, pres) 
      else:
        p0, t0 = self.cal(p0, t0, self.a[i], prevh, self.h[i])
        prevh = self.h[i]
  
  def fromhPa(self, pres):
    """Same as fromPa(), but input is in units of hPa"""

    return self.fromPa( pres * 1.0e2 )

  def fromPa(self, pres):
    """
    Get altitude, temperature, potential temperature and density from pressure 

    Parameters
    ----------
    press : float:
       Pressure in Pa to get information for 

    Returns
    -------
    float
        Altitude in m
    float
        Air temperatue in K
    float
        Potential temperature in K
    float
        Density in kg m**-3
 
    """

    if pres > self.p0 or pres < self.p[-1]:
      raise Exception( f'pressure must be in [{self.p0}, {self.p[-1]}] Pa' ) 

    for i in range( len(self.p) ):
      if pres > self.p[i]:                                                      # If pressure is greater, then closer to ground
        if i == 0:                                                              # If first iteration
          h0, h1 = 0, self.h[i]                                                 # h0 is ground
        else:                                                                   # Else, use surronding values
          h0, h1 = self.h[i-1:i+1]
        break
    mid = (h0+h1)/2.0                                                       # Get middle of layer
    p, t, theta, d = self.fromMeters( mid )                                        # Get pressure at layer

    i = 50
    while abs(p-pres) > 0.05 and i > 0:
      if pres > p:                                                          # Requested pressure is between layer bottom and layer middle 
        h1 = mid
      else:                                                                 # Reauested layer is between layer middle and layer top
        h0 = mid 
      mid = (h0+h1)/2.0                                                       # Get middle of layer
      p, t, theta, d = self.fromMeters( mid )                                        # Get pressure at layer
      i -= 1

    return mid, t, theta, d

  def fromTheta(self, thetaIn):
    """
    Get pressure, altitude, temperature and density from potential temperature

    Parameters
    ----------
    thetaIn : float:
        Potential temperature to get level in standard atmosphere for

    Returns
    -------
    float
        Pressure in Pa
    float
        Altitude in m
    float
        Air temperatue in K
    float
        Density in kg m**-3
 
    """

    if thetaIn < self.theta0 or thetaIn > self.theta[-1]: 
      raise Exception( f'theta must be in [{self.theta0}, {self.theta[-1]}] K ' ) 

    for i in range( len(self.t) ):
      if thetaIn < self.theta[i]:                                               # If pressure is greater, then closer to ground
        if i == 0:                                                              # If first iteration
          h0, h1 = 0, self.h[i]                                                 # h0 is ground
        else:                                                                   # Else, use surronding values
          h0, h1 = self.h[i-1:i+1]
        break
    mid = (h0+h1)/2.0                                                           # Get middle of layer
    p, t, theta, d = self.fromMeters( mid )                                     # Get pressure at layer

    i = 50
    while abs(theta-thetaIn) > 0.05 and i > 0:
      if thetaIn < theta:                                                       # Requested pressure is between layer bottom and layer middle 
        h1 = mid
      else:                                                                     # Reauested layer is between layer middle and layer top
        h0 = mid 
      mid = (h0+h1)/2.0                                                         # Get middle of layer
      p, t, theta, d = self.fromMeters( mid )                                   # Get pressure at layer
      i -= 1

    return p, mid, t, d
