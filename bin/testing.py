#!/usr/bin/env python3
import matplotlib.pyplot as plt
from dcotssUtils.nws_forecast import getNWSData, Meteogram

if __name__ == "__main__":
  data      = getNWSData()

  fig       = plt.figure(figsize=(10, 8))
  meteogram = Meteogram( fig, data )
  plt.show()
