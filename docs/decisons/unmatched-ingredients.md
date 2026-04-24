# Dealing with Unmatched Ingredients

## Context and Problem Statement

In many cases one or more ingredients on a product will not have a match in the ingredients taxonomy or CIQUAL. This document discusses how these ingredients should be handled.

Some [tests](https://wiki.openfoodfacts.org/Recipe/Simple_Tool) on existing products have found that, on average, ingredients quantities tend to follow an inverse power series based on their position in the ingredient list, i.e. 1/1<sup>n</sup>, 1/2<sup>n</sup>, 1/3<sup>n</sup>, etc. Tests found that a value of 1.7 for n gave the best results.

## Decision Drivers

* Should give reasonable results
* Not overly complicated
* Should not significantly impact performance

## Considered Options

* Ignore unknown ingredients in the optimization and re-introduce them afterwards
* Include unknown ingredients in the optimization, with an objective to keep as close to the inverse power series as possible

## Decision Outcome

Chosen option: "{title of option 1}", because
{justification. e.g., only option, which meets k.o. criterion decision driver | which resolves force {force} | … | comes out best (see below)}.

## Pros and Cons of the Options

### Ignore unknown ingredients in the optimization and re-introduce them afterwards

* Good: Keeps the number of variables small
* Bad: Adding afterwards will increase total mass of the recipe above 100g

### Include unknown ingredients in the optimization, with an objective to keep as close to the inverse power series as possible

* Good: Simple to implement
* Bad: Relative quantityt of unknown ingredients not affected by known ingredients, except for ordering constraints
