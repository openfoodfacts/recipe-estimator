import time
import warnings
from scipy.optimize import (
    minimize,
    dual_annealing,
    shgo,
    basinhopping,
    differential_evolution,
    direct,
)

from .fitness import get_objective_function_args, objective

# estimate_recipe() uses a linear solver to estimate the quantities of all leaf ingredients (ingredients that don't have child ingredient)
# The solver is used to minimise the difference between the sum of the nutrients in the leaf ingredients and the total nutrients in the product
# A lot of manual testing was done with product 20023751 which seems to have a lot of local minima.
# The optimal solution for this product has a total penalty of about 130900
def estimate_recipe(product):
    current = time.perf_counter()
    [bounds, leaf_ingredients, args] = get_objective_function_args(product)
    MAXITER = 5000
    x0 = [ingredient["initial_estimate"] for ingredient in leaf_ingredients]

    # Some of the global optimizers don't pass args easily
    def local_objective(x):
        return objective(x, *args)

    # Simple optimization not able to get past local minima
    # solution = minimize(
    #     local_objective,
    #     x0=x0,
    #     method="SLSQP",
    #     bounds=bounds,
    #     # constraints=constraints,
    # )  # Fastest

    # COBYQA is very slow
    # solution = minimize(objective,x,method='COBYLA',bounds=bounds,constraints=cons,options={'maxiter': 10000})

    # solution = minimize(
    #     objective,
    #     leaf_ingredients,
    #     method="L-BFGS-B",
    #     bounds=bounds,
    #     # constraints=constraints,
    # )  # Fastest

    # solution = minimize(objective,x,method='trust-constr',bounds=bounds,constraints=cons)

    # May need to consider using global minimization as the objective function is probably not convex

    # # Doesn't get close to passing most tests
    # solution = shgo(
    #     local_objective,
    #     bounds=bounds,
    #     # options={
    #     #     'f_min': 0
    #     # }
    #     minimizer_kwargs={'method': 'L-BFGS-B'}
    # )

    # # Not bad but still not as good as differential_evolution
    # solution = dual_annealing(
    #     local_objective,
    #     bounds=bounds,
    #     x0=x0,
    #     rng=0,
    #     maxiter=1000,
    #     # initial_temp=10000,
    #     # visit=2, # Default seems to work best
    #     # no_local_search=True, # Makes things a bit faster, but less optimal
    #     # L-BFGS-B (default): 53s but close to optimal. Down to 20s with 100 iterations
    #     # COBYLA: 17s and less optimal
    #     # SLSQP: 85s and not optimal
    #     minimizer_kwargs={"method": "L-BFGS-B"},
    # )

    # # COBYLA seemed to be the best minimizer to use with this and gave OK results on 20023751 130900
    # # but didn't pass tests
    # solution = basinhopping(
    #     local_objective,
    #     x0=x0,
    #     rng=0, # Seed random number generation to get consistent results between runs
    #     # niter=100, # Increasing slowed down but didn't massively improve results
    #     # stepsize=0.1, # Default of 0.5 seemed to work best
    #     # T=10, # Can't seem to improve on the default
    #     # target_accept_rate=0.9, # Changing this didn't seem to help much
    #     # stepwise_factor=0.3, # Bit of trial and error to get this
    #     # Tried the following minimizers without changing specific arguments on product 20023751
    #     # Nelder-Mead: 71s and not optimal.
    #     # L-BFGS-B: 211s but a bit more optimal
    #     # COBYLA: 7s and reasonably optimal
    #     # COBYQA: 233s and a bit less optimal
    #     # SLSQP: 1.4s but not close to optimal
    #     # trust-constr: 494s but was optimal
        
    #     minimizer_kwargs={"method": "COBYLA", "bounds": bounds},
    # )

    # This seems to give optimum results but can take some time
    solution = differential_evolution(
        objective,
        bounds,
        args=args,
        x0=x0,
        polish=False, # Don't polish results to help with performance. Results are only slightly less optimal
        rng=0, # Seed random number generator so we get consistent results between tests
        workers=-1 if len(leaf_ingredients) > 10 else 1, # Gives a bit of an improvement with more complex products but not worth it for simple ones
        updating='deferred', # Need to set this if we are going to set workers
        # popsize=10, # Default is 15. Increasing this really slows things down
        # init='sobol', # Changing this didn't seem to make much difference
        tol=0.001, # Needed a lower value here to pass tests. Didn't seem to affect performance much
        atol=2, # Going much higher seems to break tests
        # mutation=(1.5, 1.9), # Tried increasing this but gave poor results
        recombination=0.88 # Higher values seem to improve performance. This was highest I could go and still pass tests
    )

    # # Initially thought this was promising but was not finding optimal solution in a number of cases
    # # Gives consistent results where other algorithms use randomization a lot which gives different results from one run to the next
    # # but can get around this by seeding the random number generator in other algorithms
    # # For details of arguments see: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.direct.html
    # solution = direct(
    #     objective,
    #     bounds,
    #     args=args,
    #     eps=0.01,  # Bit of trial and error here but going too much higher seems to find the wrong local minimum
    #     locally_biased=False,  # False is recommended for problems with lots of local minima. True passes tests but is less good for real life recipes
    #     f_min=0,  # Global minimum. Our objective function will never go negative
    #     #f_min_rtol=0.1, # Changing this didn't seem to make a lot of difference
    #     #len_tol=0.00001,  # If this is too small then the number of iterations will be exceeded, but too large gives inaccurate results
    #     #vol_tol=1e-32,
    #     # Following two give a trade-off between performance and accuracy. Have much more of an impact on performance if locally_biased is False
    #     maxfun=10000 * len(leaf_ingredients),
    #     maxiter=MAXITER,
    # )

    total_quantity = sum(solution.x)

    def set_percentages(ingredients):
        total_percent = 0
        for ingredient in ingredients:
            if "ingredients" in ingredient and len(ingredient["ingredients"]) > 0:
                percent_estimate = set_percentages(ingredient["ingredients"])
            else:
                index = ingredient["index"]
                ingredient["quantity_estimate"] = round(solution.x[index], 2)
                # ingredient["lost_water"] = round(solution.x[index + 1], 2)
                percent_estimate = round(100 * solution.x[index] / total_quantity, 2)

            ingredient["percent_estimate"] = percent_estimate
            total_percent += percent_estimate

        return total_percent

    set_percentages(product["ingredients"])
    recipe_estimator = product["recipe_estimator"]
    recipe_estimator["status"] = 0
    recipe_estimator["status_message"] = solution.message
    # Note that for some algorithms penalties won't be set to the value from the best solution, so call the objective function again to get it
    objective(solution.x, *args)
    recipe_estimator['penalties'] = args[0]
    recipe_estimator["time"] = round(time.perf_counter() - current, 2)
    message = f"Product: {product.get('code')}, time: {recipe_estimator['time']} s, status: {solution.get('message')}, iterations: {solution.get('nit')}"
    if solution.success and solution.get("nit", 0) < MAXITER:
        print(message)
    else:
        warnings.warn(message)

    return solution
