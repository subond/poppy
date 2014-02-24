import numpy as np
from oceanpy.fluxbudget import budget_over_region_2D
from oceanpy.stats import central_differences

def _fill0(a):
    return np.ma.filled(a,0)


def fluxbudget_VVEL(ds,mask,varn,kza=0,kzo=None,S0=34.8,t=0):
    """Integrate horizontal flux using VVEL*SCALAR"""
    dxu = ds.variables['DXU'][:]/100.
    dyu = ds.variables['DYU'][:]/100.
    dz = ds.variables['dz'][:]/100.
    if kzo is None: kzo = len(dz)
    fluxbudget = 0.
    for k in xrange(kza,kzo):
        uflux = np.ma.filled(ds.variables['UVEL'][t,k]/100.,0)
        uflux *= dyu
        uflux *= dz[k]
        vflux = np.ma.filled(ds.variables['VVEL'][t,k]/100.,0)
        vflux *= dxu
        vflux *= dz[k]
        if not varn:
            scalar = None
        elif varn == 'heat':
            scalar = np.ma.filled(ds.variables['TEMP'][t,k],0)
        elif varn == 'salt':
            scalar = np.ma.filled(ds.variables['SALT'][t,k],0)
        elif varn == 'freshwater':
            scalar = (S0 - np.ma.filled(ds.variables['SALT'][t,k],0)) / S0
            scalar *= np.ma.filled(ds.variables['VVEL'][t,k],0)/100.
        fluxbudget += budget_over_region_2D(uflux,vflux,scalar=scalar,mask=mask,grid='ArakawaB')
    if varn == 'heat':
        fluxbudget *= (1e3 * 4e3 * 1e-15) # PW
    return fluxbudget


def fluxbudget_UESVNS(ds,mask,kza=0,kzo=None,t=0):
    """Integrate horizontal flux using UES and VNS variables"""
    dsvar = ds.variables
    dz = dsvar['dz'][:] * 1e-2
    tarea = dsvar['TAREA'][:] * 1e-4
    if kzo is None: kzo = len(dz)
    fluxbudget = 0.
    for k in xrange(kza,kzo):
        uflux = np.ma.filled(dsvar['UES'][t,k],0)
        uflux *= tarea
        uflux *= dz[k]
        vflux = np.ma.filled(dsvar['VNS'][t,k],0)
        vflux *= tarea
        vflux *= dz[k]
        fluxbudget += budget_over_region_2D(uflux,vflux,scalar=None,mask=mask)
    return fluxbudget


def fluxbudget_bolus_visop(ds,mask,varn,kza=0,kzo=None,S0=34.8):
    """Compute flux of `varn` into region `mask` due to eddy (bolus) velocity"""
    dxt = ds.variables['DXT'][:]/100.
    dyt = ds.variables['DYT'][:]/100.
    dz = ds.variables['dz'][:]/100.
    if kzo is None: kzo = len(dz)
    fluxbudget = 0.
    for k in xrange(kza,kzo):
        # get bolus velocity
        uflux = np.ma.filled(ds.variables['UISOP'][0,k]/100.,0) # m s-1
        vflux = np.ma.filled(ds.variables['VISOP'][0,k]/100.,0) # m s-1
        # get scalar data
        if varn == 'heat':
            scalar = np.ma.filled(ds.variables['TEMP'][0,k],0)
        elif varn == 'salt':
            scalar = np.ma.filled(ds.variables['SALT'][0,k],0)
        elif varn == 'freshwater':
            scalar = (S0 - np.ma.filled(ds.variables['SALT'][0,k],0)) / S0
        # multiply flux by scalar
        uflux *= scalar
        vflux *= scalar
        # multiply by horizontal grid spacing
        uflux *= dyt
        vflux *= dxt
        # multiply by vertical grid spacing
        uflux *= dz[k]
        vflux *= dz[k]
        # compute budget
        fluxbudget += budget_over_region_2D(uflux,vflux,scalar=None,mask=mask)
    if varn == 'heat':
        fluxbudget *= (1e3 * 4e3 * 1e-15) # PW
    return fluxbudget

fluxbudget_bolus = fluxbudget_bolus_visop


def fluxbudget_diffusion(ds,mask,varn,kza=0,kzo=None,S0=34.8,t=0):
    """Compute flux of `varn` into region `mask` due to diffusion"""
    dxt = ds.variables['DXT'][:]/100.
    dyt = ds.variables['DYT'][:]/100.
    dz = ds.variables['dz'][:]/100.
    if kzo is None: kzo = len(dz)
    fluxbudget = 0.
    for k in xrange(kza,kzo):
        # get scalar data
        if varn == 'heat':
            scalar = np.ma.filled(ds.variables['TEMP'][t,k],0)
        elif varn == 'salt':
            scalar = np.ma.filled(ds.variables['SALT'][t,k],0)
        elif varn == 'freshwater':
            scalar = (S0 - np.ma.filled(ds.variables['SALT'][t,k],0)) / S0
        # get gradient
        uflux = central_differences(scalar,dxt,axis=1) # [scalar] m-1
        vflux = central_differences(scalar,dyt,axis=0) # [scalar] m-1
        # multiply gradient by diffusion coefficient
        kappa = np.ma.filled(ds.variables['KAPPA_ISOP'][t,k]/1e4,0) # m2 s-1
        uflux *= kappa
        vflux *= kappa
        # multiply by horizontal grid spacing
        uflux *= dyt
        vflux *= dxt
        # multiply by vertical grid spacing
        uflux *= dz[k]
        vflux *= dz[k]
        # compute budget
        fluxbudget += budget_over_region_2D(uflux,vflux,scalar=None,mask=mask)
    # convert to right units
    if varn == 'heat':
        fluxbudget *= (1e3 * 4e3 * 1e-15) # PW
    return fluxbudget


def fluxbudget_bolus_advection_tendency(ds,mask,varn,t=0):
    dsvar = ds.variables
    if varn == 'heat':
        integrand = _fill0(dsvar['ADVT_ISOP'][t][mask]) * 1e-2
    elif varn == 'salt':
        integrand = _fill0(dsvar['ADVS_ISOP'][t][mask]) * 1e-2
    else:
        raise ValueError('This function only works for heat and salt transport.')
    integrand *= dsvar['TAREA'][:][mask] * 1e-4
    return np.sum(integrand)


def transport_divergence(ds,mask,kza=0,kzo=None,t=0):
    dxu = ds.variables['DXU'][:]/100.
    dyu = ds.variables['DYU'][:]/100.
    tarea = ds.variables['TAREA'][:]/1e4
    dz = ds.variables['dz'][:]/100.    
    if kzo is None: kzo = len(dz)
    transport_divergence = 0.
    for k in xrange(kza,kzo):
        uflux = ds.variables['UES'][t,k]
        uflux *= dyu
        uflux *= dz[k]
        uflux *= mask
        vflux = ds.variables['VNS'][t,k]
        vflux *= dxu
        vflux *= dz[k]
        vflux *= mask
        divergence = central_differences(uflux,dxu,axis=1) + central_differences(vflux,dyu,axis=0)
        divergence *= mask
        transport_divergence += np.sum(divergence*tarea)
    return transport_divergence


