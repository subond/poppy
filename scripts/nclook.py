#!/usr/env python
"""
This script can be executed as is or via an alias, e.g.

    alias nclookipy='ipython -i ~/path/to/nclook.py'

to quickly open a NetCDF file in Python.
"""
from __future__ import print_function
import argparse
import traceback
import os.path
import matplotlib.pyplot as plt
plt.style.use('ggplot')

# determine which importer to use (xray preferred)
try:
    import xray
    _ncmodule = 'xray'
except ImportError:
    import netCDF4
    _ncmodule = 'netCDF4'


def open_files(ncfiles, return_dsvar=False):
    """Open netCDF files, either with xray or netCDF4"""
    try:
        if _ncmodule == 'xray':
            # open files with xray
            try:
                ds = xray.open_mfdataset(ncfiles)
            except ValueError:
                ds = xray.open_mfdataset(ncfiles, decode_times=False)
                print('Warning: Using decode_times=False')
            dsvar = ds
        else:
            # open files with netCDF4
            if len(ncfiles) > 1:
                ds = netCDF4.MFDataset(ncfiles)
            else:
                ds = netCDF4.Dataset(ncfiles[0])
            dsvar = ds.variables
    except RuntimeError as err:
        traceback.print_exc(err)
        print('Warning: File(s) could not be opened: {}'.format(ncfiles))
        dsvar = None
    if return_dsvar:
        return ds, dsvar
    else:
        return ds


def save_figure(fname, fig=None):
    """Save current figure to file with default options for png and pdf"""
    if fig is None:
        fig = plt.gca().figure
    fname = os.path.expanduser(fname)
    if fname.endswith('.pdf'):
        fig.savefig(fname, bbox_inches='tight')
    else:
        fig.savefig(fname, dpi=200)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Open one or several netCDF files from command line")
    parser.add_argument('ncfiles', nargs='+', help='path to netCDF file')
    args = parser.parse_args()

    print('opening {} netCDF file(s) into namespace as \'ds\' using {} ...'.format(
        len(args.ncfiles), _ncmodule))
    ds, dsvar = open_files(args.ncfiles, return_dsvar=True)

    # Convenience functions for xray
    if _ncmodule == 'xray':
        def list_variables(ds=ds):
            for k in ds.keys():
                try:
                    print('{} : {}'.format(k, ds[k].long_name))
                except AttributeError:
                    print(k)


    # Convenience functions for netCDF4
    if _ncmodule == 'netCDF4':

        def quickplot(varn, k, dsvar=dsvar, t=0, cmap='cubehelix', **kwarg):
            """Make a quick plot of the given variable at levek `k` and time step `t`
            
            Parameters
            ----------
            varn : str
                name of 4D variable present in `dsvar`
            k : int
                vertical level index
            t : int
                time level index
            cmap : str or colormap
                color map
            **kwarg : dict
                keyword arguments passed to plt.pcolormesh
            """
            fig = plt.figure()
            plt.title('{} at {:.0f} m'.format(varn, dsvar['z_t'][k]*1e-2))
            plt.pcolormesh(dsvar[varn][t,k], cmap=cmap, **kwarg)
            plt.colorbar(label='{} ({})'.format(dsvar[varn].long_name, dsvar[varn].units))
            plt.show()
            return fig

        def list_variables(units=True,ndim=None,shapes=True):
            """List variables in netCDF *dataset*
            including units if *units* for variables 
            in *ndim* dimensions only, if specified"""
            def _get_variable_list(ds):
                for varn in ds.variables.keys():
                    if ndim is not None:
                        if len(ds.variables[varn].shape) != ndim:
                            continue
                    s = ''
                    try:
                        s += '{} :'.format(varn)
                    except:
                        pass
                    try:
                        s += ' {}'.format(ds.variables[varn].long_name)
                    except:
                        pass
                    try:
                        varunits = ds.variables[varn].units
                        if units and varunits:
                            s += ' [{}]'.format(varunits)
                    except:
                        pass
                    if shapes:
                        try:
                            s += ' {}'.format(ds.variables[varn].shape)
                        except:
                            pass
                        # print output
                    if s: 
                        print(s)
            try:
                with netCDF4.Dataset(ds) as ds_new:
                    _get_variable_list(ds_new)
            except:
                _get_variable_list(ds)
