"""OpenFIDO end-use loadshape analysis

The pipeline generates loadshapes using k-means clustering analysis on AMI load data.

INPUTS
------

    config.csv (required) - control the pipeline run

    data.csv[.gz] (required) - provides the AMI data

    loads.csv (optional) - provides the GLM load models

OUTPUTS
-------

    loadshapes.csv (always generated) - provides the loadshape data

    groups.csv (always generated) - provides the mapping of meters to loadshapes

    loads.glm (generated when LOADS_GLM specified) - provides the GLM load objects

    schedules.glm (generated when SCHEDULES_GLM specified) - provides the GLM schedule data

    clock.glm (generated when CLOCK_GLM specified) - provides the GLM clock directive

    loadshapes.png (generated when LOADSHAPE_PNG specified) - provide a plot of the loadshapes

CONFIGURATION
-------------

    INPUT_CSV,ami_data.csv
    OUTPUT_CSV,loadshapes.csv
    OUTPUT_GLM,loads.glm
    DATETIME,datetime
    POWER,real_power

"""

import sys, os
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import csv

tic = dt.datetime.now()

def toc():
    t =dt.datetime.now()-tic
    return round(t.seconds + t.microseconds/1e6,3)

VERBOSE = False
DEBUG = False
QUIET = False
WARNING = True

def boolstr(x):
    try:
        return(bool(int(x)))
    except:
        x = str(x).lower()
    if x in ['yes','no','true','false']:
        return x in ['yes','true']
    else:
        raise Exception(f"{x} is not a boolean string value")

VALID_CONFIG = {
    'VERBOSE':boolstr,
    'DEBUG':boolstr,
    'QUIET':boolstr,
    'WARNING':boolstr,
    'WORKDIR':str,

    'INPUT_CSV':str,
    'DATETIME_COLUMN':str,
    'ID_COLUMN':str,
    'DATA_COLUMN':str,
    'TIMEZONE_COLUMN':str,
    'DATETIME_FORMAT':str,

    'LOADSHAPES_CSV':str,
    'GROUPS_CSV':str,
    'FLOAT_FORMAT':str,

    # 'RESAMPLE':str,
    # 'FILL_METHOD':str,
    'AGGREGATION':str,
    'GROUP_METHOD':str,
    'GROUP_COUNT':int,

    'OUTPUT_PNG':str,
    'PNG_FIGSIZE':str,
    'PNG_FONTSIZE':str,

    'LOADS_CSV':str,
    'CLOCK_GLM':str,
    'SCHEDULES_GLM':str,
    'LOADS_GLM':str,
    'LOAD_SCALE':float,
    'LOADNAME_PREFIX':str,

    'ARCHIVE_FILE':str,
    }

WORKDIR = ''
INPUT_CSV = ''
DATETIME_COLUMN = '0'
ID_COLUMN = '1'
DATA_COLUMN = '2'
TIMEZONE_COLUMN = '3'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

LOADSHAPES_CSV = 'loadshapes.csv'
GROUPS_CSV = 'groups.csv'
FLOAT_FORMAT = '%.4g'
SCALING = '' # may be 'energy','power', '' means both

FILL_METHOD = 'ffill'
RESAMPLE = ''
AGGREGATION = 'median'
GROUP_METHOD = 'kmeans'
GROUP_COUNT = 0

OUTPUT_PNG = ''
PNG_FIGSIZE = '10x7'
PNG_FONTSIZE = 14

LOADS_CSV = ''
CLOCK_GLM = ''
LOADS_GLM = ''
SCHEDULES_GLM = ''
LOAD_SCALE = 1000.0
LOADNAME_PREFIX = ''

ARCHIVE_FILE = ''

E_OK = 0
E_EXCEPTION = 1
E_INVALID = 2
E_FAILED = 3

timezones = {
    -4 : "A",
    -5 : "E",
    -6 : "C",
    -7 : "M",
    -8 : "P",
    -9 : "AK",
    -10 : "H"
}

def error(code,msg):
    if DEBUG:
        raise Exception(msg)
    elif not QUIET:
        print(f"ERROR [loadshape@{toc()}]: {msg}",file=sys.stderr,flush=True)
    exit(code)

def warning(msg):
    if WARNING:
        print(f"WARNING [loadshape@{toc()}]: {msg}",file=sys.stderr,flush=True)

def verbose(msg):
    if VERBOSE:
        print(f"VERBOSE [loadshape@{toc()}]: {msg}",file=sys.stderr,flush=True)

def debug(msg):
    if DEBUG:
        print(f"DEBUG [loadshape@{toc()}]: {msg}",file=sys.stderr,flush=True)

def to_datetime(t,format=DATETIME_FORMAT):
    if format:
        return dt.datetime.strptime(t,format)
    else:
        return dt.datetime.fromisoformat

def to_float(x,nan=np.nan):
    try:
        return np.float64(x)
    except:
        pass
    return nan

try:

    # get input directory
    OPENFIDO_INPUT = os.getenv("OPENFIDO_INPUT")
    if not OPENFIDO_INPUT:
        error(E_INVALID,"OPENFIDO_INPUT environment variable not set")
    elif not OPENFIDO_INPUT.endswith("/"):
        OPENFIDO_INPUT += "/"

    # get output directory
    OPENFIDO_OUTPUT = os.getenv("OPENFIDO_OUTPUT")
    if not OPENFIDO_OUTPUT:
        error(E_INVALID,"OPENFIDO_OUTPUT environment variable not set")
    elif not OPENFIDO_OUTPUT.endswith("/"):
        OPENFIDO_OUTPUT += "/"
    if os.listdir(OPENFIDO_OUTPUT) and OPENFIDO_OUTPUT != os.getenv("PWD")+"/examples/":
        error(E_FAILED,"output folder is not empty")

    # get pipeline configuration 
    if os.path.exists(OPENFIDO_INPUT+"config.csv"):
        with open(OPENFIDO_INPUT+"config.csv","r") as cfg:
            reader = csv.reader(cfg)
            for row in reader:
                if row and row[0] in VALID_CONFIG.keys():
                    if len(row) == 1:
                        globals()[row[0]] = None
                    elif len(row) == 2:
                        globals()[row[0]] = VALID_CONFIG[row[0]](row[1])
                    else:
                        globals()[row[0]] = row[1:]
                    debug(f"{row[0]} = {globals()[row[0]]}")
                elif row:
                    error(E_INVALID,f"config.csv: {row[0]} is not a valid configuration parameter")
    else:
        with open(OPENFIDO_OUTPUT+"config.csv","w") as f:
            for key in VALID_CONFIG.keys():
                f.write(f"{key},{globals()[key]}\n")
        warning("config.csv not found in input folder, a template has been provided in the output folder")

    # get working directory
    verbose(f"OPENFIDO_INPUT = {OPENFIDO_INPUT}")
    verbose(f"OPENFIDO_OUTPUT = {OPENFIDO_OUTPUT}")
    if not WORKDIR:
        WORKDIR = "/tmp"
    os.chdir(WORKDIR)
    verbose(f"WORKDIR = {WORKDIR}")

    verbose(f"{OPENFIDO_INPUT}config.csv found ok")
    if VERBOSE:
        for key in VALID_CONFIG.keys():
            print(f"  {key} = {globals()[key]}",file=sys.stderr)

    if LOADS_GLM:
        if LOADS_CSV:
            loads = pd.read_csv(OPENFIDO_INPUT+LOADS_CSV,dtype=str)
            verbose("loads: {0} rows x {1} columns".format(*loads.shape))
            debug(loads)
        else:
            error(E_INVALID,"cannot output GLM loads without LOADS_CSV defined")

    if INPUT_CSV:

        try: 
            time_col = int(DATETIME_COLUMN)
            data_col = int(DATA_COLUMN)
            tz_col = int(TIMEZONE_COLUMN)
            id_col = int(ID_COLUMN)
            DATETIME_COLUMN  = time_col
            DATA_COLUMN = data_col
            TIMEZONE_COLUMN = tz_col
            ID_COLUMN = id_col
        except: 
            pass

        # 
        # Load data
        #
        data = pd.read_csv(OPENFIDO_INPUT+INPUT_CSV, 
                usecols=[DATETIME_COLUMN,ID_COLUMN,DATA_COLUMN,TIMEZONE_COLUMN],
                low_memory=False,
                converters = {
                    DATETIME_COLUMN : to_datetime,
                    DATA_COLUMN : to_float,
                    ID_COLUMN : str,
                    TIMEZONE_COLUMN : int,
                    },
                )
        verbose("data: {0} rows x {1} columns".format(*data.shape))
        debug(data)

        #
        # Resample data
        #
        if RESAMPLE:
            data = getattr(data.resample('H'),RESAMPLE)()
            verbose("resample: {0} rows x {1} columns".format(*data.shape))
            debug(data)

        #
        # Fill missing data
        #
        if FILL_METHOD:
            data.power.fillna(method=FILL_METHOD,inplace=True)

            verbose("fill: {0} rows x {1} columns".format(*data.shape))
            debug(data)

        #
        # Add timezone spec if missing
        #
        if TIMEZONE_COLUMN not in data.columns:
            data[TIMEZONE_COLUMN] = 0

        #
        # Group data
        #
        hour = (data[DATETIME_COLUMN].apply(lambda x:x.hour-1)+data[TIMEZONE_COLUMN]).astype(int).mod(24)
        weekend = data[DATETIME_COLUMN].apply(lambda x:(int(x.weekday()/5)))
        season = data[DATETIME_COLUMN].apply(lambda x:x.quarter-1)
        data["group"] = season*48 + weekend*24 + hour
        tzinfo = [data[TIMEZONE_COLUMN].min(),data[TIMEZONE_COLUMN].max()]
        dtinfo = [data[DATETIME_COLUMN].min(),data[DATETIME_COLUMN].max()]
        data.drop(TIMEZONE_COLUMN,inplace=True,axis=1)
        data.drop(DATETIME_COLUMN,inplace=True,axis=1)
        verbose("group: {0} rows x {1} columns".format(*data.shape))
        debug(data)

        # 
        # Perform pivot
        #
        groups = data.groupby([ID_COLUMN,"group"]).mean().reset_index().pivot(index=ID_COLUMN,columns="group",values=DATA_COLUMN)
        groups.dropna(inplace=True)
        verbose("pivot: {0} rows x {1} columns".format(*groups.shape))
        debug(groups)

        #
        # Run kmeans clustering
        #
        if GROUP_METHOD == "kmeans":

            if GROUP_COUNT <= 0:
                error(E_INVALID,"group count must be a positive integer")

            from sklearn.cluster import KMeans
            from sklearn.preprocessing import MinMaxScaler
            from sklearn.metrics import silhouette_score

            X = MinMaxScaler().fit_transform(groups.values.copy())
            kmeans = KMeans(n_clusters=GROUP_COUNT)
            group_found = kmeans.fit_predict(X)
            group_data = pd.Series(group_found, name="group")
            groups.set_index(group_data, append=True, inplace=True)
            verbose("groups: {0} rows x {1} columns".format(*groups.shape))
            debug(groups)
        else:
            error(E_INVALID,f"Group method '{GROUP_METHOD}' is invalid")

        #
        # Output CSV loadshapes
        #
        if LOADSHAPES_CSV:
            loadshapes = groups.groupby("group").mean()
            seasons = ["win","spr","sum","fal"]
            weekdays = ["wd","we"]
            loadshapes.columns = [f"{seasons[season]}_{weekdays[weekend]}_{hour}h" for season in range(4) for weekend in range(2) for hour in range(24)]
            loadshapes.to_csv(OPENFIDO_OUTPUT+LOADSHAPES_CSV,float_format=FLOAT_FORMAT)

        #
        # Output CSV groups
        #
        # TODO: scale for energy and/or power
        if GROUPS_CSV:
            groups.reset_index().set_index(ID_COLUMN)["group"].to_csv(OPENFIDO_OUTPUT+GROUPS_CSV,float_format=FLOAT_FORMAT)

        #
        # Output GLM clock
        if CLOCK_GLM:
            std = tzinfo[0]
            dst = tzinfo[1]
            tz = timezones[std]
            with open(OPENFIDO_OUTPUT+CLOCK_GLM,"w") as glm:
                print("clock {",file=glm)
                if std == dst:
                    tzspec = f"{tz}ST"
                else:
                    tzspec = f"{tz}ST{-std:+.0f}{tz}DT"
                print(f"  timezone \"{tzspec}\";",file=glm)
                print(f"  starttime \"{dtinfo[0]}\";",file=glm)
                print(f"  stoptime \"{dtinfo[1]}\";",file=glm)
                print("}",file=glm)

        #
        # Generate GridLAB-D schedules
        #
        if SCHEDULES_GLM:
            with open(OPENFIDO_OUTPUT+SCHEDULES_GLM,"w") as glm:
                for group in groups.index.get_level_values(level=1).unique():
                    subset = groups.xs(group, level=1)
                    values = subset.median()
                    print(f"schedule loadshape_{group}","{",file=glm)
                    months = ["1,2,3","4,5,6","7,8,9","10,11,12"]
                    weekdays = ["1,2,3,4,5","0,6"]
                    season_name = ["winter","spring","summer","fall"]
                    weekday_name = ["weekdays","weekends"]
                    for season in range(4):
                        print(f"  {season_name[season]}","{",file=glm)
                        for weekend in range(2):
                            for hour in range(24):
                                group = season*48 + weekend*24 + hour
                                print(f"    * {hour} * {months[season]} {weekdays[weekend]} {values[group]:.4g}; ",file=glm)
                        print("  }",file=glm)
                    print("}",file=glm)

        #
        # Generate GridLAB-D loads
        #
        if LOADS_GLM:
            if type(ID_COLUMN) is int:
                loads.set_index(data.reset_index().columns[ID_COLUMN],inplace=True)
            else:
                loads.set_index(ID_COLUMN,inplace=True)
            values = groups.reset_index().set_index(["meter_id","group"])
            values.index.names = ['meter_id', 'loadshape']
            values = values.melt(ignore_index=False).reset_index().set_index(["meter_id","loadshape","group"])
            values.index.names = ['meter_id', 'loadshape','hourtype']
            meters = data.set_index(["meter_id","group"])
            meters.index.names = ['meter_id','hourtype']
            mapping = meters.join(values).sort_index()
            scale = pd.DataFrame(mapping.groupby("meter_id").std().power/mapping.groupby("meter_id").std().value,columns=["scale"])
            offset = pd.DataFrame((1-scale).scale*mapping.groupby("meter_id").mean()["power"],columns=["offset"])
            with open(OPENFIDO_OUTPUT+LOADS_GLM,"w") as glm:
                print(f"module powerflow;",file=glm)
                for meter in groups.index.get_level_values(level=0).unique():
                    print(f"object {loads.loc[meter,'class']}","{",file=glm)
                    group_id = groups.loc[meter].index.values[0]
                    has_fraction = False
                    if LOADNAME_PREFIX:
                        print(f"  name \"{LOADNAME_PREFIX}{meter}\";",file=glm)
                    for propname in loads.columns:
                        if propname not in ["class","meter_id"]:
                            print(f"  {propname} {loads.loc[meter,propname]};",file=glm)
                        if "fraction" in propname.split("_"):
                            has_fraction = True
                    phases = loads.loc[meter,'phases']
                    if "A" in phases or "B" in phases or "C" in phases:
                        if "S" in phases:
                            phase = "12"
                            print(f"  base_power_{phase} loadshape_{group_id}*{scale.loc[meter].values[0]*LOAD_SCALE:.4g}{offset.loc[meter].values[0]*LOAD_SCALE:+.4g};",file=glm)
                        else:
                            n_phases = 0
                            for phase in "ABC":
                                if phase in phases:
                                    n_phases += 1
                            for phase in "ABC":
                                if phase in phases:
                                    print(f"  base_power_{phase} loadshape_{group_id}*{scale.loc[meter].values[0]/n_phases*LOAD_SCALE:.4g}{offset.loc[meter].values[0]/n_phases*LOAD_SCALE:+.4g};",file=glm)
                        if not has_fraction:
                            print(f"  power_fraction_{phase} 1.0;\n",file=glm)
                    else:
                        warning(f"load_{meter} has no phases specified")
                    print("}",file=glm)
        #
        # Output loadshape plot    
        #    
        if OUTPUT_PNG:
            import matplotlib.pyplot as plt
            fig,ax = plt.subplots(int(GROUP_COUNT/2),2, figsize=(18,3*GROUP_COUNT))
            for group in groups.index.get_level_values(level=1).unique():
                subset = groups.xs(group, level=1)
                ax = plt.subplot(int(GROUP_COUNT/2),2,group+1)
                plt.plot(subset.T,alpha=0.01,ls='-',color="blue")
                plt.plot(subset.median(), alpha=0.9, ls='-',color="black")
                ax.set_title(f"Loadshape {group} (N={len(subset)})")
                ax.set_ylabel('Power [kW]')
                ax.set_xlabel('\nHour type')
                ax.grid()
                y0 = ax.get_ylim()[0]
                for s in range(4):
                    for w in range(2):
                        label = plt.text(s*48+w*24+12,y0,["Weekday","Weekend"][w],axes=ax)
                        label.set_ha("center")
                        label.set_va("top")
                    label = plt.text(s*48+24,y0,["\nWinter","\nSpring","\nSummer","\nFall"][s],axes=ax)    
                    label.set_ha("center")
                    label.set_va("top")
                plt.xticks(range(0,192,24),[],axes=ax)
                plt.xlim([0,191])            
                plt.savefig(OPENFIDO_OUTPUT+OUTPUT_PNG, dpi=300)
            verbose(f"{OPENFIDO_OUTPUT}{OUTPUT_PNG} saved ok")

        #
        # Create archive output
        #
        if ARCHIVE_FILE:
            os.chdir(OPENFIDO_OUTPUT)
            if ARCHIVE_FILE.endswith("z"):
                os.system(f"tar cfz {ARCHIVE_FILE} --exclude {ARCHIVE_FILE} *")
            else:
                os.system(f"tar cf {ARCHIVE_FILE} --exclude {ARCHIVE_FILE} *")
    else:
        warning("INPUT_CSV not specified, no input data")

    exit(E_OK)

except Exception as err:

    if DEBUG:
        raise
    else:
        error(E_EXCEPTION,err)
