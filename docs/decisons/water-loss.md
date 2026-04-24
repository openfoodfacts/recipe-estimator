# Dealing with Water Loss

## Context and Problem Statement

In many recipes water is lost during the cooking / processing stage of the whole product and / or individual ingredients. This means that the sum of quantities of ingredients needed to make 100g of product can exceed 100g. Water might also be added to some ingredients that are re-hydrated, such as juice concentrates.

This document discusses approaches to dealing with this.

## Decision Drivers

* Key requirement is to know the quantity of the original ingredient needed to make 100g of product
* Should not introduce unnecessary complexity

## Considered Options

* Use variables for water loss on each ingredient and for the recipe as a whole
* Have one variable for water loss
* Use maximum water loss as a constraint and optimize to minimize water loss

## Decision Outcome

Chosen option: "Use maximum water loss as a constraint and optimize to minimize water loss", because it keeps the number of variables small and seems to give good results.

## Pros and Cons of the Options

### Use variables for water loss on each ingredient and for the recipe as a whole

This would add a variable for each ingredient that contains water indicating its water loss prior to being added to the "mixing bowl". There would then be a separate water loss for the recipe as a whole and also for any compound ingredients.

In theory, knowing the water loss of each ingredient prior to adding to the mixing bowl allows it to be taken into consideration in ordering constraints. For example a recipe may contain onions and tomato puree. There may be more weight of raw tomatoes in the product than onions but if the tomato was added to the mixing bowl as puree then it could be listed after onions in the ingredients list.

However, in practice the rules for this are quite ambiguous, vary by country and can be subject to interpretation depending on how the manufacturer wants to present their ingredients.

* Good: Theoretically gives more information about each ingredient and how it has been processed
* Bad: Introduces more variables into the optimization without enough data to calculate them
* Bad: Additional information is not helpful in practice

### Have one variable for water loss

In this case a single variable for water loss (or gain in the case of rehydration) is introduced which can be used to constrain the sum of all ingredients less water loss to always equal 100g. The water loss variable can also be constrained based on the maximum water content of each ingredient.

* Good: Clearly shows total water loss for the recipe
* Good: Easy to understand
* Bad: Adds another variable without adding more data to support the calculation

### Use maximum water loss as a constraint and optimize to minimize water loss

Rather than add a variable the water loss is incorporated into the optimization as a constraint and objective target.

The constraint is that the sum of all the ingredients less the maximum possible water loss for each ingredient must be no more than 100g.

The optimization objective is to minimize the water loss, so favour solutions where the sum of the raw ingredients is equal to 100g.

* Good: Doesn't add any more variables
* Good: Easy to understand
* Good: Water loss can easily be inferred from the difference between the sum of the ingredients and 100g
