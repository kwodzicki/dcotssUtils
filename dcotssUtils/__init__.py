import logging
LOG = logging.getLogger(__name__)
LOG.setLevel( logging.DEBUG )
LOG.addHandler( logging.StreamHandler() )
LOG.handlers[0].setLevel( logging.DEBUG )

KM2KFT = 3.28084 # 1 km is 3.2 kft
