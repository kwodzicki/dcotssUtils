from qtpy.QtWidgets import QMainWindow, QWidget, QVBoxLayout

from .version import __version__
from .widgets import Clock, HeightConverter
  
class MainWindow( QMainWindow ):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    #self.setGeometry(0, 0, 500, 50)
    self.setWindowTitle( f'DCOTSS Utils v{__version__}' )
    clock  = Clock()
    height = HeightConverter()

    layout = QVBoxLayout()
    layout.addWidget( clock )
    layout.addWidget( height )

    main = QWidget()
    main.setLayout( layout )

    self.setCentralWidget( main )
    self.show()
