# Choice of Algorithm

## Context and Problem Statement

In estimating a recipe we are attempting to minimize the variance between the nutritional information calculated from the ingredients and that displayed on the product packaging whilst keeping to certain constraints, such as ingredient ordering.

This document describes how the algorithm used for this was selected.

## Decision Drivers

* All required optimization variables and constraints can be supported
* Performance (need to be able to quickly re-process millions of products)
* The code is easy to follow
* The results are close to optimal

## Considered Options

* GLOP
* SciPy minimize
* SciPy global optimization
* SciPy differential evolution
* NNLS
* CVXPY

## Decision Outcome

Chosen option: "CVXPY", because it is fast and whilst giving some flexibility in how the objective function and constraints are expressed it ensures the problem remains convex (avoiding local minima).

### Consequences

The objective function and constraints are restricted to functions supported by CVXPY (of which there are many).

## Pros and Cons of the Options

### GLOP

With this approach we use the [Linear Programming solver](https://developers.google.com/optimization/lp/lp_example) from Google's Linear Optimization Package (GLOP).

* Good: Fast
* Good: Results are reasonably optimal
* Bad: Nutrient distance is linear rather than by variance
* Bad: Way of coping with positive or negative variance is complicated

### SciPy minimize

Various methods from the [SciPy minimize](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html) library were attempted.

* Good: Some methods, such as SLSQP, where very fast
* Good: Objective function can be expressed as a standard Python function
* Bad: Most algorithms were prone to getting stuck in local minima

### SciPy global optimization

SciPy has a number of global optimization options which should avoid local minima. The following were tried:

* [shgo](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.shgo.html#scipy.optimize.shgo)
* [dual_annealing](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html#scipy.optimize.dual_annealing)
* [basinhopping](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.basinhopping.html#scipy.optimize.basinhopping)
* [direct](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.direct.html#scipy.optimize.direct)

* Good: Objective function can be expressed as a standard Python function
* Bad: Many were quite slow
* Bad: Still had problems with local minima

### SciPy differential evolution

The SciPy [differential evolution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html#scipy.optimize.differential_evolution) method uses genetic algorithms to attempt to find an optimal solution.

* Good: Objective function can be expressed as a standard Python function
* Good: Gave close to optimal results with sufficient iterations
* Bad: Much slower than GLOP

### NNLS

The SciPy [Non-negative Least Squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.nnls.html#scipy.optimize.nnls) algorithm was attempted as this was used when manually testing the general approach, as discussed in various [Wiki articles](https://wiki.openfoodfacts.org/Recipe/Overview).

* Good: Fast
* Good: Gave close to optimal results in simle cases
* Bad: Very restrictive on how the problem is expressed
* Bad: Difficult to express ingredient ordering constraints, especially for compound ingredients


### CVXPY

The [CVXPY](https://www.cvxpy.org/index.html) library is a general solver for convex optimization problems. It restricts the way that the problem is expressed to ensure that local minima are avoided.

* Good: Fast
* Good: Close to optimal results
* Good: Objective and constraints can be expressed in an easy to understand way
* Good: Prevents deviation from a convex problem

