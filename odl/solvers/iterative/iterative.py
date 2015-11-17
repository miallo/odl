# Copyright 2014, 2015 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

"""Simple iterative type optimization schemes."""

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

# External

# Internal
from odl.operator.default_ops import IdentityOperator
from odl.operator.operator import OperatorComp, OperatorSum
__all__ = ()


# TODO: update all docs


def landweber(op, x, rhs, niter=1, omega=1, partial=None):
    """Optimized implementation of Landweber's method.

    This method solves the inverse problem (of the first kind)

    :math:`A (x) = y`

    for a (Frechet-) differentiable operator `A` using the iteration

    :math:`x <- x - \omega * (A')^* (A(x) - y)`

    It uses a minimum amount of memory copies by applying re-usable
    temporaries and in-place evaluation.

    The method is described in a
    `Wikipedia article
    <https://en.wikipedia.org/wiki/Landweber_iteration>`_.

    Parameters
    ----------
    op : `Operator`
        Operator in the inverse problem. It must have a `derivative`
        property, which returns a new operator which in turn has an
        `adjoint` property, i.e. `op.derivative(x).adjoint` must be
        well-defined for `x` in the operator domain.
    x : element of the domain of `op`
        Vector to which the result is written. Its initial value is
        used as starting point of the iteration, and its values are
        updated in each iteration step.
    rhs : element of the range of `op`
        Right-hand side of the equation defining the inverse problem
    niter : int, optional
        Maximum number of iterations
    omega : positive float
        Relaxation parameter, must lie between 0 and :math:`2/||A||`,
        the operator norm of `A`, to guarantee convergence.
    partial : `Partial`, optional
        Object executing code per iteration, e.g. plotting each iterate

    Returns
    -------
    None
    """
    # TODO: add a book reference

    # Reusable temporaries
    tmp_ran = op.range.element()
    tmp_dom = op.domain.element()

    for _ in range(niter):
        op(x, out=tmp_ran)
        tmp_ran -= rhs
        op.derivative(x).adjoint(tmp_ran, out=tmp_dom)
        x.lincomb(1, x, -omega, tmp_dom)

        if partial is not None:
            partial.send(x)


def conjugate_gradient(op, x, rhs, niter=1, partial=None):
    """Optimized implementation of CG for self-adjoint operators.

    This method solves the inverse problem (of the first kind)

    :math:`A x = y`

    for a linear and self-adjoint operator `A`.

    It uses a minimum amount of memory copies by applying re-usable
    temporaries and in-place evaluation.

    The method is described (for linear systems) in a
    `Wikipedia article
    <https://en.wikipedia.org/wiki/Conjugate_gradient_method>`_.

    Parameters
    ----------
    op : `Operator`
        Operator in the inverse problem. It must be linear and
        self-adjoint. This implies in particular that its domain and
        range are equal.
    x : element of the domain of `op`
        Vector to which the result is written. Its initial value is
        used as starting point of the iteration, and its values are
        updated in each iteration step.
    rhs : element of the range of `op`
        Right-hand side of the equation defining the inverse problem
    niter : int, optional
        Maximum number of iterations
    partial : `Partial`, optional
        Object executing code per iteration, e.g. plotting each iterate

    Returns
    -------
    None
    """
    # TODO: add a book reference

    if op.domain != op.range:
        raise TypeError('Operator needs to be self adjoint')

    r = op(x)
    r.lincomb(1, rhs, -1, r)       # r = rhs - A x
    p = r.copy()
    Ap = op.domain.element()  # Extra storage for storing A x

    sqnorm_r_old = r.norm()**2  # Only recalculate norm after update

    for _ in range(niter):
        op(p, out=Ap)  # Ap = A p

        alpha = sqnorm_r_old / p.inner(Ap)

        if alpha == 0.0:  # Return if residual is 0
            return

        x.lincomb(1, x, alpha, p)            # x = x + alpha*p
        r.lincomb(1, r, -alpha, Ap)           # r = r - alpha*p

        sqnorm_r_new = r.norm()**2

        beta = sqnorm_r_new / sqnorm_r_old
        sqnorm_r_old = sqnorm_r_new

        p.lincomb(1, r, beta, p)                       # p = s + b * p

        if partial is not None:
            partial.send(x)


def conjugate_gradient_normal(op, x, rhs, niter=1, partial=None):
    """Optimized implementation of CG for the normal equation.

    This method solves the normal equation

    :math:`A^* A x = A^* y`

    to the inverse problem (of the first kind)

    :math:`A x = y`

    with a linear operator `A`.

    It uses a minimum amount of memory copies by applying re-usable
    temporaries and in-place evaluation.

    The method is described (for linear systems) in a
    `Wikipedia article
    <https://en.wikipedia.org/wiki/Conjugate_gradient_method#\
Conjugate_gradient_on_the_normal_equations>`_.

    Parameters
    ----------
    op : `Operator`
        Operator in the inverse problem. It must be linear and implement
        the `adjoint` property.
    x : element of the domain of `op`
        Vector to which the result is written. Its initial value is
        used as starting point of the iteration, and its values are
        updated in each iteration step.
    rhs : element of the range of `op`
        Right-hand side of the equation defining the inverse problem
    niter : int, optional
        Maximum number of iterations
    partial : `Partial`, optional
        Object executing code per iteration, e.g. plotting each iterate

    Returns
    -------
    None
    """
    # TODO: add a book reference

    d = op(x)
    d.lincomb(1, rhs, -1, d)               # d = rhs - A x
    p = op.derivative(x).adjoint(d)
    s = p.copy()
    q = op.range.element()
    sqnorm_s_old = s.norm()**2  # Only recalculate norm after update

    for _ in range(niter):
        op(p, out=q)                       # q = A p
        sqnorm_q = q.norm()**2
        if sqnorm_q == 0.0:  # Return if residual is 0
            return

        a = sqnorm_s_old / sqnorm_q
        x.lincomb(1, x, a, p)               # x = x + a*p
        d.lincomb(1, d, -a, q)              # d = d - a*Ap
        op.derivative(p).adjoint(d, out=s)  # s = A^T d

        sqnorm_s_new = s.norm()**2
        b = sqnorm_s_new / sqnorm_s_old
        sqnorm_s_old = sqnorm_s_new

        p.lincomb(1, s, b, p)               # p = s + b * p

        if partial is not None:
            partial.send(x)


def exp_zero_seq(base):
    """The default exponential zero sequence.

    It is defined by

        t_0 = 1.0
        t_m = t_(m-1) / base

    or, in closed form

        t_m = base^(-m-1)

    Parameters
    ----------
    base : float
        Base of the sequence. Its absolute value must be larger than
        1.

    Yields
    ------
    val : float
        The next value in the exponential sequence
    """
    value = 1.0
    while True:
        value /= base
        yield value


def gauss_newton(op, x, rhs, niter=1, zero_seq=exp_zero_seq(2.0),
                 partial=None):
    """Optimized implementation of a Gauss-Newton method.

    This method solves the inverse problem (of the first kind)

    :math:`A (x) = y`

    for a (Frechet-) differentiable operator `A` using a
    Gauss-Newton iteration.

    It uses a minimum amount of memory copies by applying re-usable
    temporaries and in-place evaluation.

    A variant of the method applied to a specific problem is described
    in a
    `Wikipedia article
    <https://en.wikipedia.org/wiki/Gauss%E2%80%93Newton_algorithm>`_.

    Parameters
    ----------
    op : `odl.Operator`
        Operator in the inverse problem. It must have a `derivative`
        property, which returns a new operator which in turn has an
        `adjoint` property, i.e. `op.derivative(x).adjoint` must be
        well-defined for `x` in the operator domain.
    x : element of the domain of `op`
        Vector to which the result is written. Its initial value is
        used as starting point of the iteration, and its values are
        updated in each iteration step.
    rhs : element of the range of `op`
        Right-hand side of the equation defining the inverse problem
    niter : int, optional
        Maximum number of iterations
    zero_seq : iterable, optional
        Zero sequence whose values are used for the regularization of
        the linearized problem in each Newton step
    partial : `Partial`, optional
        Object executing code per iteration, e.g. plotting each iterate

    Returns
    -------
    None
    """
    x0 = x.copy()
    I = IdentityOperator(op.domain)
    dx = x.space.zero()

    tmp_dom = op.domain.element()
    u = op.domain.element()
    tmp_ran = op.range.element()
    v = op.range.element()

    for _ in range(niter):
        tm = next(zero_seq)
        deriv = op.derivative(x)
        deriv_adjoint = deriv.adjoint

        # v = rhs - op(x) - deriv(x0-x)
        # u = deriv.T(v)
        op(x, out=tmp_ran)              # eval  op(x)
        v.lincomb(1, rhs, -1, tmp_ran)  # assign  v = rhs - op(x)
        tmp_dom.lincomb(1, x0, -1, x)   # assign temp  tmp_dom = x0 - x
        deriv(tmp_dom, out=tmp_ran)     # eval  deriv(x0-x)
        v -= tmp_ran                    # assign  v = rhs-op(x)-deriv(x0-x)
        deriv_adjoint(v, out=u)         # eval/assign  u = deriv.T(v)

        # Solve equation system
        # (deriv.T o deriv + tm * I)^-1 u = dx
        A = OperatorSum(OperatorComp(deriv.adjoint, deriv),
                        tm * I, tmp_dom)

        # TODO: allow user to select other method
        conjugate_gradient(A, dx, u, 3)

        # Update x
        x.lincomb(1, x0, 1, dx)  # x = x0 + dx

        if partial is not None:
            partial.send(x)

if __name__ == '__main__':
    from doctest import testmod, NORMALIZE_WHITESPACE
    testmod(optionflags=NORMALIZE_WHITESPACE)