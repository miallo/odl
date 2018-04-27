# coding=utf-8

# Copyright 2014-2017 The ODL contributors
#
# This file is part of ODL.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import print_function, division, absolute_import
import numpy as np

from odl.operator.operator import (
    Operator, OperatorComp, OperatorLeftScalarMult, OperatorRightScalarMult,
    OperatorRightVectorMult, OperatorSum, OperatorPointwiseProduct)
from odl.operator.default_ops import (IdentityOperator, ConstantOperator)
from odl.solvers.nonsmooth import (proximal_arg_scaling, proximal_translation,
                                   proximal_quadratic_perturbation,
                                   proximal_const_func, proximal_convex_conj)
from odl.util import signature_string, indent


__all__ = ('Functional', 'FunctionalLeftScalarMult',
           'FunctionalRightScalarMult', 'FunctionalComp',
           'FunctionalRightVectorMult', 'FunctionalSum', 'FunctionalScalarSum',
           'FunctionalTranslation', 'InfimalConvolution',
           'FunctionalQuadraticPerturb', 'FunctionalProduct',
           'FunctionalQuotient', 'BregmanDistance', 'simple_functional')


class Functional(Operator):

    """Implementation of a functional class.

    A functional is an operator ``f`` that maps from some domain ``X`` to the
    field of scalars ``F`` associated with the domain:

        ``f : X -> F``.

    Notes
    -----
    The implementation of the functional class assumes that the domain
    :math:`X` is a Hilbert space and that the field of scalars :math:`F` is a
    is the real numbers. It is possible to create functions that do not fulfil
    these assumptions, however some mathematical results might not be valid in
    this case. For more information, see `the ODL functional guide
    <http://odlgroup.github.io/odl/guide/in_depth/functional_guide.html>`_.
    """

    def __init__(self, domain, linear=False, grad_lipschitz=np.nan,range=None):
        """Initialize a new instance.

        Parameters
        ----------
        domain : `LinearSpace`
            The domain of this functional, i.e., the set of elements to
            which this functional can be applied.
        linear : bool, optional
            If `True`, the functional is considered as linear.
        grad_lipschitz : float, optional
            The Lipschitz constant of the gradient. Default: ``nan``
        """
        # Cannot use `super(Functional, self)` here since that breaks
        # subclasses with multiple inheritance (at least those where both
        # parents implement `__init__`, e.g., in `ScalingFunctional`)
#        print(range)
        if range is None:
            range = domain.field
        elif range != domain.field:
            linear = False
        Operator.__init__(self, domain=domain, range=range, linear=linear)
        self.__grad_lipschitz = float(grad_lipschitz)

    @property
    def grad_lipschitz(self):
        """Lipschitz constant for the gradient of the functional"""
        return self.__grad_lipschitz

    @grad_lipschitz.setter
    def grad_lipschitz(self, value):
        """Setter for the Lipschitz constant for the gradient."""
        self.__grad_lipschitz = float(value)

    @property
    def gradient(self):
        """Gradient operator of the functional.

        Notes
        -----
        The operator that corresponds to the mapping

        .. math::
            x \\to \\nabla f(x)

        where :math:`\\nabla f(x)` is the element used to evaluate
        derivatives in a direction :math:`d` by
        :math:`\\langle \\nabla f(x), d \\rangle`.
        """
        raise NotImplementedError(
            'no gradient implemented for functional {!r}'
            ''.format(self))

    @property
    def proximal(self):
        """Proximal factory of the functional.

        Notes
        -----
        The proximal operator of a function :math:`f` is an operator defined as

        .. math::
            prox_{\\sigma f}(x) = \\sup_{y} \\left\{ f(y) -
            \\frac{1}{2\\sigma} \| y-x \|_2^2 \\right\}.

        Proximal operators are often used in different optimization algorithms,
        especially when designed to handle nonsmooth functionals.

        A `proximal factory` is a function that, when called with a step
        length :math:`\\sigma`, returns the corresponding proximal operator.

        The nonsmooth solvers that make use of proximal operators to solve a
        given optimization problem take a `proximal factory` as input,
        i.e., a function returning a proximal operator. See for example
        `forward_backward_pd`.

        In general, the step length :math:`\\sigma` is expected to be a
        positive float, but certain functionals might accept more types of
        objects as a stepsize:

        * If a functional is a `SeparableSum`, then, instead of a positive
        float, one may call the `proximal factory` with a list of positive
        floats, and the stepsize are applied to each component individually.

        * For certain special functionals like `L1Norm` and `L2NormSquared`,
        which are not implemented as a `SeparableSum`, the proximal factory
        will accept an argument which is `element-like` regarding the domain
        of the functional. Its components must be strictly positive floats.

        A stepsize like :math:`(\\sigma_1, \\ldots, \\sigma_n)`  coincides
        with a matrix-valued distance according to Section XV.4 of _[HL1993]
        and the rule

        .. math::
            M = \\mathrm{diag}(\\sigma_1^{-1}, \\ldots, \\sigma_n^{-1})

        or the Bregman-proximal according to _[E1993] and the rule

        .. math::
            h(x) = \langle x, M x \rangle.

        References
        ----------
        [HL1993] Hiriart-Urruty J-B, and Lemaréchal C. *Convex analysis and
        minimization algorithms II. Advanced theory and bundle methods.*
        Springer, 1993.

        [E1993] Eckstein J. *Nonlinear proximal point algorithms using Bregman
        functions, with applications to convex programming.* Mathematics of
        Operations Research, 18.1 (1993), pp 202--226.
        """
        raise NotImplementedError(
            'no proximal operator implemented for functional {!r}'
            ''.format(self))

    @property
    def convex_conj(self):
        """Convex conjugate functional of the functional.

        Notes
        -----
        The convex conjugate functional of a convex functional :math:`f(x)`,
        defined on a Hilber space, is defined as the functional

        .. math::
            f^*(x^*) = \\sup_{x} \{ \\langle x^*,x \\rangle - f(x)  \}.

        The concept is also known as the Legendre transformation.

        For literature references see, e.g., [Lue1969], [Roc1970], the
        wikipedia article on `Convex conjugate
        <https://en.wikipedia.org/wiki/Convex_conjugate>`_ or the wikipedia
        article on the `Legendre transformation
        <https://en.wikipedia.org/wiki/Legendre_transformation>`_.

        References
        ----------
        [Lue1969] Luenberger, D G. *Optimization by vector space methods*.
        Wiley, 1969.

        [Roc1970] Rockafellar, R. T. *Convex analysis*. Princeton
        University Press, 1970.
        """
        return FunctionalDefaultConvexConjugate(self)

    def derivative(self, point):
        """Return the derivative operator in the given point.

        This function returns the linear operator given by::

            self.derivative(point)(x) == self.gradient(point).inner(x)

        Parameters
        ----------
        point : `domain` element
            The point in which the gradient is evaluated.

        Returns
        -------
        derivative : `Operator`
        """
        
        return self.gradient(point).T

    def translated(self, shift):
        """Return a translation of the functional.

        For a given functional ``f`` and an element ``translation`` in the
        domain of ``f``, this operation creates the functional
        ``f(. - translation)``.

        Parameters
        ----------
        translation : `domain` element
            Element in the domain of the functional

        Returns
        -------
        out : `FunctionalTranslation`
            The functional ``f(. - translation)``
        """
        return FunctionalTranslation(self, shift)

    def bregman(self, point, subgrad=None):
        """Return the Bregman distance functional.

        Parameters
        ----------
        point : element of ``functional.domain``
            Point from which to define the Bregman distance.
        subgrad : `Operator`, optional
            A subgradient operator. Operator which that takes an element in
            `functional.domain` and returns a subdifferential of the functional
            in that point.
            Default: ``functional.gradient``.

        Returns
        -------
        out : `BregmanDistance`
            The Bregman distance functional.

        Notes
        -----
        Given a functional :math:`f`, which has a (sub)gradient
        :math:`\partial f`, and given a point :math:`y`, the Bregman distance
        functional :math:`D_f(\cdot, y)` in a point :math:`x` is given by

        .. math::
            D_f(x, y) = f(x) - f(y) - \\langle \partial f(y), x - y \\rangle.


        For mathematical details, see `[Bur2016]`_.

        References
        ----------
        Wikipedia article: https://en.wikipedia.org/wiki/Bregman_divergence

        [Bur2016] Burger, M. *Bregman Distances in Inverse Problems and Partial
        Differential Equation*. In: Advances in Mathematical Modeling,
        Optimization and Optimal Control, 2016. p. 3-33.

        .. _[Bur2016]:  https://arxiv.org/abs/1505.05191
        """
        return BregmanDistance(self, point, subgrad)

    def __mul__(self, other):
        """Return ``self * other``.

        If ``other`` is an `Operator`, this corresponds to composition with the
        operator:

            ``(func * op)(x) == func(op(x))``

        If ``other`` is a scalar, this corresponds to right multiplication of
        scalars with functionals:

            ``(func * scalar)(x) == func(scalar * x)``

        If ``other`` is a vector, this corresponds to right multiplication of
        vectors with functionals:

            ``(func * vector) == func(vector * x)``

        Note that left and right multiplications are generally different.

        Parameters
        ----------
        other : `Operator`, `domain` element or scalar
            `Operator`:
            The `Operator.range` of ``other`` must match this functional's
            `domain`.

            `domain` element:
            ``other`` must be an element of this functionals's
            `Functional.domain`.

            scalar:
            The `domain` of this functional must be a
            `LinearSpace` and ``other`` must be an element of the `field`
            of this functional's `domain`. Note that this `field` is also this
            functional's `range`.

        Returns
        -------
        mul : `Functional`
            Multiplication result.

            If ``other`` is an `Operator`, ``mul`` is a
            `FunctionalComp`.

            If ``other`` is a scalar, ``mul`` is a
            `FunctionalRightScalarMult`.

            If ``other`` is a vector, ``mul`` is a
            `FunctionalRightVectorMult`.
        """
        if isinstance(other, Operator):
            return FunctionalComp(self, other)
        elif other in self.range:
            # Left multiplication is more efficient, so we can use this in the
            # case of linear functional.
            if other == 0:
                from odl.solvers.functional.default_functionals import (
                    ConstantFunctional)
                return ConstantFunctional(self.domain,
                                          self(self.domain.zero()))
            elif self.is_linear:
                return FunctionalLeftScalarMult(self, other)
            else:
                return FunctionalRightScalarMult(self, other)
        elif other in self.domain:
            return FunctionalRightVectorMult(self, other)
        else:
            return super(Functional, self).__mul__(other)

    def __rmul__(self, other):
        """Return ``other * self``.

        If ``other`` is an `Operator`, since a functional is also an operator
        this corresponds to operator composition:

            ``(op * func)(x) == op(func(x))``

        If ``other`` is a scalar, this corresponds to left multiplication of
        scalars with functionals:

            ``(scalar * func)(x) == scalar * func(x)``

        If ``other`` is a vector,  since a functional is also an operator this
        corresponds to left multiplication of vectors with operators:

            ``(vector * func)(x) == vector * func(x)``

        Note that left and right multiplications are generally different.

        Parameters
        ----------
        other : `Operator`, `domain` element or scalar
            `Operator`:
            The `Operator.domain` of ``other`` must match this functional's
            `Functional.range`.

            `LinearSpaceElement`:
            ``other`` must be an element of this functionals's
            `Functional.range`.

            scalar:
            The `Operator.domain` of this operator must be a
            `LinearSpace` and ``other`` must be an
            element of the ``field`` of this operator's
            `Operator.domain`.

        Returns
        -------
        rmul : `Functional` or `Operator`
            Multiplication result.

            If ``other`` is an `Operator`, ``rmul`` is an `OperatorComp`.

            If ``other`` is a scalar, ``rmul`` is a
            `FunctionalLeftScalarMult`.

            If ``other`` is a vector, ``rmul`` is a
            `OperatorLeftVectorMult`.
        """
        if other in self.range:
            if other == 0:
                from odl.solvers.functional.default_functionals import (
                    ZeroFunctional)
                return ZeroFunctional(self.domain)
            else:
                return FunctionalLeftScalarMult(self, other)
        else:
            return super(Functional, self).__rmul__(other)

    def __add__(self, other):
        """Return ``self + other``.

        If ``other`` is a `Functional`, this corresponds to

            ``(func1 + func2)(x) == func1(x) + func2(x)``

        If ``other`` is a scalar, this corresponds to adding a scalar to the
        value of the functional:

            ``(func + scalar)(x) == func(x) + scalar``

        Parameters
        ----------
        other : `Functional` or scalar
            `Functional`:
            The `Functional.domain` and `Functional.range` of ``other``
            must match this functional's  `Functional.domain` and
            `Functional.range`.

            scalar:
            The scalar needs to be in this functional's `Functional.range`.

        Returns
        -------
        sum : `Functional`
            Addition result.

            If ``other`` is in ``Functional.range``, ``sum`` is a
            `FunctionalScalarSum`.

            If ``other`` is a `Functional`, ``sum`` is a `FunctionalSum`.
        """
#        print(other,self.domain)
        if other in self.domain.field:
            return FunctionalScalarSum(self, other)
        elif isinstance(other, Functional):
            return FunctionalSum(self, other)
        else:
            return super(Functional, self).__add__(other)

    # Since addition is commutative, right and left addition is the same
    __radd__ = __add__

    def __sub__(self, other):
        """Return ``self - other``."""
        return self + (-1) * other


class FunctionalLeftScalarMult(Functional, OperatorLeftScalarMult):

    """Scalar multiplication of functional from the left.

    Given a functional ``f`` and a scalar ``scalar``, this represents the
    functional

        ``(scalar * f)(x) == scalar * f(x)``.

    `Functional.__rmul__` takes care of the case scalar = 0.
    """

    def __init__(self, func, scalar):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            Functional to be scaled.
        scalar : float, nonzero
            Number with which to scale the functional.
        """
        if not isinstance(func, Functional):
            raise TypeError('`func` {!r} is not a `Functional` instance'
                            ''.format(func))

        Functional.__init__(
            self, domain=func.domain, linear=func.is_linear,
            grad_lipschitz=np.abs(scalar) * func.grad_lipschitz,
            range=func.range)
        OperatorLeftScalarMult.__init__(self, operator=func, scalar=scalar)

    @property
    def functional(self):
        """The original functional."""
        return self.operator

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        return self.scalar * self.functional.gradient

    @property
    def convex_conj(self):
        """Convex conjugate functional of the scaled functional.

        `Functional.__rmul__` takes care of the case scalar = 0.
        """
        if self.scalar <= 0:
            raise ValueError('scaling with nonpositive values have no convex '
                             'conjugate. Current value: {}.'
                             ''.format(self.scalar))

        return self.scalar * self.functional.convex_conj * (1.0 / self.scalar)

    @property
    def proximal(self):
        """Proximal factory of the scaled functional.

        `Functional.__rmul__` takes care of the case scalar = 0

        See Also
        --------
        proximal_const_func
        """

        if self.scalar < 0:
            raise ValueError('proximal operator of functional scaled with a '
                             'negative value {} is not well-defined'
                             ''.format(self.scalar))

        elif self.scalar == 0:
            # Should not get here. `Functional.__rmul__` takes care of the case
            # scalar = 0
            return proximal_const_func(self.domain)

        else:
            def proximal_left_scalar_mult(sigma=1.0):
                """Proximal operator for left scalar multiplication.

                    Parameters
                    ----------
                    sigma : positive float, optional
                        Step size parameter. Default: 1.0
                """
                return self.functional.proximal(sigma * self.scalar)

            return proximal_left_scalar_mult


class FunctionalRightScalarMult(Functional, OperatorRightScalarMult):

    """Scalar multiplication of the argument of functional.

    Given a functional ``f`` and a scalar ``scalar``, this represents the
    functional

        ``(f * scalar)(x) == f(scalar * x)``.

    `Functional.__mul__` takes care of the case scalar = 0.
    """

    def __init__(self, func, scalar):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            The functional which will have its argument scaled.
        scalar : float, nonzero
            The scaling parameter with which the argument is scaled.
        """

        if not isinstance(func, Functional):
            raise TypeError('`func` {!r} is not a `Functional` instance'
                            ''.format(func))

        scalar = func.domain.field.element(scalar)

        Functional.__init__(
            self, domain=func.domain, linear=func.is_linear,
            grad_lipschitz=np.abs(scalar) * func.grad_lipschitz,
            range=func.range)
        OperatorRightScalarMult.__init__(self, operator=func, scalar=scalar)

    @property
    def functional(self):
        """The original functional."""
        return self.operator

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        return self.scalar * self.functional.gradient * self.scalar

    @property
    def convex_conj(self):
        """Convex conjugate functional of functional with scaled argument.

        `Functional.__mul__` takes care of the case scalar = 0.
        """
        return self.functional.convex_conj * (1 / self.scalar)

    @property
    def proximal(self):
        """Proximal factory of the functional.

        See Also
        --------
        proximal_arg_scaling
        """
        return proximal_arg_scaling(self.functional.proximal, self.scalar)


class FunctionalComp(Functional, OperatorComp):

    """Composition of a functional with an operator.

    Given a functional ``func`` and an operator ``op``, such that the range of
    the operator is equal to the domain of the functional, this corresponds to
    the functional

        ``(func * op)(x) == func(op(x))``.
    """

    def __init__(self, func, op):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            The left ("outer") operator
        op : `Operator`
            The right ("inner") operator. Its range must coincide with the
            domain of ``func``.
        """
        if not isinstance(func, Functional):
            raise TypeError('`fun` {!r} is not a `Functional` instance'
                            ''.format(func))

        OperatorComp.__init__(self, left=func, right=op)
        Functional.__init__(self, domain=op.domain,
                            linear=(func.is_linear and op.is_linear),
                            grad_lipschitz=np.nan, range=func.range)

    @property
    def gradient(self):
        """Gradient of the compositon according to the chain rule."""
        func = self.left
        op = self.right

        class FunctionalCompositionGradient(Operator):

            """Gradient of the compositon according to the chain rule."""

            def __init__(self):
                """Initialize a new instance."""
                super(FunctionalCompositionGradient, self).__init__(
                    op.domain, op.domain, linear=False)

            def _call(self, x):
                """Apply the gradient operator to the given point."""
                return op.derivative(x).adjoint(func.gradient(op(x)))

            def derivative(self, x):
                """The derivative in point ``x``.

                This is only defined
                """
                if not op.is_linear:
                    raise NotImplementedError('derivative only implemented '
                                              'for linear opertors.')
                else:
                    return (op.adjoint * func.gradient * op).derivative(x)

        return FunctionalCompositionGradient()


class FunctionalRightVectorMult(Functional, OperatorRightVectorMult):

    """Expression type for the functional right vector multiplication.

    Given a functional ``func`` and a vector ``y`` in the domain of ``func``,
    this corresponds to the functional

        ``(func * y)(x) == func(y * x)``.
    """

    def __init__(self, func, vector):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            The domain of ``func`` must be a ``vector.space``.
        vector : `domain` element
            The vector to multiply by.
        """
        if not isinstance(func, Functional):
            raise TypeError('`fun` {!r} is not a `Functional` instance'
                            ''.format(func))

        OperatorRightVectorMult.__init__(self, operator=func, vector=vector)
        # HELP: before it was Functional.__init__(self, domain=func.domain).
        # But doesn't this loose the information on grad_lipschitz and linear?
        Functional.__init__(self, domain=func.domain,
                            grad_lipschitz=func.grad_lipschitz,
                            linear=func.is_linear,
                            range=func.range)

    @property
    def functional(self):
        return self.operator

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        return self.vector * self.operator.gradient * self.vector

    @property
    def convex_conj(self):
        """Convex conjugate functional of the functional.

        This is only defined for vectors with no zero-elements.
        """
        return self.functional.convex_conj * (1.0 / self.vector)


class FunctionalSum(Functional, OperatorSum):

    """Expression type for the sum of functionals.

    ``FunctionalSum(func1, func2) == (x --> func1(x) + func2(x))``.
    """

    def __init__(self, left, right):
        """Initialize a new instance.

        Parameters
        ----------
        left, right : `Functional`
            The summands of the functional sum. Their `Functional.domain`
            and `Functional.range` must coincide.
        """
        if not isinstance(left, Functional):
            raise TypeError('`left` {!r} is not a `Functional` instance'
                            ''.format(left))
        if not isinstance(right, Functional):
            raise TypeError('`right` {!r} is not a `Functional` instance'
                            ''.format(right))
        if left.range!=right.range:
            raise TypeError('The ranges of `functionals` {!r} and {!r} '
                            'are not equal'.format(left, right))
        Functional.__init__(
            self, domain=left.domain,
            linear=(left.is_linear and right.is_linear),
            grad_lipschitz=left.grad_lipschitz + right.grad_lipschitz,
            range=left.range)
        OperatorSum.__init__(self, left, right)

    @property
    def gradient(self):
        """Gradient operator of functional sum."""
        return self.left.gradient + self.right.gradient


class FunctionalScalarSum(FunctionalSum):

    """Expression type for the sum of a functional and a scalar.

    ``FunctionalScalarSum(func, scalar) == (x --> func(x) + scalar)``
    """

    def __init__(self, func, scalar):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            Functional to which the scalar is added.
        scalar : `element` in the `field` of the ``domain``
            The scalar to be added to the functional. The `field` of the
            ``domain`` is the range of the functional.
        """
        from odl.solvers.functional.default_functionals import (
            ConstantFunctional)

        if not isinstance(func, Functional):
            raise TypeError('`fun` {!r} is not a `Functional` instance'
                            ''.format(func))
        if scalar not in func.range:
            raise TypeError('`scalar` {} is not in the range of '
                            '`func` {!r}'.format(scalar, func))

        super(FunctionalScalarSum, self).__init__(
            left=func,
            right=ConstantFunctional(domain=func.domain, constant=scalar))

    @property
    def scalar(self):
        """The scalar that is added to the functional"""
        return self.right.constant

    @property
    def proximal(self):
        """Proximal factory of the FunctionalScalarSum."""
        return self.left.proximal

    @property
    def convex_conj(self):
        """Convex conjugate functional of FunctionalScalarSum."""
        return self.left.convex_conj - self.scalar


class FunctionalTranslation(Functional):

    """Implementation of the translated functional.

    Given a functional ``f`` and an element ``translation`` in the domain of
    ``f``, this corresponds to the functional ``f(. - translation)``.
    """

    def __init__(self, func, translation):
        """Initialize a new instance.

        Given a functional ``f(.)`` and a vector ``translation`` in the domain
        of ``f``, this corresponds to the functional ``f(. - translation)``.

        Parameters
        ----------
        func : `Functional`
            Functional which is to be translated.
        translation : `domain` element
            The translation.
        """
        if not isinstance(func, Functional):
            raise TypeError('`func` {!r} not a `Functional` instance'
                            ''.format(func))

        translation = func.domain.element(translation)

        super(FunctionalTranslation, self).__init__(
            domain=func.domain, linear=False,
            grad_lipschitz=func.grad_lipschitz)

        # TODO: Add case if we have translation -> scaling -> translation?
        if isinstance(func, FunctionalTranslation):
            self.__functional = func.functional
            self.__translation = func.translation + translation

        else:
            self.__functional = func
            self.__translation = translation

    @property
    def functional(self):
        """The original functional that has been translated."""
        return self.__functional

    @property
    def translation(self):
        """The translation."""
        return self.__translation

    def _call(self, x):
        """Evaluate the functional in a point ``x``."""
        return self.functional(x - self.translation)

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        return (self.functional.gradient *
                (IdentityOperator(self.domain) - self.translation))

    @property
    def proximal(self):
        """Proximal factory of the translated functional.

        See Also
        --------
        odl.solvers.nonsmooth.proximal_operators.proximal_translation
        """
        return proximal_translation(self.functional.proximal,
                                    self.translation)

    @property
    def convex_conj(self):
        """Convex conjugate functional of the translated functional.

        Notes
        -----
        Given a functional :math:`f`, the convex conjugate of a translated
        version :math:`f(\cdot - y)` is given by a linear pertubation of the
        convex conjugate of :math:`f`:

        .. math::
            (f( . - y))^* (x) = f^*(x) + <y, x>.

        For reference on the identity used, see [KP2015].

        References
        ----------
        [KP2015] Komodakis, N, and Pesquet, J-C. *Playing with Duality: An
        overview of recent primal-dual approaches for solving large-scale
        optimization problems*. IEEE Signal Processing Magazine, 32.6 (2015),
        pp 31--54.
        """
        return FunctionalQuadraticPerturb(
            self.functional.convex_conj,
            linear_term=self.translation)

    def __repr__(self):
        """Return ``repr(self)``."""
        return '{!r}.translated({!r})'.format(self.functional,
                                              self.translation)

    def __str__(self):
        """Return ``str(self)``."""
        return '{}.translated({})'.format(self.functional,
                                          self.translation)


class InfimalConvolution(Functional):

    """Functional representing ``h(x) = inf_y f(x-y) + g(y)``."""

    def __init__(self, left, right):
        """Initialize a new instance.

        Parameters
        ----------
        left : `Functional`
            Function corresponding to ``f``.
        right : `Functional`
            Function corresponding to ``g``.

        Examples
        --------
        >>> space = odl.rn(3)
        >>> l1 = odl.solvers.L1Norm(space)
        >>> l2 = odl.solvers.L2Norm(space)
        >>> f = odl.solvers.InfimalConvolution(l1.convex_conj, l2.convex_conj)
        >>> x = f.domain.one()
        >>> f.convex_conj(x) - (l1(x) + l2(x))
        0.0
        """
        if not isinstance(left, Functional):
            raise TypeError('`func` {} is not a `Functional` instance'
                            ''.format(left))

        if not isinstance(right, Functional):
            raise TypeError('`func` {} is not a `Functional` instance'
                            ''.format(right))

        super(InfimalConvolution, self).__init__(
            domain=left.domain, linear=False, grad_lipschitz=np.nan,
            range=left.range)
        self.__left = left
        self.__right = right

    @property
    def left(self):
        """Left functional."""
        return self.__left

    @property
    def right(self):
        """Right functional."""
        return self.__right

    @property
    def convex_conj(self):
        """Convex conjugate functional of the functional.

        Notes
        -----
        The convex conjugate of the infimal convolution

        .. math::
            h(x) = inf_y f(x-y) + g(y)

        is the sum of it:

        .. math::
            h^*(x) = f^*(x) + g^*(x)

        """
        return self.left.convex_conj + self.right.convex_conj

    def __repr__(self):
        """Return ``repr(self)``."""
        posargs = [self.left, self.right]
        inner_str = signature_string(posargs, [], sep=',\n')
        return '{}(\n{}\n)'.format(self.__class__.__name__, indent(inner_str))

    def __str__(self):
        """Return ``str(self)``."""
        return repr(self)


class FunctionalQuadraticPerturb(Functional):

    """The functional representing ``F(.) + a * <., .> + <., u> + c``."""

    def __init__(self, func, quadratic_coeff=0, linear_term=None,
                 constant=0):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            Function corresponding to ``f``.
        quadratic_coeff : ``domain.field`` element, optional
            Coefficient of the quadratic term. Default: 0.
        linear_term : `domain` element, optional
            Element in domain of ``func``, corresponding to the translation.
            Default: Zero element.
        constant : ``domain.field`` element, optional
            The constant coefficient. Default: 0.
        """
        if not isinstance(func, Functional):
            raise TypeError('`func` {} is not a `Functional` instance'
                            ''.format(func))

        self.__functional = func
        quadratic_coeff = func.domain.field.element(quadratic_coeff)
        if quadratic_coeff.imag != 0:
            raise ValueError(
                "Complex-valued quadratic coefficient is not supported.")
        self.__quadratic_coeff = quadratic_coeff.real

        if linear_term is not None:
            self.__linear_term = func.domain.element(linear_term)
        else:
            self.__linear_term = func.domain.zero()

        if linear_term is None:
            grad_lipschitz = func.grad_lipschitz
        else:
            grad_lipschitz = (func.grad_lipschitz + self.linear_term.norm())

        constant = func.domain.field.element(constant)
        if constant.imag != 0:
            raise ValueError(
                "Complex-valued `constant` coefficient is not supported.")
        self.__constant = constant.real
        #HELP: Need to check for range? The + should take care of it, right?
        super(FunctionalQuadraticPerturb, self).__init__(
            domain=func.domain,
            linear=func.is_linear and (quadratic_coeff == 0),
            grad_lipschitz=grad_lipschitz, range=func.range)

    @property
    def functional(self):
        """Original functional."""
        return self.__functional

    @property
    def quadratic_coeff(self):
        """Cofficient of the quadratic term."""
        return self.__quadratic_coeff

    @property
    def linear_term(self):
        """Linear term."""
        return self.__linear_term

    @property
    def constant(self):
        """The constant coefficient."""
        return self.__constant

    def _call(self, x):
        """Apply the functional to the given point."""
        return (self.functional(x) +
                self.quadratic_coeff * x.inner(x) +
                x.inner(self.linear_term) + self.constant)

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        return (self.functional.gradient +
                (2 * self.quadratic_coeff) * IdentityOperator(self.domain) +
                ConstantOperator(self.linear_term))

    @property
    def proximal(self):
        """Proximal factory of the quadratically perturbed functional."""
        if self.quadratic_coeff < 0:
            raise TypeError('`quadratic_coeff` {} must be non-negative'
                            ''.format(self.quadratic_coeff))

        return proximal_quadratic_perturbation(
            self.functional.proximal,
            a=self.quadratic_coeff, u=self.linear_term)

    @property
    def convex_conj(self):
        """Convex conjugate functional of the functional.

        Notes
        -----
        Given a functional :math:`f`, the convex conjugate of a linearly
        perturbed version :math:`f(x) + <y, x>` is given by a translation of
        the convex conjugate of :math:`f`:

        .. math::
            (f + \\langle y, \cdot \\rangle)^* (x^*) = f^*(x^* - y).

        For reference on the identity used, see `[KP2015]`_. Moreover, the
        convex conjugate of :math:`f + c` is by definition

        .. math::
            (f + c)^* (x^*) = f^*(x^*) - c.


        References
        ----------
        [KP2015] Komodakis, N, and Pesquet, J-C. *Playing with Duality: An
        overview of recent primal-dual approaches for solving large-scale
        optimization problems*. IEEE Signal Processing Magazine, 32.6 (2015),
        pp 31--54.

        .. _[KP2015]:  https://arxiv.org/abs/1406.5429
        """
        if self.quadratic_coeff == 0:
            return (self.functional.convex_conj.translated(
                self.linear_term) - self.constant)
        else:
            return super(FunctionalQuadraticPerturb, self).convex_conj

    def __repr__(self):
        """Return ``repr(self)``."""
        return '{}({!r}, {!r}, {!r}, {!r})'.format(self.__class__.__name__,
                                                   self.functional,
                                                   self.quadratic_coeff,
                                                   self.linear_term,
                                                   self.constant)

    def __str__(self):
        """Return ``str(self)``."""
        return '{}({}, {}, {}, {})'.format(self.__class__.__name__,
                                           self.functional,
                                           self.quadratic_coeff,
                                           self.linear_term,
                                           self.constant)


class FunctionalProduct(Functional, OperatorPointwiseProduct):

    """Product ``p(x) = f(x) * g(x)`` of two functionals ``f`` and ``g``."""

    def __init__(self, left, right):
        """Initialize a new instance.

        Parameters
        ----------
        left, right : `Functional`
            Functionals in the product. Need to have matching domains.

        Examples
        --------
        Construct the functional || . ||_2^2 * 3

        >>> space = odl.rn(2)
        >>> func1 = odl.solvers.L2NormSquared(space)
        >>> func2 = odl.solvers.ConstantFunctional(space, 3)
        >>> prod = odl.solvers.FunctionalProduct(func1, func2)
        >>> prod([2, 3])  # expect (2**2 + 3**2) * 3 = 39
        39.0
        """
        if not isinstance(left, Functional):
            raise TypeError('`left` {} is not a `Functional` instance'
                            ''.format(left))
        if not isinstance(right, Functional):
            raise TypeError('`right` {} is not a `Functional` instance'
                            ''.format(right))
        #HELP: Check ranges?
        OperatorPointwiseProduct.__init__(self, left, right)
        Functional.__init__(self, left.domain, linear=False,
                            grad_lipschitz=np.nan, range=left.range)

    @property
    def gradient(self):
        """Gradient operator of the functional.

        Notes
        -----
        The derivative is computed using Leibniz's rule:

        .. math::
            [\\nabla (f g)](p) = g(p) [\\nabla f](p) + f(p) [\\nabla g](p)
        """
        func = self

        class FunctionalProductGradient(Operator):

            """Functional representing the gradient of ``f(.) * g(.)``."""

            def _call(self, x):
                return (func.right(x) * func.left.gradient(x) +
                        func.left(x) * func.right.gradient(x))

        return FunctionalProductGradient(self.domain, self.domain,
                                         linear=False)


class FunctionalQuotient(Functional):

    """Quotient ``p(x) = f(x) / g(x)`` of two functionals ``f`` and ``g``."""

    def __init__(self, dividend, divisor):
        """Initialize a new instance.

        Parameters
        ----------
        dividend, divisor : `Functional`
            Functionals in the quotient. Need to have matching domains.

        Examples
        --------
        Construct the functional || . ||_2 / 5

        >>> space = odl.rn(2)
        >>> func1 = odl.solvers.L2Norm(space)
        >>> func2 = odl.solvers.ConstantFunctional(space, 5)
        >>> prod = odl.solvers.FunctionalQuotient(func1, func2)
        >>> prod([3, 4])  # expect sqrt(3**2 + 4**2) / 5 = 1
        1.0
        """
        if not isinstance(dividend, Functional):
            raise TypeError('`dividend` {} is not a `Functional` instance'
                            ''.format(dividend))
        if not isinstance(divisor, Functional):
            raise TypeError('`divisor` {} is not a `Functional` instance'
                            ''.format(divisor))

        if dividend.domain != divisor.domain:
            raise ValueError('domains of the operators do not match')
        if dividend.range is not divisor.range:
            raise ValueError('range of the operators do not match')
        
        self.__dividend = dividend
        self.__divisor = divisor
        

        super(FunctionalQuotient, self).__init__(
            dividend.domain, linear=False, grad_lipschitz=np.nan,
            range=dividend.range)

    @property
    def dividend(self):
        """The dividend of the quotient."""
        return self.__dividend

    @property
    def divisor(self):
        """The divisor of the quotient."""
        return self.__divisor

    def _call(self, x):
        """Apply the functional to the given point."""
        return self.dividend(x) / self.divisor(x)

    @property
    def gradient(self):
        """Gradient operator of the functional.

        Notes
        -----
        The derivative is computed using the quotient rule:

        .. math::
            [\\nabla (f / g)](p) = (g(p) [\\nabla f](p) -
                                    f(p) [\\nabla g](p)) / g(p)^2
        """
        func = self

        class FunctionalQuotientGradient(Operator):

            """Functional representing the gradient of ``f(.) / g(.)``."""

            def _call(self, x):
                """Apply the functional to the given point."""
                dividendx = func.dividend(x)
                divisorx = func.divisor(x)
                return ((1 / divisorx) * func.dividend.gradient(x) +
                        (- dividendx / divisorx**2) * func.divisor.gradient(x))

        return FunctionalQuotientGradient(self.domain, self.domain,
                                          linear=False)

    def __repr__(self):
        """Return ``repr(self)``."""
        return '{}({!r}, {!r})'.format(self.__class__.__name__,
                                       self.dividend, self.divisor)

    def __str__(self):
        """Return ``str(self)``."""
        return '{}({}, {})'.format(self.__class__.__name__,
                                   self.dividend, self.divisor)


class FunctionalDefaultConvexConjugate(Functional):

    """The `Functional` representing ``F^*``, the convex conjugate of ``F``.

    This class does not provide a way to evaluate the functional, it is rather
    intended to be used for its `proximal`.

    Notes
    -----
    The proximal is found by using the Moreau identity

    .. math::
        \\text{prox}_{\\sigma F^*}(y) = y -
        \\sigma \\text{prox}_{F / \\sigma}(y / \\sigma)

    which allows the proximal of the convex conjugate to be calculated without
    explicit knowledge about the convex conjugate itself.
    """

    def __init__(self, func):
        """Initialize a new instance.

        Parameters
        ----------
        func : `Functional`
            Functional corresponding to F.
        """
        if not isinstance(func, Functional):
            raise TypeError('`func` {} is not a `Functional` instance'
                            ''.format(func))
        #HELP: The range should be equal?!
        super(FunctionalDefaultConvexConjugate, self).__init__(
            domain=func.domain, linear=func.is_linear, range=func.range)
        self.__convex_conj = func

    @property
    def convex_conj(self):
        """The original functional."""
        return self.__convex_conj

    @property
    def proximal(self):
        """Proximal factory using the Moreu identity.

        Returns
        -------
        proximal : proximal_convex_conj
            Proximal computed using the Moreu identity
        """
        return proximal_convex_conj(self.convex_conj.proximal)

    def __repr__(self):
        """Return ``repr(self)``."""
        return '{!r}.convex_conj'.format(self.convex_conj)

    def __str__(self):
        """Return ``str(self)``."""
        return '{}.convex_conj'.format(self.convex_conj)


class BregmanDistance(Functional):
    """The Bregman distance functional.

    The Bregman distance, also refered to as the Bregman divergence, is similar
    to a metric but satisfies neither the triangle inequality nor symmetry.
    Nevertheless, the Bregman distance is used in variational regularization of
    inverse problems, see, e.g., `[Bur2016]`_.

    Notes
    -----
    Given a functional :math:`f`, which has a (sub)gradient :math:`\partial f`,
    and given a point :math:`y`, the Bregman distance functional
    :math:`D_f(\cdot, y)` in a point :math:`x` is given by

    .. math::
        D_f(x, y) = f(x) - f(y) - \\langle \partial f(y), x - y \\rangle.


    For mathematical details, see `[Bur2016]`_.

    References
    ----------
    Wikipedia article: https://en.wikipedia.org/wiki/Bregman_divergence

    [Bur2016] Burger, M. *Bregman Distances in Inverse Problems and Partial
    Differential Equation*. In: Advances in Mathematical Modeling, Optimization
    and Optimal Control, 2016. p. 3-33.

    .. _[Bur2016]:  https://arxiv.org/abs/1505.05191
    """

    def __init__(self, functional, point, func_subgrad=None):
        """Initialize a new instance.

        Parameters
        ----------
        functional : `Functional`
            Functional on which to base the Bregman distance. If the
            optional argument `func_subgrad` is not given, the functional
            needs to implement `functional.gradient`.
        point : element of ``functional.domain``
            Point from which to define the Bregman distance.
        func_subgrad : `Operator`, optional
            A subgradient operator. Operator which that takes an element in
            `functional.domain` and returns a subdifferential of the functional
            in that point.
            Default: ``functional.gradient``.

        Examples
        --------
        Example of initializing the Bregman distance functional:

        >>> space = odl.uniform_discr(0, 1, 10)
        >>> l2_squared = odl.solvers.L2NormSquared(space)
        >>> point = space.one()
        >>> Bregman_dist = odl.solvers.BregmanDistance(l2_squared, point)

        This is gives squared L2 distance to the given point, ||x - 1||^2:

        >>> expected_functional = l2_squared.translated(point)
        >>> Bregman_dist(space.zero()) == expected_functional(space.zero())
        True
        """
        if not isinstance(functional, Functional):
            raise TypeError('`functional` {} not an instance of ``Functional``'
                            ''.format(functional))
        self.__functional = functional

        if point not in functional.domain:
            raise ValueError('`point` {} is not in `functional.domain` {}'
                             ''.format(point, functional.domain))
        self.__point = point

        if func_subgrad is None:
            # If the subgradient is not given, assign the gradient of the
            # functional
            try:
                self.__func_subgrad = self.__functional.gradient
            except NotImplementedError:
                raise NotImplementedError(
                    '`subgradient` not given, and the `functional` {} does '
                    'not implement `functional.gradient`'.format(functional))
        else:
            # Check that given subgradient is an operator that maps from the
            # domain of the functional to itself
            if not isinstance(func_subgrad, Operator):
                raise TypeError(
                    '`func_subgrad` must be an instance of ``Operator``, got '
                    '{}'.format(func_subgrad))
            if func_subgrad.domain != self.__functional.domain:
                raise ValueError('`func_subgrad.domain` {} is not the same as '
                                 '`functional.domain` {}'
                                 ''.format(self.__functional.domain,
                                           func_subgrad.domain))
            if func_subgrad.range != self.__functional.domain:
                raise ValueError('`func_subgrad.range` {} is not the same as '
                                 '`functional.domain` {}'
                                 ''.format(self.__functional.domain,
                                           func_subgrad.range))
            self.__func_subgrad = func_subgrad

        self.__is_initialized = False
        
        #HELP: Is the range right?
        super(BregmanDistance, self).__init__(domain=functional.domain,
                                              linear=False,
                                              range=functional.range)

    @property
    def functional(self):
        """The functional used to define the Bregman distance."""
        return self.__functional

    @property
    def point(self):
        """The point used to define the Bregman distance."""
        return self.__point

    @property
    def func_subgrad(self):
        """The subgradient operator used to define the Bregman distance."""
        return self.__func_subgrad

    @property
    def initialized(self):
        """Flag for if the Bregman distance functional is initialized."""
        return self.__initialized

    def _initialize_if_needed(self):
        """Helper function to initialize the functional."""
        if not self.__is_initialized:
            self.__func_subgrad_eval = self.func_subgrad(self.point)
            self.__constant = (-self.functional(self.point) +
                               self.__func_subgrad_eval.inner(self.point))
            self.__bregman_dist = FunctionalQuadraticPerturb(
                self.functional, linear_term=-self.__func_subgrad_eval,
                constant=self.__constant)

            self.grad_lipschitz = (self.functional.grad_lipschitz +
                                   self.__func_subgrad_eval.norm())

            self.__initialized = True

    def _call(self, x):
        """Return ``self(x)``."""
        self._initialize_if_needed()
        return self.__bregman_dist(x)

    @property
    def convex_conj(self):
        """The convex conjugate"""
        self._initialize_if_needed()
        return self.__bregman_dist.convex_conj

    @property
    def proximal(self):
        """Return the ``proximal factory`` of the functional."""
        self._initialize_if_needed()
        return self.__bregman_dist.proximal

    @property
    def gradient(self):
        """Gradient operator of the functional."""
        self._initialize_if_needed()
        return self.func_subgrad - ConstantOperator(self.__func_subgrad_eval)

    def __repr__(self):
        '''Return ``repr(self)``.'''
        posargs = [self.functional, self.point]
        optargs = [('func_subgrad', self.func_subgrad, None)]
        inner_str = signature_string(posargs, optargs, sep=',\n')
        return '{}(\n{}\n)'.format(self.__class__.__name__, indent(inner_str))


def simple_functional(space, fcall=None, grad=None, prox=None, grad_lip=np.nan,
                      convex_conj_fcall=None, convex_conj_grad=None,
                      convex_conj_prox=None, convex_conj_grad_lip=np.nan,
                      linear=False, range=None):
    """Simplified interface to create a functional with specific properties.

    Users may specify as many properties as is needed by the application.

    Parameters
    ----------
    space : `LinearSpace`
        Space that the functional should act on.
    fcall : callable, optional
        Function to evaluate when calling the functional.
    grad : callable or `Operator`, optional
        Gradient operator of the functional.
    prox : `proximal factory`, optional
        Proximal factory for the functional.
    grad_lip : float, optional
        lipschitz constant of the functional.
    convex_conj_fcall : callable, optional
        Function to evaluate when calling the convex conjugate functional.
    convex_conj_grad : callable or `Operator`, optional
        Gradient operator of the convex conjugate functional
    convex_conj_prox : `proximal factory`, optional
        Proximal factory for the convex conjugate functional.
    convex_conj_grad_lip : float, optional
        lipschitz constant of the convex conjugate functional.
    linear : bool, optional
        True if the operator is linear.

    Examples
    --------
    Create squared sum functional on rn:

    >>> def f(x):
    ...     return sum(xi**2 for xi in x)
    >>> def dfdx(x):
    ...     return 2 * x
    >>> space = odl.rn(3)
    >>> func = simple_functional(space, f, grad=dfdx)
    >>> func.domain
    rn(3)
    >>> func.range
    RealNumbers()
    >>> func([1, 2, 3])
    14.0
    >>> func.gradient([1, 2, 3])
    rn(3).element([ 2.,  4.,  6.])
    """
    if grad is not None and not isinstance(grad, Operator):
        grad_in = grad

        class SimpleFunctionalGradient(Operator):

            """Gradient of a `SimpleFunctional`."""

            def _call(self, x):
                """Return ``self(x)``."""
                return grad_in(x)

        grad = SimpleFunctionalGradient(space, space, linear=False)

    if (convex_conj_grad is not None and
            not isinstance(convex_conj_grad, Operator)):
        convex_conj_grad_in = convex_conj_grad

        class SimpleFunctionalConvexConjGradient(Operator):

            """Gradient of the convex conj of a  `SimpleFunctional`."""

            def _call(self, x):
                """Return ``self(x)``."""
                return convex_conj_grad_in(x)

        convex_conj_grad = SimpleFunctionalConvexConjGradient(
            space, space, linear=False)

    class SimpleFunctional(Functional):

        """A simplified functional for examples."""

        def __init__(self):
            """Initialize an instance."""
            super(SimpleFunctional, self).__init__(
                space, linear=linear, grad_lipschitz=grad_lip, range=range)

        def _call(self, x):
            """Return ``self(x)``."""
            if fcall is None:
                raise NotImplementedError('call not implemented')
            else:
                return fcall(x)

        @property
        def proximal(self):
            """Return the proximal of the operator."""
            if prox is None:
                raise NotImplementedError('proximal not implemented')
            else:
                return prox

        @property
        def gradient(self):
            """Return the gradient of the operator."""
            if grad is None:
                raise NotImplementedError('gradient not implemented')
            else:
                return grad

        @property
        def convex_conj(self):
            return simple_functional(space, fcall=convex_conj_fcall,
                                     grad=convex_conj_grad,
                                     prox=convex_conj_prox,
                                     grad_lip=convex_conj_grad_lip,
                                     convex_conj_fcall=fcall,
                                     convex_conj_grad=grad,
                                     convex_conj_prox=prox,
                                     convex_conj_grad_lip=grad_lip,
                                     linear=linear,
                                     range=range)

    return SimpleFunctional()


if __name__ == '__main__':
    from odl.util.testutils import run_doctests
    run_doctests()
