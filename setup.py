from setuptools import setup, find_packages
import os

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    long_description = f.read()

setup(name='jodel_api',
      version='1.2.3',
      description='Unoffical Python Interface to the Jodel API',
      long_description=long_description,
      url='https://github.com/nborrmann/jodel_api',
      author='Nils Borrmann',
      author_email='n.borrmann@googlemail.com',
      license='MIT',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords='jodel',
      package_dir={'': 'src'},
      install_requires=['requests', 'future', 'mock', 'varint', 'protobuf'],
      packages=find_packages('src'),
      setup_requires=['pytest-runner', ],
      tests_require=['pytest', 'flaky'],
      zip_safe=False)
