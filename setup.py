from setuptools import setup, find_packages

setup(name='jodel_api',
      version='1.0',
      description='Unoffical Python Interface to the Jodel API Edit',
      url='https://github.com/nborrmann/jodel_api',
      author='Nils Borrmann',
      author_email='n.borrmann@googlemail.com',
      license='MIT',
      install_requires=['requests'],
      package_dir={'': 'src'},
      py_modules=['jodel_api'],
      setup_requires=['pytest-runner', ],
      tests_require=['pytest', ],
      zip_safe=False)
