from __future__ import print_function
import numpy as np
import netCDF4
import xray
import scipy.ndimage
import subprocess
import traceback
try:
    import pandas as pd
    use_pandas = True
except ImportError:
    use_pandas = False
    print('Pandas could not be imported. Functions will return data as tuple '
          '(tseries, timeaxis).')
    pass

from . import grid as poppygrid
from . import utils

### HELP FUNCTIONS

def get_ulimitn(default=1e3):
    """Try to get the maximum number of open files on the system. Works with Unix."""
    return 100 # There are performance issues with netCDF4.MFDataset
    try:
        maxn = int(subprocess.check_output(['ulimit -n'],shell=True))
    except:
        maxn = default
        traceback.print_exc()
    return maxn

def _nfiles_diag(n):
    if n == 0:
        raise ValueError('No files found. Check your glob pattern.')
    else:
        print('Processing {} files ...'.format(n))

def _pandas_add_meta_data(ts, meta):
    return ts # NOT WORKING PROPERLY ANYWAYS!
    for k,v in meta.iteritems():
        ts.k = v
        ts._metadata.append(k)
    return ts

def _pandas_copy_meta_data(source, target, addmeta={}):
    return target # NOT WORKING PROPERLY ANYWAYS!
    for k in source._metadata:
        try:
            setattr(target, k, getattr(source, k))
            target._metadata.append(k)
        except AttributeError:
            print('Warning: Series/dataframe has no attribute \'{}\''.format(k))
    _pandas_add_meta_data(target, addmeta)
    return target


### METRICS FUNCTIONS

def get_amoc(ncfiles, latlim=(30,60), zlim=(500,9999), window_size=12):
    """Retrieve AMOC time series from a set of CESM/POP model output files

    Parameters
    ----------
    ncfiles : list of str
        paths to input files
    latlim : tuple
        Latitude limits between which to find the maximum AMOC
    zlim : tuple
        Depth limits between which to find the maximum AMOC
    window_size : int
        Smoothing window width to apply before taking maximum

    Returns
    -------
    Atlantic meridional overturning circulation (AMOC) maximum between 
    30N and 60N below 500 m water depth (following Shields et al. 2012).

    Note
    ----
    Only works with POP data that has the diagnostic variable 'MOC' included.

    """
    n = len(ncfiles)
    _nfiles_diag(n)
    
    maxn = get_ulimitn()

    with netCDF4.Dataset(ncfiles[0]) as ds:
        dsvar = ds.variables
        zax = dsvar['moc_z'][:]/100.
        kza = np.argmin(np.abs(zax-zlim[0]))
        kzo = np.argmin(np.abs(zax-zlim[1]))
        nz = kzo-kza+1

        latax = dsvar['lat_aux_grid'][:]
        ja = np.argmin(np.abs(latax-latlim[0]))
        jo = np.argmin(np.abs(latax-latlim[1]))        
        nlat = jo-ja+1
        
    if n <= maxn:
        with netCDF4.MFDataset(ncfiles) as ds:
            dsvar = ds.variables
            timeax = utils.get_time_decimal_year(dsvar['time'])
            amoc = dsvar['MOC'][:,1,0,kza:kzo+1,ja:jo+1]
    else:
        timeax = np.zeros(n)
        amoc = np.zeros((n,nz,nlat))
        for i,fname in enumerate(ncfiles):
            with netCDF4.Dataset(fname) as ds:
                dsvar = ds.variables
                timeax[i] = utils.get_time_decimal_year(dsvar['time'])
                amoc[i] = dsvar['MOC'][0,1,0,kza:kzo+1,ja:jo+1]
                
    if window_size > 1:
        maxmeanamoc = np.max(np.max(scipy.ndimage.convolve1d(
            amoc,weights=np.ones(int(window_size))/float(window_size),
            axis=0,mode='constant',cval=np.nan),axis=-1),axis=-1)
        maxmeanamoc[:window_size+1] = np.nan
        maxmeanamoc[-window_size:] = np.nan
    else:
        maxmeanamoc = np.max(np.max(amoc,axis=-1),axis=-1)

    if use_pandas:
        index = pd.Index(timeax, name='ModelYear')
        ts = pd.Series(maxmeanamoc, index=index, name='AMOC')
        _pandas_add_meta_data(ts, meta=dict(
           latlim = latlim,
           zlim = zlim,
            ))
        return ts
    else:
        return maxmeanamoc, timeax


componentnames = {
    0 : 'Total',
    1 : 'Eulerian-Mean Advection',             
    2 : 'Eddy-Induced Advection (bolus) + Diffusion',
    3 : 'Eddy-Induced (bolus) Advection',
    4 : 'Submeso Advection',
    }


def get_mht(ncfiles, latlim=(30,60), component=0):
    """Get MHT time series from CESM/POP data
    
    Parameters
    ----------
    ncfiles : list of str
        paths to input files
    latlim : tuple
        latitude limits for maximum
    component : int
        see metrics.componentnames
    """
    n = len(ncfiles)
    _nfiles_diag(n)
    maxn = get_ulimitn()

    with netCDF4.Dataset(ncfiles[0]) as ds:
        latax = ds.variables['lat_aux_grid'][:]
        ja = np.argmin(np.abs(latax-latlim[0]))
        jo = np.argmin(np.abs(latax-latlim[1]))
        nlat = jo-ja+1
        
    if n <= maxn:
        with netCDF4.MFDataset(ncfiles) as ds:
            dsvar = ds.variables
            timeax = utils.get_time_decimal_year(dsvar['time'])
            nheat = dsvar['N_HEAT'][:,0,component,ja:jo+1]
    else:
        timeax = np.zeros(n)
        nheat = np.zeros((n,nlat))
        for i,fname in enumerate(ncfiles):
            with netCDF4.Dataset(fname) as ds:
                dsvar = ds.variables
                timeax[i] = utils.get_time_decimal_year(dsvar['time'])
                nheat[i,:] = dsvar['N_HEAT'][0,0,component,ja:jo+1]
                
    window_size = 12
    maxmeannheat = np.max(scipy.ndimage.convolve1d(
        nheat,weights=np.ones(int(window_size))/float(window_size),
        axis=0,mode='constant',cval=np.nan),axis=-1)

    if use_pandas:
        index = pd.Index(timeax, name='ModelYear')
        ts = pd.Series(maxmeannheat, index=index, name='MHT')
        _pandas_add_meta_data(ts, meta=dict(
            latlim = latlim,
            component = component,
            ))
        return ts
    else:
        return maxmeannheat, timeax


def get_mst(ncfiles, lat0=55, component=0):
    """Get MST time series from CESM/POP data
    
    Parameters
    ----------
    ncfiles : list of str
        paths to input files
    lat0 : float
        latitude to take the mean at
    component : int
        see metrics.componentnames
    """
    n = len(ncfiles)
    _nfiles_diag(n)
    maxn = get_ulimitn()

    with netCDF4.Dataset(ncfiles[0]) as ds:
        dsvar = ds.variables
        latax = dsvar['lat_aux_grid'][:]
        j0 = np.argmin(np.abs(latax-lat0))
        
    if n <= maxn:
        with netCDF4.MFDataset(ncfiles) as ds:
            dsvar = ds.variables
            timeax = utils.get_time_decimal_year(dsvar['time'])
            nsalt = dsvar['N_SALT'][:,0,component,j0]
    else:
        timeax = np.zeros(n)
        nsalt = np.zeros(n)
        for i,fname in enumerate(sorted(ncfiles)):
            with netCDF4.Dataset(fname) as ds:
                dsvar = ds.variables
                timeax[i] = utils.get_time_decimal_year(dsvar['time'])
                nsalt[i] = dsvar['N_SALT'][0,0,component,j0]
                
    window_size=12
    window = np.ones(int(window_size))/float(window_size)
    meannsalt = np.convolve(nsalt,window,'same')
    meannsalt[:window_size+1] = np.nan
    meannsalt[-window_size:] = np.nan

    if use_pandas:
        index = pd.Index(timeax, name='ModelYear')
        ts = pd.Series(meannsalt, index=index, name='MST')
        ts = _pandas_add_meta_data(ts, meta=dict(
            lat0 = lat0,
            component = component,
            ))
        return ts
    else:
        return meannsalt, timeax


def get_timeseries(ncfiles, varn, grid, 
        reducefunc=np.nanmean, 
        latlim=None, lonlim=None, k=0):
    """Get time series of any 2D POP field reduced by a numpy function
    
    Parameters
    ----------
    ncfiles : list of str
        paths to input files
    varn : str
        variable name
    grid : str ('T' or 'U')
        which grid the variable is on
    reducefunc : function
        function to reduce the selected region
        NOTE: must be NaN-aware
    latlim : tup
        latitude limits for maximum
    lonlim : tup
        longitude limits for maximum
    k : int
        layer
    """
    n = len(ncfiles)
    _nfiles_diag(n)
    maxn = get_ulimitn()

    # get mask
    with xray.open_dataset(ncfiles[0], decode_times=False) as ds:
        if latlim is None and lonlim is None:
            mask = None
        else:
            mask = poppygrid.get_grid_mask(
                    lon = ds[grid+'LONG'], 
                    lat = ds[grid+'LAT'],
                    lonlim=lonlim, latlim=latlim)
            mask &= ds.variables['KM'+grid][:]>0

    # read data
    if n <= maxn:
        with xray.open_mfdataset(ncfiles, decode_times=False) as ds:
            # select variable
            ds = ds[varn]
            # select level
            try:
                ds = ds.isel(z_t=k)
            except ValueError:
                pass
            # apply mask
            if mask is not None:
                ds = ds.where(mask)
            tseries = ds.reduce(reducefunc, ['nlon', 'nlat']).values
            timevar = ds['time']
            timeax = utils.get_time_decimal_year(timevar)
    else:
        timeax = np.zeros(n)
        tseries = np.zeros((n))
        for i,fname in enumerate(ncfiles):
            with xray.open_dataset(fname, decode_times=False) as ds:
                # select variable
                ds = ds[varn]
                # select level
                try:
                    ds = ds.isel(z_t=k)
                except ValueError:
                    pass
                # apply mask
                if mask is not None:
                    ds = ds.where(mask)
                tseries[i] = ds.reduce(reducefunc, ['nlon', 'nlat']).values
                timevar = ds['time']
                timeax[i] = utils.get_time_decimal_year(timevar)

    # output
    if use_pandas:
        index = pd.Index(timeax, name='ModelYear')
        ts = pd.Series(tseries, index=index, name=varn)
        _pandas_add_meta_data(ts, meta=dict(
            latlim = latlim,
            lonlim = lonlim,
            varn = varn,
            reducefunc = str(reducefunc),
            k = k,
            grid = grid,
            ))
        return ts
    else:
        return tseries, timeax

