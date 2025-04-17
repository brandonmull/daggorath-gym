from .paths import GYM_PATH, ROOT_PATH, EMU_PATH
from .config import *
from .funcs import *

# Make these paths available when importing the package
__all__ = ['config', 'funcs', 'GYM_PATH', 'EMU_PATH', 'ROOT_PATH']

# Daggorath Gym Environment
from .main import DaggorathEnv