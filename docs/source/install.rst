===================
Install ML4Chem
===================

You can install ML4Chem from ``pip``, ``conda`` or ``sources``.

Pip
------

You can install ML4Chem and all its dependencies like NumPy, Pandas, Dask,
and so on that are necessary for deploying this package. For a global
installation, execute::

   pip install "ml4chem"    

If you want to install the application for your user::

   pip install --user ml4chem


Conda
--------

For conda installation, execute::

    conda install ml4chem


Sources
--------

1. Clone the application::

    git clone https://github.com/muammar/ml4chem

2. Install the requirements::

    cd ml4chem
    pip install -r requirements.txt

3. After requirements are installed, you can proceed to add ``ml4chem`` to
   your ``PYTHONPATH`` and ``PATH`` (to use the ``ml4chem`` command line
   tool). Add the following to your ``.bashrc`` or ``.zshrc``::

    PYTHOPATH=/path/to/ml4chem:$PYTHONPATH
    PATH=/path/to/ml4chem/bin:$PATH
