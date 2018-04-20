from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

d = generate_distutils_setup(
     packages=['posture_execution', 'posture_execution.interfaces'],
     package_dir={'': 'src'}
)

setup(**d)

