# MIT License
#
# Copyright (c) 2020 Archis Joglekar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import numpy as np
from scipy import interpolate


def __get_k__(ax):
    """
    get axis of transformed quantity

    :param ax: axis to transform
    :return:
    """
    return np.fft.fftfreq(ax.size, d=ax[1] - ax[0])


def get_vdfdx_sl(x, v):
    """
    Get the vdfdx Semi-Lagrangian stepper

    :param x:
    :param v:
    :return:
    """
    x_pad = np.zeros(x.size + 2)

    xm, vm = np.meshgrid(x, v, indexing="ij")
    xm = xm.flatten()
    vm = vm.flatten()

    f_pad = np.zeros((x.size + 2, v.size))

    def update_spatial_adv_sl(f, dt):
        """
        evolution of df/dt = v df/dx

        :param f: distribution function. (numpy array of shape (nx, nv))
        :param kx: real-space wavenumber axis (numpy array of shape (nx,))
        :param v: velocity axis (numpy array of shape (nv,))
        :param dt: timestep (single float value)
        :return:
        """

        x_pad[1:-1] = x
        x_pad[0] = x[0] - (x[2] - x[1])
        x_pad[-1] = x[-1] + (x[2] - x[1])

        f_pad[1:-1, :] = f
        f_pad[0, :] = f[-1, :]
        f_pad[-1, :] = f[0, :]

        f_interpolator = interpolate.RectBivariateSpline(x_pad, v, f_pad)
        f_out = f_interpolator(xm - vm * dt, vm, grid=False).reshape((x.size, v.size))

        return f_out

    return update_spatial_adv_sl


def get_vdfdx_exponential(kx, v):
    """
    This function creates the exponential vdfdx stepper

    It uses kx and v as metadata that should stay constant throughout the simulation

    :param kx:
    :param v:
    :return:
    """

    def step_vdfdx_exponential(f, dt):
        """
        evolution of df/dt = v df/dx

        :param f: distribution function. (numpy array of shape (nx, nv))
        :param kx: real-space wavenumber axis (numpy array of shape (nx,))
        :param v: velocity axis (numpy array of shape (nv,))
        :param dt: timestep (single float value)
        :return:
        """

        return np.real(
            np.fft.ifft(
                np.exp(-1j * kx[:, None] * dt * v) * np.fft.fft(f, axis=0), axis=0
            )
        )

    return step_vdfdx_exponential


def get_edfdv_exponential(kv):
    """
    This function creates the exponential edfdv stepper

    It uses kv as metadata that should stay constant throughout the simulation

    :param kv:
    :return:
    """

    def step_edfdv_exponential(f, e, dt):
        """
        evolution of df/dt = e df/dv

        :param f: distribution function. (numpy array of shape (nx, nv))
        :param kv: velocity-space wavenumber axis (numpy array of shape (nv,))
        :param e: electric field (numpy array of shape (nx,))
        :param dt: timestep (single float value)
        :return:
        """

        return np.real(
            np.fft.ifft(
                np.exp(-1j * kv * dt * e[:, None]) * np.fft.fft(f, axis=1), axis=1
            )
        )

    return step_edfdv_exponential


def get_edfdv_center_differenced(dv):
    """
    This function creates the center differenced edfdv stepper

    It uses dv as metadata that should stay constant throughout the simulation

    :param dv:
    :return:
    """

    def step_edfdv_center_difference(f, e, dt):
        """
        This method calculates the f + dt * e * df/dv using naive
        2nd-order center differencing

        :param f:
        :param e:
        :param dt:
        :return:
        """
        return f - e[:, None] * np.gradient(f, dv, axis=1, edge_order=2) * dt

    return step_edfdv_center_difference


def get_edfdv_sl(x, v):
    """
    Get the vdfdx Semi-Lagrangian stepper

    :param x:
    :param v:
    :return:
    """
    v_pad = np.zeros(v.size + 2)
    xm, vm = np.meshgrid(x, v, indexing="ij")
    xm = xm.flatten()
    vm = vm.flatten()

    f_pad = np.zeros((x.size, v.size + 2))

    def update_velocity_adv_sl(f, e, dt):
        """
        evolution of df/dt = e df/dv

        :param f: distribution function. (numpy array of shape (nx, nv))
        :param kv: velocity-space wavenumber axis (numpy array of shape (nv,))
        :param e: electric field (numpy array of shape (nx,))
        :param dt: timestep (single float value)
        :return:
        """

        v_pad[1:-1] = v
        v_pad[0] = v[0] - (v[2] - v[1])
        v_pad[-1] = v[-1] + (v[2] - v[1])

        f_pad[:, 1:-1] = f
        f_pad[:, 0] = f[:, -1]
        f_pad[:, -1] = f[:, 0]

        e_fit = interpolate.interp1d(x, e, kind="cubic")

        em = e_fit(xm)

        f_interpolator = interpolate.RectBivariateSpline(x, v_pad, f_pad)
        f_out = f_interpolator(xm, vm - em * dt, grid=False).reshape((x.size, v.size))

        return f_out

    return update_velocity_adv_sl


def get_vdfdx(stuff_for_time_loop, vdfdx_implementation="exponential"):
    """
    This function enables VlaPy to choose the implementation of the vdfdx stepper
    to use in the lower level sections of the simulation

    :param stuff_for_time_loop:
    :param vdfdx_implementation:
    :return:
    """
    if vdfdx_implementation == "exponential":
        vdfdx = get_vdfdx_exponential(
            kx=stuff_for_time_loop["kx"], v=stuff_for_time_loop["v"]
        )
    elif vdfdx_implementation == "sl":
        vdfdx = get_vdfdx_sl(x=stuff_for_time_loop["x"], v=stuff_for_time_loop["v"])
    else:
        raise NotImplementedError

    return vdfdx


def get_edfdv(stuff_for_time_loop, edfdv_implementation="exponential"):
    """
    This function enables VlaPy to choose the implementation of the edfdv stepper
    to use in the lower level sections of the simulation

    :param stuff_for_time_loop:
    :param edfdv_implementation:
    :return:
    """
    if edfdv_implementation == "exponential":
        edfdv = get_edfdv_exponential(kv=stuff_for_time_loop["kv"])
    elif edfdv_implementation == "cd2":
        edfdv = get_edfdv_center_differenced(dv=stuff_for_time_loop["dv"])
    elif edfdv_implementation == "sl":
        edfdv = get_edfdv_sl(v=stuff_for_time_loop["v"], x=stuff_for_time_loop["x"])
    else:
        raise NotImplementedError

    return edfdv