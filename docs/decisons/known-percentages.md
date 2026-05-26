# Dealing with Known Ingredient Percentages

## Context and Problem Statement

Many products quote percentages for some of their ingredients, which should be taken into consideration during the optimization.

For the UK/EU the quantity of the ingredient used to make 100g of product is equal to the quoted percentage. e.g. if 30g tomatoes were used in a recipe with a total raw ingredient weight of 120g to make 100g product then the percentage of tomatoes would be quoted as 30% (hence percentages could theoretically add up to mre than 100).

However, in the US the percentage is the quantity of the raw ingredient relative to the finished weight, so in the above example 30g raw tomatoes / 120g total raw ingredients = 25%.

## Decision Drivers

* Percentages are quoted based on the "mixing bowl" rule in the UK/EU, but relative to the final weight in the US
* Percentages will have been rounded

## Considered Options

* Add constraints to the optimization for ingredients with known percentages
* Add objectives to the optimization to get the ingredient as close to the quoted percentage as possible

## Decision Outcome

Chosen option: "Add constraints to the optimization for ingredients with known percentages", because it keeps things linear and ensures close matching with quoted product percentages.

### How to deal with compound ingredients

A supplementary decision on how to cope with compund ingredients that have a percentage quoted on them.

#### Decision Outcome

Chosen option: "Single water loss variable on the parent".

#### Single water loss variable on the parent

* Good: Less variables so a more deterministic result
* Bad: Can't see percentage of component ingredients

#### Separate variables for each sub-ingredient

* Good: Easier to present
* Bad: Adds more variables with only one data point (parent percentage) to support them

<!-- This is an optional element. Feel free to remove. -->
### Consequences

{Provide detail on the implications of making this decision and how any forseen problems can be mitigated}

## Pros and Cons of the Options

### Add constraints to the optimization for ingredients with known percentages

For the UK/EU this is straightforward as the quantity of the ingredient used to make 100g of product is the quoted percentage. A constraint could be added that the quantity of the ingredient must lie within a determined tolerance of the stated percentage. If the Ingredient has a water loss before adding to the mixing bowl (see [water-loss.md](water-loss.md)) then the water loss would be subtracted from the raw ingredient quantity before applying this constraint, as the per-ingredient water loss happens before the mixing bowl.

However, in the US, the percentage is the quantity of the raw ingredient relative to the finished weight, so for any particular ingredient:

100 * ingredient_quantity / sum_of_all_ingredient_quantities ~ quoted_percentage

Rearranging this to be a linear constraint:

(100 * ingredient_quantity) - (quoted_percentage * sum_of_all_ingredient_quantities) ~ 0

As for the UK / EU the ingredient quantities here are at the time of adding to the final mixing bowl, so per ingredient water loss would be subtracted first.

* Good: Using a constraint will force the estimator to align with quoted percentages
* Good: Can be coded as a linear function
* Neutral: Requires us to come up with suitable tolerances
* Bad: Failing to meet the constraint should abort the optimization

### Add objectives to the optimization to get the ingredient as close to the quoted percentage as possible

For the UK/EU this would be relatively straightforward where we would minimize the square of the difference between the quantity of the ingredient in the final mixing bowl (ingredient_quantity - ingredient_water_loss) and the stated percentage.

In the case of the US we would be minimizing the square of the formula quoted above, i.e.

(100 * ingredient_quantity) - (quoted_percentage * sum_of_all_ingredient_quantities)

* Good: Allows some flexibility on quoted percentages, e.g. if there has been an ingredient parsing error
* Neutral: Should be convex, but need to check as squaring the formula above will create some kind of power equation
* Bad: Could result in recipes that don't match the quoted percentages

## More Information

Add references to mixing bowl rules and differnt regional legislation.