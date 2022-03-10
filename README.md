Pipeline status: [![validation](https://github.com/openfido/loadshape/actions/workflows/main.yml/badge.svg)](https://github.com/openfido/loadshape/actions/workflows/main.yml)

OpenFIDO loadshape pipeline
===========================

The loadshape pipeline analyses AMI data and generates the most common
loadshapes present. Hourly loadshapes are generated for each season weekday and weekend. The AMI data is then grouped using the specified group method (by default K-Means Clustering).

The loadshape data may be optionally output to GLM files so that loads
can be attached to network models.

PIPELINE
--------

Recommended pipeline settings:

| Setting                 | Recommended value
| ----------------------- | -----------------
| Pipeline name           | Loadshape
| Description             | AMI loadshape analysis and generation
| DockerHub Repository    | debian:11
| Git Clone URL (https)   | https://github.com/openfido/loadshape
| Repository Branch       | main
| Entrypoint Script (.sh) | openfido.sh

INPUTS
------

** Required inputs **

`config.csv` - The run configuration file is required (see CONFIGURATION below).

*AMI data* - The AMI data (required) as a CSV file (may be compressed). The name of this file must be specified in the `config.csv` using the `INPUT_CSV` parameter. The required columns include:

| Column | Content
| ------ | -------
| 0      | Date and time
| 1      | Meter ID
| 2      | Interval energy measurement
| 3      | Timezone specification

The date/time column may be specified in UTC or local date/time.  The name of the date/time column may be specified using the `DATETIME_COLUMN` configuration parameter in `config.csv`. The format of the date/time column is given by the `DATETIME_FORMAT` configuration parameter in `config.csv`.

The meter id column may contain any valid unique string identifier.  The name of the meter id column may be specified using the `ID_COLUMN` configuration parameter in `config.csv`.

The interval energy is measured in units of energy per hour in `kWh/h`. The name of the interval energy measurement may be changed using the `DATA_COLUMN` configuration parameter in `config.csv`.

The timezone specification is given in hours offset relative to UTC, i.e., east is positive and west is negative. The name of the timezone specification column may be changed using the `TIMEZONE_COLUMN` configuraiton parameter in `config.csv`. If this parameter is set to an empty string, the timezone is set to UTC. If UTC is used, then the timezone must be specified as UTC offset, with DST shifts, if any, e.g., -8 for PST, and -7 for PDT. If local time is used, then the timezone should specify only the DST shift, i.e., 0 for standard, and 1 for summer time. If DST is not use and the date/time data is local, the timezone column may be omitted.  At this time only Atlantic (AST/ADT), Eastern (EST/EDT), Central (CST/CDT), Mountain (MST/MDT), Pacific (PST/PDT), Alaska (AKST/AKDT), and Hawaii (HST/HDT) timezones are supported.  

** Optional Inputs **

*Load map* - An optional CSV file containing the mapping of loads to the network model. The name of this file may be specified using the `LOADS_CSV` parameter in `config.csv`. Required columns correspond to GridLAB-D load object properties:

| Property | Description
| -------- | -----------
| `meter_id` | The meter id from the AMI data
| `class`    | The object class (`load` or `triplex_load`
| `parent`   | The parent object ID (a valid network node name)
| `phases`   | The load phases (must match network node)
| `nominal_voltage` | The load nominal voltage (must match network node)
| `{power,current,impedance}_fraction_[ABC]` | The ZIP powerflow `load` fractions (only for 1, 2, or 3-phase non-split loads)
| `{power,current,impedance}_fraction_{1,2,12}` | The ZIP powerflow `triplex_load` fractions (only for single-phase split-tap loads)

If the fractions are omitted, the ZIP load is set to a unitary constant power fraction.  All other columns are copied to the loads verbatim.

OUTPUTS
-------

**Data files** (always output)

*Loadshapes* - The loadshapes are saved to the CSV file specified by the
`LOADSHAPES_CSV` configuration parameter in `config.csv`. The default filename if the parameter is not specified is `loadshapes.csv`. The rows identify each loadshape group, and the columns provide the load for each hour, daytype, and season in that loadshape. The column names use abbreviations for season and day type, i.e., season in {`win`,`spr`,`sum`,`fal`} and day type in {`wd`,`we`}, which a concatenated with the hour of day, e.g., `win_wd_0` for hour 0 of a winter weekday.

*Groups* - The groups are saved to the CSV file specifies by the `GROUPS_CSV` configuration parameter in `config.csv`.  The default filename if the parameter is not specified is `groups.csv`.  The rows identify each meter specified by the `ID_COLUMN` field in the input AMI data.

**GridLAB-D model** (optional output)

*Clock* - This model fragement contains the data range and timezone specification based on input the AMI data. This file is generated only when `CLOCK_GLM` is specified in `config.csv`.

*Schedules* - This model fragment contains the loadshape data generated as GridLAB-D schedules. This file is generated only when `SCHEDULES_GLM` is specified in `config.csv`.

*Loads* - This model fragment contains the load objects generated using scaled references to schedules. This file is generated only `LOADS_GLM` is specified in `config.csv`.  In addition, the file specified by `INPUT_MAP` is required to identify how loads are mapped to the network model.

**Plots** (optional output)

If `OUTPUT_PNG` is specified in `config.csv`, then a plot containing the loadshapes and underlying AMI data is generated.  The `config.csv` parameters `PNG_FIGSIZE` and `PNG_FONTSIZE` control figure size (in inch) and font size (in points), respectively. If omitted the defaults `10x7` and `14`, respectively.

CONFIGURATION
-------------

The following configuration parameters are supported

| Parameter | Default | Description
| --------- | ------- | -----------
| `VERBOSE`   | True    | Enables verbose output.
| `DEBUG`     | True    | Enables debug output.
| `QUIET`     | False   | Disables all output.
| `WARNING`   | True    | Enables warning output.
| *Input*
| `WORKDIR`   | `'/tmp'`  | Specifies the working directory.
| `INPUT_CSV` | `''`      | Specifies AMI input data file (REQUIRED).
| `DATETIME_COLUMN` | `'0'` | Specifies the date/time column in the AMI file.
| `ID_COLUMN` | `'1'`     | Specifies the id column in the AMI file.
| `DATA_COLUMN` | `'2'`   | Specifies the data column in the AMI file.
| `TIMEZONE_COLUMN` | `'3'` | Specifies the timezone column in the AMI file.
| `DATETIME_FORMAT` | `'%Y-%m-%d %H:%M:%S'` | Specifies the input date/time format.
| *Analysis*
| `FILL_METHOD` | `''`    | Specifies the fill method for missing data. Valid values are `'bfill'`, `'backfill'`, `'pad'`, `'ffill'`.
| `RESAMPLE` | `''` | Specifies resample method to use. Valid methods include all DataFrame aggregators.
| `AGGREGATION` | `'median'` | Group aggregation method. Valid methods include all DataFrame aggregators.
| `GROUP_METHOD` | `'kmeans'` | Grouping method. Valid method is `'kmeans'`
| `GROUP_COUNT` | `0` | Grouping count. Must be a positive number (REQUIRED).
| *Outputs*
| `LOADSHAPES_CSV` | `'loadshapes.csv'` | Specifies the loadshape file to generate.
| `GROUPS_CSV` | `'groups.csv'` | Specifies the group file to generate.
| `FLOAT_FORMAT` | `'%.4g'` | Specifies float data format.
| `SCALING` | `''` | may be `'energy'`, `'power'`, `''` means both.
| *Plotting*
| `OUTPUT_PNG` | `''` | Specifies the output PNG file name.
| `PNG_FIGSIZE` | `'10x7'` | Specifies the output PNG image size (in inches)
| `PNG_FONTSIZE` | `14` | Specifies the output PNG image font size (in points)
| *GridLAB-D*
| `LOADS_CSV` | `''`      | Specifies the load mapping file.
| `CLOCK_GLM` | `''` | Specifies the output GLM clock model fragment.
| `LOADS_GLM` | `''` | Specifies the output GLM load model fragment.
| `SCHEDULES_GLM` | `''` | Specifies the output GLM schedule model fragment.
| `LOAD_SCALE` | '1000' | Specifies the scaling of the schedule data to load (e.g., 1kVA=1000VA)

ENVIRONMENT
-----------

* `OPENFIDO_INPUT` specifies the input folder.

* `OPENFIDO_OUTPUT` specifies the output folder.

* `PWD` specifies the default working folder.

EXIT CODES
----------

The following exit codes are used:

| Exit code | Condition
| --------- | ---------
| 0         | Load shape analysis completed ok
| 1         | A fatal exception was detected
| 2         | An invalid input was received
| 3         | The loadshape analysis failed

In the event of a non-zero exit code, the `DEBUG` and `VERBOSE` configuration options in `config.csv` may be used to obtain additional information on where and why the condition occured.
