# Fit.py

import numpy as np
import datetime as dt
import configparser
import scipy
import scipy.integrate
import scipy.special as sp
from scipy.spatial import ConvexHull
import tables
import importlib
import os
import pymap3d as pm

<<<<<<< HEAD
=======
from Model_RBF import Model
from Param import AMISR_param
>>>>>>> rbf_model

class Fit(object):
    """
    This class performs the least-squares fit of the data to the 3D analytic model to find the coefficient vector for the model.
    It also handles calculating regularization matricies and parameters if nessisary.

    Parameters:
        config_file: [str]
            config file that specifies the fit parameters/options

    Atributes:
        date: date the model is fit for
        regularization_list: list of regularization methods to be used for the fit
        time: list of datetime objects corresponding to each event fit
        Coeffs: list of coefficient vectors corresponding to each event fit
        Covariance: list of covariance matrices corresponding to each event fit
        chi_sq: list of chi squared (goodness of fit test) corresponding to each event fit
        cent_point: list of the center points corresponding ot each event fit
        hull_v: list of hull verticies corresponding to each event fit
        raw_coords: list of the coordinates for the raw data corresponding to each event fit
        raw_data: list of the data value for the raw data corresponding to each event fit
        raw_error: list of the error vlue for the raw data corresponding to each event fit
        raw_filename: list of the raw data file names corresponding to each event fit
        raw_index: list of the index within each raw data file correspoinding ot each event fit

    Methods:
        get_ns: calculating the 2 n indicies for a NxN array from a 1D index q
        eval_omega: evaluate Omega, the curvature regularization matrix
        parallelize_omega: evaluates a single term in the Omega matrix, useful for parallelizing the loop
        omega_z_integrand: evaluates the z integrand for a term in the Omega matrix
        omega_t_integrand: evaluates the theta integrand for a term in the Omega matrix
        omega_p_integrand: evaluates the phi integrand for a term in the Omega matrix
        eval_Psi: evaluate Psi matrix, used for 0th order regularization
        parallelize_psi: evaluates a single term in the Psi maxtrix, useful for parallelizing the loop
        psi_z_integrand: evaluates the z integrand for a term in the Psi matrix
        psi_t_integrand: evaluates the theta integrand for a term in the Psi matrix
        psi_p_integrand: evaluates the phi integrand for a term in the Psi matrix
        eval_Tau: evaluates Tau vector, used for 0th order regularization
        parallelize_tau: evaluates a single term in the Tau vector, useful for parallelizing the loop
        tau_z_integrand: evaluates the z integrand for a term in the Tau vector
        tau_t_integrand: evaluates the theta integrand for a term in the Tau vector
        tau_p_integrand: evaluates the phi integrand for a term in the Tau vector
        find_reg_params: finds the regularization parameters
        chi2: finds the regularization parameter using the chi2-nu method
        chi2objfunct: objective function for the chi2-nu method
        gcv: finds the regularization parameter using generalized cross validation
        gcvobjfunct: the objective function for generalized cross validation
        manual: finds the regularization parameter via values manually hardcoded in function
        prompt: finds the regularization parameter via comand line prompts for user input
        eval_C: evaluates the coefficent vector and covariance matrix
        fit: performs fits to the 3D analytic model for data from a series of events
        saveh5: save the results of fit() to an output hdf5 file
        validate: plot the raw data and model fit to check for a good visual agreement

    """

    def __init__(self,config_file):

        self.configfile = config_file
        self.read_config(self.configfile)

        m = importlib.import_module(self.model_name)
        self.model = m.Model(open(self.configfile))

    def read_config(self, config_file):
        # read config file
        config = configparser.ConfigParser()
        config.read_file(open(config_file))

        self.regularization_list = config.get('DEFAULT','REGULARIZATION_LIST').split(',')
        self.reg_method = config.get('DEFAULT','REGULARIZATION_METHOD')

        self.filename = config.get('DEFAULT','FILENAME')
        self.outputfilename = config.get('DEFAULT','OUTPUTFILENAME')

        self.param = config.get('DEFAULT', 'PARAM')

<<<<<<< HEAD
        self.errlim = [float(i) for i in config.get('DEFAULT', 'ERRLIM').split(',')]
        self.chi2lim = [float(i) for i in config.get('DEFAULT', 'CHI2LIM').split(',')]
        self.goodfitcode = [int(i) for i in config.get('DEFAULT', 'GOODFITCODE').split(',')]
=======
        # maxk = eval(config.get('DEFAULT','MAXK'))
        # maxl = eval(config.get('DEFAULT','MAXL'))
        # cap_lim = eval(config.get('DEFAULT','CAP_LIM'))
        
        # super().__init__(maxk,maxl,cap_lim)
        super().__init__()
        
        self.regularization_list = eval(config.get('DEFAULT','REGULARIZATION_LIST'))
        self.reg_method = eval(config.get('DEFAULT','REGULARIZATION_METHOD'))
        self.max_z_int = float(config.get('DEFAULT','MAX_Z_INT'))
    
        self.filename = eval(config.get('DEFAULT','FILENAME'))
        self.outputfilename = eval(config.get('DEFAULT','OUTPUTFILENAME'))
                               
        param = eval(config.get('DEFAULT', 'PARAM'))
        self.param = AMISR_param(param)
>>>>>>> rbf_model

        self.model_name = config.get('MODEL', 'MODEL')





    # inform regularization parameter by beam seperation?
    # the more beams, the more features can be resolved?

    def find_reg_param(self,A,b,W,reg_matrices,method=None):
        """
        Find the regularization parameters.  A number of different methods are provided for this (se the reg_methods dictionary).
            - chi2: enforce the statistical condition chi2 = nu (e.g. Nicolls et al., 2014)
            - gcv: use Generalized Cross validation
            - manual: hardcode in regularization parameters
            - prompt: ask user for regularization parameters via a prompt

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            method: [str]
                method that should be used to find regularization parameter (valid options include 'chi2', 'gcv', 'manual', 'prompt')
        Returns:
            reg_params: [dict]
                dictionary of regularization parameters needed based on regularization_list
        Notes:
            - Currently, the automated methods of calculating regularization parameters (chi2 and gcv) handle multiple parameters by
                solving for each parameter individually while assuming all other parameters are zero.  This is non-ideal and tends
                to lead to over smothing, but it's the best approach we have right now because most standard methods of selecting
                regularization parameters only consider one condition (one condition = one unkown).  There is some literature on how
                to find multiple regularization parameters simultaniously, but have not had luck implementing any of these techniques.
            - Regularization (particularly choosing an "appropriate" regularization parameter) is VERY finiky.  This function attempts
                to have reasonable defaults and options, but it is HIGHLY unlikely these will work well in all cases.  The author has
                tried to make the code flexible so new methods can be added "easily", but appologizes in advance for the headache
                this will undoubtably cause.
        """

        # Define reg_methods dictionary
        reg_methods = {'chi2':self.chi2,'gcv':self.gcv,'manual':self.manual,'prompt':self.prompt}

        # Default method is chi2
        if method is None:
            method = 'chi2'

        reg_params = {}
        for rl in self.regularization_list:
            try:
                reg_params[rl] = reg_methods[method](A,b,W,reg_matrices,rl)
            except ValueError as err:
                print(err)
                print('Returning NANs for regularization parameters.')
                reg_params[rl] = np.nan

        return reg_params


    # consider modularizing out regularization Methods
    # these are probably things that will be changing/evolving frequently
    def chi2(self,A,b,W,reg_matrices,reg):
        """
        Find the regularization parameter using the chi2 method.

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            reg_param: [double]
                the value of the regularization parameter
        """

        # Set nu
        scale_factors = [0.6,0.7,0.8,0.9,1.0]
#         scale_factors = [1.0]
        N = len(b)
#         N = A.shape[0]-A.shape[1]
#         print(N,A.shape)
        bracket = False

        for sf in scale_factors:
            nu = N*sf
            # nu = N*1.

            # Determine the bracketing interval for the root (between 1e0 and 1e-100)
            alpha0 = 0.
            val0 = 1.
            alpha = 0.
            val = self.chi2objfunct(alpha,A,b,W,reg_matrices,nu,reg)
            if val<0:
                print('Too smooth to find regularization parameter. Returning alpha=0.')
                return 0

            while val0*val > 0:
                # print val0, val
                bracket = True
                # nu = N*scale_factor
                val0 = val
                alpha0 = alpha
                alpha = alpha - 1.
                val = self.chi2objfunct(alpha,A,b,W,reg_matrices,nu,reg)
                if alpha < -100.:
                    bracket = False
                    break
            if bracket:
                break
            else:
                continue


        if not bracket:
            raise ValueError('Could not find any roots to the objective function chi^2-nu in the range (1e-100,1).')
        else:
            # Use the Brent (1973) method to find the root within the bracketing interval found above
            solution = scipy.optimize.brentq(self.chi2objfunct,alpha,alpha0,args=(A,b,W,reg_matrices,nu,reg),disp=True)

        reg_param = np.power(10.,solution)

        return reg_param



    def chi2objfunct(self,alpha,A,b,W,reg_matrices,nu,reg):
        """
        Objective function for the chi2 method of finding the regularization parameter.  Returns chi^2-nu for a given
         regularization parameter.

        Parameters:
            alpha: [double]
                regularization parameter that is being found iteratively
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            nu: [double]
                value that chi2 should be equal to (usualy the number of data points)
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            chi2 - nu
        Notes:
            - The objective function is used in a root finder to find the regularization parameter which satisfies chi2-n=0.
        """

        # Make the reg_params dictionary from alpha and the defined reg
        reg_params = {}
        for rl in self.regularization_list:
            if rl == reg:
                reg_params[rl] = np.power(10.,alpha)
            else:
                reg_params[rl] = 0.

        # Evaluate coefficient vector
        C = self.eval_C(A,b,W,reg_matrices,reg_params)

        # compute chi^2
        val = np.squeeze(np.dot(A,C))
        chi2 = sum((val-np.squeeze(b))**2*np.squeeze(W))

        return chi2-nu




    def gcv(self,A,b,W,reg_matrices,reg):
        """
        Find the regularization parameter using the generalized cross validation method.

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            reg_param: [double]
                the value of the regularization parameter
        Notes:
            - Convergence of the minimizer can be very sensitive to the initial guess (alpha0) chosen.  This method has
                not been thoroughly tested for all AMISR parameters and modes, so it may be nessisary to alter the initial
                guess later, possibly having different initial guesses for density and temperature.
        """

        # Set initial guess
        alpha0 = -20.

        # Use the Nelder-Mead method to find the minimum of the GCV objective function
        solution = scipy.optimize.minimize(self.gcvobjfunct,alpha0,args=(A,b,W,reg_matrices,reg),method='Nelder-Mead')
        if not solution.success:
            raise ValueError('Minima of GCV function could not be found')

        reg_param = np.power(10.,solution.x[0])

        return reg_param


    def gcvobjfunct(self,alpha,A0,b0,W0,reg_matrices,reg):
        """
        Objective function for the GCV method of finding the regularization parameter.  Returns the value of the GCV function
         for a given regularization parameter.

        Parameters:
            alpha: [double]
                regularization parameter that is being found iteratively
            A0: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b0: [ndarray(npoints)]
                array of raw input data
            W0: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            GCV function for regularization parameter alpha
        Notes:
            - The objective function is used in a minimizer to find the regularization parameter which minimizes the GCV
                function.
        """

        # Define reg_params dictionary
        reg_params = {}
        for rl in self.regularization_list:
            if rl == reg:
                reg_params[rl] = np.power(10.,alpha)
            else:
                reg_params[rl] = 0.

        residuals = []
        for i in range(len(b0)):
            # Pull one data point out of arrays
            # data point in question:
            Ai = A0[i,:]
            bi = b0[i]
            Wi = W0[i]
            # arrays minus one data point:
            A = np.delete(A0,i,0)
            b = np.delete(b0,i,0)
            W = np.delete(W0,i,0)

            # Evaluate coefficient vector
            C = self.eval_C(A,b,W,reg_matrices,reg_params)

            # Calculate residual for the data point not included in the fit
            val = np.squeeze(np.dot(Ai,C))
            residuals.append((val-bi)**2*Wi)

        return sum(residuals)


    def manual(self,A,b,W,Omega,Psi,Tau,reg):
        """
        Manually hard-code the regularization parameter.

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            reg_param: [double]
                the value of the regularization parameter
        """

        lam = 1.e-28
        kappa = 1.e-23

        if reg == 'curvature':
            reg_param = lam
        if reg == '0thorder':
            reg_param = kappa

        return reg_param



    def prompt(self,A,b,W,Omega,Psi,Tau,reg):
        """
        Enter the regularization parameter via command line prompt.

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg: [str]
                regularization method (from regularization_list) that the regularization parameter is being solved for
        Returns:
            reg_param: [double]
                the value of the regularization parameter
        """

        reg_param = raw_input('Enter {} regularization parameter: '.format(reg))

        reg_param = float(reg_param)

        return reg_param

    def compute_hull(self,lat,lon,alt):
        """
        Compute the convex hull that contains the original data.  This is nessisary to check if points requested from the
         model are within the vaild range of where the data constrains the model.

        Parameters:
            R0: [ndarray(3,npoints)]
                array of input points in geocentric coordinates
                R = [[r coordinates (m)],[theta coordinates (rad)],[phi coordinates (rad)]]
                if input points are expressed as a list of r,t,p points, eg. points = [[r1,t1,p1],[r2,t2,p2],...], R = np.array(points).T
        Returns:
            hv: [ndarray(3,nverticies)]
                array of the coordinates of the verticies of the convex hull
        Notes:
            - hv is also saved as an attribute of the class
        """

        # x, y, z = cc.geodetic_to_cartesian(R0[0],R0[1],R0[2])
        x, y, z = pm.geodetic2ecef(lat, lon, alt)
        R_cart = np.array([x,y,z]).T

        chull = ConvexHull(R_cart)
        self.hull_vert = R_cart[chull.vertices]

        # lat, lon, alt = cc.cartesian_to_geodetic(vert.T[0],vert.T[1],vert.T[2])
        # self.hull_verticies = np.array([lat, lon, alt]).T
        #
        # return self.hull_verticies




    def eval_C(self,A,b,W,reg_matrices,reg_params,calccov=False):
        """
        Evaluate the coefficient array, C.

        Parameters:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
            b: [ndarray(npoints)]
                array of raw input data
            W: [ndarray(npoint)]
                array of errors on raw input data
            reg_matrices: [dict]
                dictionary of all the regularization matrices needed based on regularization_list
            reg_params: [dict]
                dictionary of all the regularization parameter values needed based on regularization_list
            calccov: [bool]
                boolian value whether or not to calculate the covariance matrix
        Returns:
            C: [ndarray(nbasis)]
                array of basis function coefficients
            dC: Optional [ndarray(nbasis,nbasis)]
                covariance matrix for basis functions
        """

        AWA = np.dot(A.T,W*A)
        X = np.dot(A.T,W*A)
        y = np.dot(A.T,W*b)

        for reg in self.regularization_list:
            X = X + reg_params[reg]*reg_matrices[reg]
        C = np.squeeze(scipy.linalg.lstsq(X,y,overwrite_a=True,overwrite_b=True)[0])

        if calccov:
            H = scipy.linalg.pinv(X)
            dC = np.dot(H,np.dot(AWA,H.T))
            return C, dC
        else:
            return C


    def fit(self, starttime=None, endtime=None):
        """
        Perform fit on every record in file.

        Parameters:
            None
        """


        Coeffs = []
        Covariance = []
        chi_sq = []

        print('Evaluating Regularization matricies.  This may take a few minutes.')
        reg_matricies = {}
        for reg in self.regularization_list:
            try:
                reg_matricies[reg] = self.model.eval_reg_matricies[reg]()
            except KeyError as e:
                print('WARNING: The model {} does not support {} regularization!'.format(self.model_name,reg))
                print('If you would like to use {} regularization, please modify {}.py so that it includes functions to calculate the appropriate regularization matrix.'.format(reg,self.model_name))
                raise e

        # read data from AMISR fitted file
        utime, lat, lon, alt, value, error = self.get_data(self.filename)

        # compute hull that surrounds data
        self.compute_hull(lat, lon, alt)

        # if a starttime and endtime are given, rewrite utime, value, and error arrays so
        #   they only contain records between those two times
        if starttime and endtime:
            idx = np.argwhere((utime[:,0]>=(starttime-dt.datetime.utcfromtimestamp(0)).total_seconds()) & (utime[:,1]<=(endtime-dt.datetime.utcfromtimestamp(0)).total_seconds())).flatten()
            utime = utime[idx,:]
            value = value[idx]
            error = error[idx]
<<<<<<< HEAD
=======
 
        # Find convex hull of original data set
        verticies = self.compute_hull(R00)

        self.set_model(R00)
        
        # Transform coordinates
        R0 = self.transform_coord(R00)
>>>>>>> rbf_model

        # loop over every record and calculate the coefficients
        # if modeling time variation, this loop will change?
        for ut, ne0, er0 in zip(utime, value, error):
            print(dt.datetime.utcfromtimestamp(ut[0]))

            # remove any points with NaN values
            # Any NaN in the input value array will result in all fit coefficients being NaN
            lat0 = lat[np.isfinite(ne0)]
            lon0 = lon[np.isfinite(ne0)]
            alt0 = alt[np.isfinite(ne0)]
            er0 = er0[np.isfinite(ne0)]
            ne0 = ne0[np.isfinite(ne0)]

            # define matricies
            W = np.array(er0**(-2))[:,None]
            b = ne0[:,None]
            A = self.model.basis(lat0, lon0, alt0)


            # # Evaluate Tau regularization matrix - this is based on data and must be in loop
            # if '0thorder' in self.regularization_list:
            #
            #     # try:
            #     # self.param.eval_zeroth_order(R[0],data,error)
            #     self.param.eval_zeroth_order(R[0],ne0,er0)
            #     tau = self.eval_tau(self.param.zeroth_order)
            #     # except RuntimeError:
            #     #     tau = np.full((self.nbasis,),np.nan)
            #     reg_matrices['Tau'] = tau
            #     # reg_matrices['Tau'] = self.eval_tau(R,ne0,er0)


            # # if regularization matricies are NaN, skip this record - fit can not be computed
            # if np.any([np.any(np.isnan(v.flatten())) for v in reg_matricies.values()]):
            #     # NaNs in C, dC, c2
            #     Coeffs.append(np.full(self.model.nbasis, np.nan))
            #     Covariance.append(np.full((self.model.nbasis,self.model.nbasis), np.nan))
            #     chi_sq.append(np.nan)
            #     continue

            # # define matricies
            # W = np.array(er0**(-2))[:,None]
            # b = ne0[:,None]
            # A = self.model.eval_basis(R)

            # calculate regularization parameters
            reg_params = self.find_reg_param(A,b,W,reg_matricies,method=self.reg_method)

            # if regularization parameters are NaN, skip this record - fit can not be computed
            if np.any(np.isnan([v for v in reg_params.values()])):
                # NaNs in C, dC, c2
                Coeffs.append(np.full(self.model.nbasis, np.nan))
                Covariance.append(np.full((self.model.nbasis,self.model.nbasis), np.nan))
                chi_sq.append(np.nan)
                continue

            # calculate coefficients and covarience matrix
            C, dC = self.eval_C(A,b,W,reg_matricies,reg_params,calccov=True)

            # calculate chi2
            c2 = sum((np.squeeze(np.dot(A,C))-np.squeeze(b))**2*np.squeeze(W))

            # append lists
            Coeffs.append(C)
            Covariance.append(dC)
            chi_sq.append(c2)

        self.time = utime
        self.Coeffs = np.array(Coeffs)
        self.Covariance = np.array(Covariance)
        self.chi_sq = np.array(chi_sq)
<<<<<<< HEAD
=======
        # self.cent_point = cp
        self.hull_v = verticies
        self.raw_coords = R00
        self.raw_data = value
        self.raw_error = error
>>>>>>> rbf_model
        self.raw_filename = self.filename


    def get_data(self,filename):
        """
        Read parameter from a processed AMISR hdf5 file and return the time, coordinates, values, and errors as arrays.

        Parameters:
            filename: [str]
                filename/path of processed AMISR hdf5 file

        Returns:
            utime: [ndarray (nrecordsx2)]
                start and end time of each record (Unix Time)
            R0: [ndarray (3xnpoints)]
                coordinates of each data point in spherical coordinate system
            value: [ndarray (nrecordsxnpoints)]
                parameter value of each data point
            error: [ndarray (nrecordsxnpoints)]
                error in parameter values
        """

<<<<<<< HEAD
        index_dict = {'frac':0, 'temp':1, 'colfreq':2}
        mass_dict = {'O':16, 'O2':32, 'NO':30, 'N2':28, 'N':14}
=======
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
        import cartopy.crs as ccrs

        self.fit(starttime=starttime, endtime=endtime)
        
        lat0, lon0, alt0 = self.raw_coords

        # set input coordinates
        latn, lonn = np.meshgrid(np.linspace(min(lat0), max(lat0), 50), np.linspace(min(lon0), max(lon0), 50))
        altn = np.full(latn.shape, altitude)
        R0n = np.array([latn, lonn, altn])

        Rshape = R0n.shape
        R0 = R0n.reshape(Rshape[0], -1)

        map_proj = ccrs.LambertConformal(central_latitude=np.mean(lat0), central_longitude=np.mean(lon0))
        denslim = [0., 3.e11]
    
        for i, (rd, C) in enumerate(zip(self.raw_data, self.Coeffs)):
            out = self.eval_model(R0,C)
            ne = out['param'].reshape(tuple(list(Rshape)[1:]))

            # create plot
            fig = plt.figure(figsize=(10,10))
            ax = fig.add_axes([0.02, 0.1, 0.9, 0.8], projection=map_proj)
            ax.coastlines()
            ax.gridlines()
            ax.set_extent([min(lon0),max(lon0),min(lat0),max(lat0)])

            # plot density contours from RISR
            c = ax.contourf(lonn, latn, ne, np.linspace(denslim[0],denslim[1],31), extend='both', transform=ccrs.PlateCarree())
            # c = ax.contourf(lonn, latn, ne, transform=ccrs.PlateCarree())
            ax.scatter(lon0[np.abs(alt0-altitude)<altlim], lat0[np.abs(alt0-altitude)<altlim], c=rd[np.abs(alt0-altitude)<altlim], vmin=denslim[0], vmax=denslim[1], transform=ccrs.Geodetic())

            cax = fig.add_axes([0.91,0.1,0.03,0.8])
            cbar = plt.colorbar(c, cax=cax)
            cbar.set_label(r'Electron Density (m$^{-3}$)')

            plt.savefig('temp{:02d}.png'.format(i))
            plt.close(fig)

#         self.datetime = time0

#         targtime = (self.datetime-dt.datetime(1970,1,1)).total_seconds()

#         try:
#             utime = np.array([[(t[0]-dt.datetime.utcfromtimestamp(0)).total_seconds(),(t[1]-dt.datetime.utcfromtimestamp(0)).total_seconds()] for t in self.time])
#             rec = np.where((targtime >= utime[:,0]) & (targtime < utime[:,1]))[0]
#             rec = rec[0]

#             self.t = self.time[rec][0]
#             self.C = self.Coeffs[rec]
#             self.dC = self.Covariance[rec]
#             self.hv = self.hull_v[rec].T
#             self.cp = self.cent_point[rec]
#             self.rR = self.raw_coords[rec].T
#             self.rd = self.raw_data[rec]
#             self.re = self.raw_error[rec]


#         except AttributeError:
#             self.loadh5(raw=True)


#         lat, lon, alt = cc.spherical_to_geodetic(self.hv.T[0],self.hv.T[1],self.hv.T[2])
#         latrange = np.linspace(min(lat),max(lat),50)
#         lonrange = np.linspace(min(lon),max(lon),50)
#         altrange = np.linspace(min(alt),max(alt),50)

#         cent_lat = (min(lat)+max(lat))/2.
#         cent_lon = (min(lon)+max(lon))/2.
#         height = (max(lat)-min(lat))*np.pi/180.*(RE+altitude)
#         width = (max(lon)-min(lon))*np.pi/180.*(RE+altitude)*np.cos(cent_lat*np.pi/180.)
>>>>>>> rbf_model

        with tables.open_file(filename,'r') as h5file:

            utime = h5file.get_node('/Time/UnixTime')[:]

            alt = h5file.get_node('/Geomag/Altitude')[:]
            lat = h5file.get_node('/Geomag/Latitude')[:]
            lon = h5file.get_node('/Geomag/Longitude')[:]
            c2 = h5file.get_node('/FittedParams/FitInfo/chi2')[:]
            fc = h5file.get_node('/FittedParams/FitInfo/fitcode')[:]
            imass = h5file.get_node('/FittedParams/IonMass')[:]

            if self.param == 'dens':
                val = h5file.get_node('/FittedParams/Ne')[:]
                err = h5file.get_node('/FittedParams/dNe')[:]
            else:
                param = self.param.split('_')
                # find i index based on what the key starts with
                i = index_dict[param[0]]
                # find m index based on what the key ends with
                try:
                    m = int(np.where(imass == mass_dict[param[1]])[0])
                except IndexError:
                    m = -1
                val = h5file.get_node('/FittedParams/Fits')[:,:,:,m,i]
                err = h5file.get_node('/FittedParams/Errors')[:,:,:,m,i]


        altitude = alt.flatten()
        latitude = lat.flatten()
        longitude = lon.flatten()
        chi2 = c2.reshape(c2.shape[0], -1)
        fitcode = fc.reshape(fc.shape[0], -1)

        value = val.reshape(val.shape[0], -1)
        error = err.reshape(err.shape[0], -1)

        # This accounts for an error in some of the hdf5 files where chi2 is overestimated by 369.
        if np.nanmedian(chi2) > 100.:
            chi2 = chi2 - 369.

        # data_check: 2D boolian array for removing "bad" data
        # Each column correpsonds to a different "check" condition
        # TRUE for "GOOD" point; FALSE for "BAD" point
        # A "good" record that shouldn't be removed should be TRUE for EVERY check condition
        data_check = np.array([error>self.errlim[0], error<self.errlim[1], chi2>self.chi2lim[0], chi2<self.chi2lim[1], np.isin(fitcode,self.goodfitcode)])

        # If ANY elements of data_check are FALSE, flag index as bad data
        bad_data = np.squeeze(np.any(data_check==False,axis=0,keepdims=True))
        value[bad_data] = np.nan
        error[bad_data] = np.nan

        # remove the points where coordinate arrays are NaN
        # these points usually correspond to altitude bins that were specified by the fitter but a particular beam does not reach
        value = value[:,np.isfinite(altitude)]
        error = error[:,np.isfinite(altitude)]
        latitude = latitude[np.isfinite(altitude)]
        longitude = longitude[np.isfinite(altitude)]
        altitude = altitude[np.isfinite(altitude)]


        return utime, latitude, longitude, altitude, value, error



    def saveh5(self):
        # TODO: compress arrays to reduce coefficient file size
        """
        Saves coefficients to a hdf5 file

        Parameters:
            None
        """

        with tables.open_file(self.outputfilename, 'w') as h5out:

            cgroup = h5out.create_group('/','Coeffs','Dataset')
            fgroup = h5out.create_group('/','FitParams','Dataset')
            dgroup = h5out.create_group('/','RawData','Dataset')

            h5out.create_array('/', 'UnixTime', self.time)

            h5out.create_array(cgroup, 'C', self.Coeffs)
            h5out.create_array(cgroup, 'dC', self.Covariance)

            h5out.create_array(fgroup, 'reglist', self.regularization_list)
            h5out.create_array(fgroup, 'regmethod', self.reg_method.encode('utf-8'))
            h5out.create_array(fgroup, 'chi2', self.chi_sq)

            h5out.create_array(fgroup, 'hull_vert', self.hull_vert)

            h5out.create_array(dgroup, 'filename', self.raw_filename.encode('utf-8'))

            # config file
            Path = os.path.dirname(os.path.abspath(self.configfile))
            Name = os.path.basename(self.configfile)
            with open(self.configfile, 'r') as f:
                Contents = ''.join(f.readlines())

            h5out.create_group('/', 'ConfigFile')
            h5out.create_array('/ConfigFile', 'Name', Name.encode('utf-8'))
            h5out.create_array('/ConfigFile', 'Path', Path.encode('utf-8'))
            h5out.create_array('/ConfigFile', 'Contents', Contents.encode('utf-8'))
