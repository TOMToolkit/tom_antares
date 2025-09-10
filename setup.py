from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tom-antares',
    description='Antares broker module for the TOM Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://tomtoolkit.github.io',
    author='TOM Toolkit Project',
    author_email='llindstrom@lco.global, dmcollom@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics'
    ],
    keywords=['tomtoolkit', 'astronomy', 'astrophysics', 'cosmology', 'science', 'fits', 'observatory', 'antares'],
    packages=find_packages(),
    use_scm_version=True,  # use_scm_version and setup_requires setuptools_scm are required for automated releases
    setup_requires=['setuptools_scm', 'wheel'],
    install_requires=[
        'tomtoolkit>=2.12,<3.0',
        'antares-client>=1.9,<2.0',
        'elasticsearch-dsl>=7.3,<7.5'
    ],
    extras_require={
        'test': ['factory_boy>=3.1,<3.4']
    },
    include_package_data=True,
)
