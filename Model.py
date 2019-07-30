# Model.py

import numpy as np
import scipy.special as sp
import coord_convert as cc

RE = 6371.2*1000.           # Earth Radius (m)	

class Model(object):
    # TODO: update docstring
    """
    This class defines the 3D analytic model that is used to describe density and temperature within an AMISR FoV.

    Parameters:
        maxk: [int]
            number of basis functions used in the vertical direction
        maxl: [int]
            number of basis functions used in the horizontal direction
        cap_lim: [double]
            colatitude limit of the polar cap in radians
        C: Optional [ndarray(nbasis)]
            array of fit coefficients - must be nbasis long
        dC: Optional [ndarray(nbasis,nbasis)]
            covariance matrix for fit coefficients - must be nbasis X nbasis

    Attributes:
        maxk: number of basis functions used in the vertical direction
        maxl: number of basis functions used in the horizontal direction
        nbasis: total number of 3D basis functions used
        cap_lim: colatitude (in radians) of the edge of the "cap" used for spherical cap harmonics (defaults to 6 degrees)
        C: array of fit coefficients
        dC: covariance matrix of fit coefficients

    Methods:
        basis_numbers: returns k, l, m given a single input 3D basis index
        nu: returns v, the non-integer degree for spherical cap harmonics
        eval_basis: returns a matrix of all basis functions calcuated at all input points
        eval_grad_basis: returns a maxtix of the gradient of all basis fuctions calculated at all input points
        eval_model: returns parameter and gradient arrays for all input points
        Az: azimuthal component
        dAz: derivative of azimuthal component
        Kvm: constant Kvm

    Notes:
        - All methods EXCEPT for eval_model() can be called without specifying C or dC.
    """

    def __init__(self,maxk,maxl,cap_lim=6.):
        self.maxk = maxk
        self.maxl = maxl
        self.nbasis = self.maxk*self.maxl**2
        self.cap_lim = cap_lim*np.pi/180.
#         if C is not None:
#             self.C = C
#         if dC is not None:
#             self.dC = dC

    def basis_numbers(self,n):
        """
        Converts a single 3D index number into 3 individual indexes for the radial, latitudinal, and azimulthal components

        Parameters:
            n: [int]
                single 3D index number

        Returns:
            k: [int]
                radial index number corresponding to n
            l: [int]
                latitudinal index number corresponding to n
            m: [int]
                azimuthal index number corresponding to n
        """
        k = n//(self.maxl**2)
        r = n%(self.maxl**2)
        l = np.floor(np.sqrt(r))
        m = r-l*(l+1)
        return k, l, m

    def nu(self,n):
        """
        Returns the non-integer order of the spherical cap harmonics given a 3D index number
        This is calculated using the approximation given in Thebault et al., 2006.

        Parameters:
            n: [int]
                single 3D index number
        Returns:
            v: [double]
                non-integer degree for the spherical cap harmonics
        """
        k, l, m = self.basis_numbers(n)
        v = (2*l+0.5)*np.pi/(2*self.cap_lim)-0.5
        return v


    def eval_basis(self,R):
        """
        Calculates a matrix of the basis functions evaluated at all input points

        Parameters:
            R: [ndarray(3,npoints)]
                array of input coordinates
                R = [[z coordinates (m)],[theta coordinates (rad)],[phi coordinates (rad)]]
                if input points are expressed as a list of r,t,p points, eg. points = [[r1,t1,p1],[r2,t2,p2],...], R = np.array(points).T
        Returns:
            A: [ndarray(npoints,nbasis)]
                array of basis functions evaluated at all input points
        Notes:
            - Something clever could probably be done to not recalculate the full expression when incrimenting n does not result in a change in k, or similar.
                All the evaluations of special functions here make it one of the slowest parts of the code.
        """
        z = R[0]
        theta = R[1]
        phi = R[2]
        A = []
        for n in range(self.nbasis):
            k, l, m = self.basis_numbers(n)
            v = self.nu(n)
            A.append(np.exp(-0.5*z)*sp.eval_laguerre(k,z)*self.Az(v,m,phi)*sp.lpmv(m,v,np.cos(theta)))
        return np.array(A).T


    def eval_grad_basis(self,R):
        """
        Calculates a matrix of the gradient of basis functions evaluated at all input points

        Parameters:
            R: [ndarray(3,npoints)]
                array of input coordinates
                R = [[z coordinates (m)],[theta coordinates (rad)],[phi coordinates (rad)]]
                if input points are expressed as a list of r,t,p points, eg. points = [[r1,t1,p1],[r2,t2,p2],...], R = np.array(points).T
        Returns:
            A: [ndarray(npoints,nbasis,3)]
                array of gradient of basis functions evaluated at all input points
        Notes:
            - Something clever could probably be done to not recalculate the full expression when incrimenting n does not result in a change in k, or similar.
                All the evaluations of special functions here make it one of the slowest parts of the code.
        """
        z = R[0]
        theta = R[1]
        phi = R[2]
        Ag = []
        x = np.cos(theta)
        y = np.sin(theta)
        e = np.exp(-0.5*z)
        for n in range(self.nbasis):
            k, l, m = self.basis_numbers(n)
            v = self.nu(n)
            L0 = sp.eval_laguerre(k,z)
            L1 = sp.eval_genlaguerre(k-1,1,z)
            Pmv = sp.lpmv(m,v,x)
            Pmv1 = sp.lpmv(m,v+1,x)
            A = self.Az(v,m,phi)
            zhat = -0.5*e*(L0+2*L1)*Pmv*A*100./RE
            that = e*L0*(-(v+1)*x*Pmv+(v-m+1)*Pmv1)*A/(y*(z/100.+1)*RE)
            phat = e*L0*Pmv*self.dAz(v,m,phi)/(y*(z/100.+1)*RE)
            Ag.append([zhat,that,phat])
        # print np.shape(np.array(Ag).T)
        return np.array(Ag).T

        


    def eval_model(self,R,C,calcgrad=False,calcerr=False,verbose=False):
        """
        Evaluate the density and gradients at the points in R given the coefficients C.
         If the covarience matrix, dC, is provided, the errors in the density and gradients will be calculated.  If not,
         just the density and gradient vectors will be returned by default.

        Parameters:
            R: [ndarray(3,npoints)]
                array of input coordinates
                R = [[z coordinates (m)],[theta coordinates (rad)],[phi coordinates (rad)]]
                if input points are expressed as a list of r,t,p points, eg. points = [[r1,t1,p1],[r2,t2,p2],...], R = np.array(points).T
            calcgrad: [bool]
                indicates if gradients should be calculated
                True (default): gradients WILL be calculated
                False: gradients WILL NOT be calculated
                Setting calcgrad=False if gradients are not required may improve efficiency
            calcerr: [bool]
                indicates if errors on parameters and gradients should be calculated
                True: errors WILL be calculated
                False (default): errors WILL NOT be calculated
            verbose: [bool]
                indicates if function should be run in verbose mode
                This prints a warning if dC is not specified and the errors will not be calculated.
                True: verbose mode is ON
                False (default): verbose mode is OFF
        Returns:
            out: [dict]
                dictionary containing calculated parameter, gradient, and error arrays, as appropriate
                vaild keys:
                    'param': parameter
                    'grad': gradient (if calcgrad=True)
                    'err': error on parameter (if calcerr=True)
                    'gerr': error on gradient (if calcgrad=True AND calcerr=True)
        Notes:
            - A rough framework for error handling has been included in this code, but it has not been used often.
                The method needs to be validated still and there are probably errors in the code.
        """

#         if self.C is None:
#             print 'WARNING: C not specified in Model!'

        R, _ = self.transform_coord(R)

        out = {}
        A = self.eval_basis(R)
        parameter = np.reshape(np.dot(A,C),np.shape(A)[0])
        out['param'] = parameter

        if calcgrad:
            Ag = self.eval_grad_basis(R)
#             gradient = np.reshape(np.tensordot(Ag,self.C,axes=1),(np.shape(Ag)[0],np.shape(Ag)[1]))
            gradient = np.reshape(np.tensordot(Ag,C,axes=1),(np.shape(Ag)[0],np.shape(Ag)[1]))
            out['grad'] = gradient

        if calcerr:
            if self.dC is None:
                if verbose:
                    print('Covariance matrix not provided. Errors will not be calculated.')
            error = np.diag(np.squeeze(np.dot(A,np.dot(self.dC,A.T))))
            out['err'] = error

            if calcgrad:
                gradmat = np.tensordot(Ag,np.tensordot(self.dC,Ag.T,axes=1),axes=1)
                graderr = []
                for i in range(np.shape(gradmat)[0]):
                    graderr.append(np.diag(gradmat[i,:,:,i]))
                graderr = np.array(graderr)
                out['gerr'] = graderr
        return out

        
    def Az(self,v,m,phi):
        """
        Evaluates the azimuthal function

        Parameters:
            v: [double]
                non-integer degree of spherical cap harmonics
            m: [int]
                order of spherical cap harmonics
            phi: [ndarray]
                array of phi values (radians)
        Returns:
            az: [ndarray]
                evaluated azimuthal function at all values of phi 
        """
        if m < 0:
            return self.Kvm(v,abs(m))*np.sin(abs(m)*phi)
        else:
            return self.Kvm(v,abs(m))*np.cos(abs(m)*phi)


    def dAz(self,v,m,phi):
        """
        Evaluates the derivative of the azimuthal function

        Parameters:
            v: [double]
                non-integer degree of spherical cap harmonics
            m: [int]
                order of spherical cap harmonics
            phi: [ndarray]
                array of phi values (radians)
        Returns:
            daz: [ndarray]
                evaluated derivative of the azimuthal function at all values of phi 
        """
        if m < 0:
            return abs(m)*self.Kvm(v,abs(m))*np.cos(abs(m)*phi)
        else:
            return -1*m*self.Kvm(v,abs(m))*np.sin(abs(m)*phi)


    def Kvm(self,v,m):
        """
        Evaluates the constant Kvm associated with spherical harmonics

        Parameters:
            v: [double]
                non-integer degree of spherical cap harmonics
            m: [int]
                order of spherical cap harmonics
        Returns:
            Kvm: [double]
                constant Kvm
        """
        Kvm = np.sqrt((2*v+1)/(4*np.pi)*sp.gamma(float(v-m+1))/sp.gamma(float(v+m+1)))
        if m != 0:
            Kvm = Kvm*np.sqrt(2)
        return Kvm


    def transform_coord(self,R0):
        """
        Transform from spherical coordinates to something friendlier for calculating the basis fit.
        This involves a rotation so that the data is centered around the north pole and a trasformation
         of the radial component such that z = 100*(r/RE-1).

        Parameters:
            R0: [ndarray(3,npoints)]
                array of input points in geocentric coordinates
                R = [[r coordinates (m)],[theta coordinates (rad)],[phi coordinates (rad)]]
                if input points are expressed as a list of r,t,p points, eg. points = [[r1,t1,p1],[r2,t2,p2],...], R = np.array(points).T
        Returns:
            R_trans: [ndarray(3,npoints)]
                array of input points transformed into model coordinates
                R_trans = [[z coordinates],[theta coordinates (rad)],[phi coordinates (rad)]]
            cp: [ndarray(2)]
                center point of the input coordinates R0
        Notes:

        """


        try:
            phi0 = self.cp[1]
            theta0 = self.cp[0]
        except:
            phi0 = np.average(R0[2])
            theta0 = -1*np.average(R0[1])
            self.cp = [theta0,phi0]


        k = np.array([np.cos(phi0+np.pi/2.),np.sin(phi0+np.pi/2.),0.])

        x, y, z = cc.spherical_to_cartesian(R0[0],R0[1],R0[2])
        Rp = np.array([x,y,z])
        Rr = np.array([R*np.cos(theta0)+np.cross(k,R)*np.sin(theta0)+k*np.dot(k,R)*(1-np.cos(theta0)) for R in Rp.T]).T
        r, t, p = cc.cartesian_to_spherical(Rr[0],Rr[1],Rr[2])
        R_trans = np.array([100*(r/RE-1),t,p])

        return R_trans, self.cp



    def inverse_transform(self,R0,vec):
        """
        Inverse transformation to recover the correct vector components at their original position after
         calling eval_model().  This is primarially nessisary to get the gradients correct.

        Parameters:
            R0: [ndarray(3,npoints)]
                array of points in model coordinates corresponding to the location of each vector in vec
            vec: [ndarray(npoints,3)]
                array of vectors in model coordinates
        Returns:
            vec_rot: [ndarray(npoints,3)]
                array of vectors rotated back to original geocenteric coordinates
        """

        phi0 = self.cp[1]
        theta0 = -1.*self.cp[0]

        k = np.array([np.cos(phi0+np.pi/2.),np.sin(phi0+np.pi/2.),0.])

        rx, ry, rz = cc.spherical_to_cartesian((R0[0]/100.+1.)*RE,R0[1],R0[2])
        Rc = np.array([rx,ry,rz])
        vx, vy, vz = cc.vector_spherical_to_cartesian(vec.T[0],vec.T[1],vec.T[2],(R0[0]/100.+1.)*RE,R0[1],R0[2])
        vc = np.array([vx,vy,vz])

        rr = np.array([R*np.cos(theta0)+np.cross(k,R)*np.sin(theta0)+k*np.dot(k,R)*(1-np.cos(theta0)) for R in Rc.T]).T
        vr = np.array([v*np.cos(theta0)+np.cross(k,v)*np.sin(theta0)+k*np.dot(k,v)*(1-np.cos(theta0)) for v in vc.T]).T
        vr, vt, vp = cc.vector_cartesian_to_spherical(vr[0],vr[1],vr[2],rr[0],rr[1],rr[2])

        vec_rot = np.array([vr,vt,vp]).T

        return vec_rot

    