- [Home](https://flopy.readthedocs.io/en/stable/index.html)
- [API Reference](https://flopy.readthedocs.io/en/stable/code.html)
- flopy.modflow.mfwel module

* * *

# flopy.modflow.mfwel module [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html\#module-flopy.modflow.mfwel "Permalink to this heading")

mfwel module. Contains the ModflowWel class. Note that the user can access
the ModflowWel class as flopy.modflow.ModflowWel.

Additional information for this MODFLOW package can be found at the [Online\\
MODFLOW Guide](https://water.usgs.gov/ogw/modflow/MODFLOW-2005-Guide/wel.html).

_class_ ModflowWel( _model_, _ipakcb=None_, _stress\_period\_data=None_, _dtype=None_, _extension='wel'_, _options=None_, _binary=False_, _unitnumber=None_, _filenames=None_, _add\_package=True_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel "Permalink to this definition")

Bases: [`Package`](https://flopy.readthedocs.io/en/stable/source/flopy.pakbase.html#flopy.pakbase.Package "flopy.pakbase.Package")

MODFLOW Well Package Class.

Parameters:

- **model** ( _model object_) – The model object (of type [`flopy.modflow.mf.Modflow`](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mf.html#flopy.modflow.mf.Modflow "flopy.modflow.mf.Modflow")) to which
this package will be added.

- **ipakcb** ( [_int_](https://docs.python.org/3/library/functions.html#int "(in Python v3.13)") _,_ _optional_) – Toggles whether cell-by-cell budget data should be saved. If None or zero,
budget data will not be saved (default is None).

- **stress\_period\_data** ( [_list_](https://docs.python.org/3/library/stdtypes.html#list "(in Python v3.13)") _,_ _recarray_ _,_ _dataframe_ _or_ _dictionary_ _of_ _boundaries._) –

Each well is defined through definition of
layer (int), row (int), column (int), flux (float).
The simplest form is a dictionary with a lists of boundaries for each
stress period, where each list of boundaries itself is a list of
boundaries. Indices of the dictionary are the numbers of the stress
period. This gives the form of:


> stress\_period\_data =
> {0: \[\
>\
> > \[lay, row, col, flux\],\
> > \[lay, row, col, flux\],\
> > \[lay, row, col, flux\]\
> > \],
>
> 1: \[\
>\
> \[lay, row, col, flux\],\
> \[lay, row, col, flux\],\
> \[lay, row, col, flux\]\
> \], …
>
> kper:
>
> \[\
> \[lay, row, col, flux\],\
> \[lay, row, col, flux\],\
> \[lay, row, col, flux\]\
> \]
>
> }


Note that if the number of lists is smaller than the number of stress
periods, then the last list of wells will apply until the end of the
simulation. Full details of all options to specify stress\_period\_data
can be found in the flopy3 boundaries Notebook in the basic
subdirectory of the examples directory

- **dtype** ( _custom datatype_ _of_ _stress\_period\_data._) – If None the default well datatype will be applied (default is None).

- **extension** ( _string_) – Filename extension (default is ‘wel’)

- **options** ( [_list_](https://docs.python.org/3/library/stdtypes.html#list "(in Python v3.13)") _of_ _strings_) – Package options (default is None).

- **unitnumber** ( [_int_](https://docs.python.org/3/library/functions.html#int "(in Python v3.13)")) – File unit number (default is None).

- **filenames** ( [_str_](https://docs.python.org/3/library/stdtypes.html#str "(in Python v3.13)") _or_ [_list_](https://docs.python.org/3/library/stdtypes.html#list "(in Python v3.13)") _of_ [_str_](https://docs.python.org/3/library/stdtypes.html#str "(in Python v3.13)")) – Filenames to use for the package and the output files. If
filenames=None the package name will be created using the model name
and package extension and the cbc output name will be created using
the model name and .cbc extension (for example, modflowtest.cbc),
if ipakcb is a number greater than zero. If a single string is passed
the package will be set to the string and cbc output names will be
created using the model name and .cbc extension, if ipakcb is a
number greater than zero. To define the names for all package files
(input and output) the length of the list of strings should be 2.
Default is None.

- **add\_package** ( [_bool_](https://docs.python.org/3/library/functions.html#bool "(in Python v3.13)")) – Flag to add the initialised package object to the parent model object.
Default is True.


mxactw [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.mxactw "Permalink to this definition")

Maximum number of wells for a stress period. This is calculated
automatically by FloPy based on the information in
stress\_period\_data.

Type:

[int](https://docs.python.org/3/library/functions.html#int "(in Python v3.13)")

Notes

Parameters are not supported in FloPy.

Examples

```
>>> import flopy
>>> m = flopy.modflow.Modflow()
>>> lrcq = {0:[[2, 3, 4, -100.]], 1:[[2, 3, 4, -100.]]}
>>> wel = flopy.modflow.ModflowWel(m, stress_period_data=lrcq)

```

add\_record( _kper_, _index_, _values_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel.add_record) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.add_record "Permalink to this definition")_static_ get\_default\_dtype( _structured=True_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel.get_default_dtype) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.get_default_dtype "Permalink to this definition")_static_ get\_empty( _ncells=0_, _aux\_names=None_, _structured=True_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel.get_empty) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.get_empty "Permalink to this definition")_classmethod_ load( _f_, _model_, _nper=None_, _ext\_unit\_dict=None_, _check=True_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel.load) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.load "Permalink to this definition")

Load an existing package.

Parameters:

- **f** ( _filename_ _or_ _file handle_) – File to load.

- **model** ( _model object_) – The model object (of type [`flopy.modflow.mf.Modflow`](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mf.html#flopy.modflow.mf.Modflow "flopy.modflow.mf.Modflow")) to
which this package will be added.

- **nper** ( [_int_](https://docs.python.org/3/library/functions.html#int "(in Python v3.13)")) – The number of stress periods. If nper is None, then nper will be
obtained from the model object. (default is None).

- **ext\_unit\_dict** ( _dictionary_ _,_ _optional_) – If the arrays in the file are specified using EXTERNAL,
or older style array control records, then f should be a file
handle. In this case ext\_unit\_dict is required, which can be
constructed using the function
[`flopy.utils.mfreadnam.parsenamefile`](https://flopy.readthedocs.io/en/stable/source/flopy.utils.mfreadnam.html#flopy.utils.mfreadnam.parsenamefile "flopy.utils.mfreadnam.parsenamefile").


Returns:

**wel** – ModflowWel object.

Return type:

ModflowWel object

Examples

```
>>> import flopy
>>> m = flopy.modflow.Modflow()
>>> wel = flopy.modflow.ModflowWel.load('test.wel', m)

```

write\_file( _f=None_) [\[source\]](https://flopy.readthedocs.io/en/stable/_modules/flopy/modflow/mfwel.html#ModflowWel.write_file) [](https://flopy.readthedocs.io/en/stable/source/flopy.modflow.mfwel.html#flopy.modflow.mfwel.ModflowWel.write_file "Permalink to this definition")

Write the package file.

Parameters:

**f** ( [_str_](https://docs.python.org/3/library/stdtypes.html#str "(in Python v3.13)") _,_ _optional_) – file name

Return type:

None