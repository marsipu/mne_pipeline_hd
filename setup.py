from setuptools import setup, find_packages

setup(name='mne_pipeline_hd',
      version='0.1',
      description='A pipeline for brain-data analysis with MNE-Python',
      url='https://github.com/marsipu/mne_pipeline_hd.git',
      author='marsipu',
      author_email='martin.schulz@stud.uni-heidelberg.de',
      license='GPL-3.0',
      packages=find_packages(exclude=['docs', 'tests']))
