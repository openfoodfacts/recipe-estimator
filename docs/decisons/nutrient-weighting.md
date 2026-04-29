# How to weight different nutrients

## Context and Problem Statement

Some nutrients, such as salt, are generally in very small quantities so a weighting would need to be applied to them in order for them to have a significant impact on the nutrient variance.

It may also be beneficial to attach a higher weight to nutrients that are expressed with better accuracy.

## Decision Drivers

- Should give the best results with representative products

## Considered Options

All weightings were set to 1 and then various iterations of the known-percent-united-kingdom test set were run with each nutrient weighting set to various values to test the sensitivity.

Starting with an average variance of 914

| Nutrient      | Weighting | Average Variance |
| ------------- | --------- | ---------------- |
| Protein       | 0.1       | 930              |
| Protein       | 5         | **908**          |
| Protein       | 10        | 920              |
| Fat           | 0.1       | 915              |
| Fat           | 5         | **904**          |
| Fat           | 10        | 916              |
| Carbohydrates | 0.01      | 894              |
| Carbohydrates | 0.05      | **876**          |
| Carbohydrates | 0.1       | 880              |
| Carbohydrates | 0.5       | 909              |
| Carbohydrates | 10        | 971              |
| Saturated Fat | 0.1       | 926              |
| Saturated Fat | 10        | 879              |
| Saturated Fat | 20        | **878**          |
| Saturated Fat | 50        | 879              |
| Saturated Fat | 100       | 889              |
| Sugars        | 0.1       | 912              |
| Sugars        | 5         | 906              |
| Sugars        | 10        | **905**          |
| Sugars        | 20        | 919              |
| Sugars        | 100       | 982              |
| Fiber         | 0.01      | 910              |
| Fiber         | 0.05      | 904              |
| Fiber         | 0.1       | **903**          |
| Fiber         | 0.5       | 912              |
| Fiber         | 10        | 943              |
| Sodium        | 0.1       | 916              |
| Sodium        | 10        | 914              |
| Sodium        | 100       | 919              |
| Sodium        | 500       | 912              |
| Sodium        | 1000      | 910              |
| Sodium        | 2000      | **909**          |
| Sodium        | 5000      | 911              |
| Sodium        | 10000     | 914              |

The **best** value from each was then used but this did not give better results than when just one value was changed, so further _iterations_ were made:

| Protein | Fat  | Carbohydrates | Saturated Fat | Sugars | Fiber | Sodium | Average Variance |
| ------- | ---- | ------------- | ------------- | ------ | ----- | ------ | ---------------- |
| 5       | 5    | _0.05_        | 20            | 10     | 0.1   | 2000   | 896              |
| 5       | 5    | _0.1_         | 20            | 10     | 0.1   | 2000   | 890              |
| 5       | 5    | _1_           | 20            | 10     | 0.1   | 2000   | 882              |
| 5       | 5    | _5_           | 20            | 10     | 0.1   | 2000   | 907              |
| 5       | 5    | _0.5_         | 20            | 10     | 0.1   | 2000   | 876              |
| 5       | 5    | _0.2_         | 20            | 10     | 0.1   | 2000   | 886              |
| 5       | 5    | 0.5           | _50_          | 10     | 0.1   | 2000   | 872              |
| 5       | 5    | 0.5           | _100_         | 10     | 0.1   | 2000   | 877              |
| 5       | 5    | 0.5           | 50            | _20_   | 0.1   | 2000   | 871              |
| 5       | 5    | 0.5           | 50            | 20     | _1_   | 2000   | 860              |
| 5       | 5    | 0.5           | 50            | 20     | _2_   | 2000   | 859              |
| 5       | 5    | 0.5           | 50            | 20     | _5_   | 2000   | 853              |
| 5       | 5    | 0.5           | 50            | 20     | _10_  | 2000   | 857              |
| 5       | _10_ | 0.5           | 50            | 20     | 5     | 2000   | 855              |
| _10_    | 5    | 0.5           | 50            | 20     | 5     | 2000   | 858              |
| 5       | 5    | 0.5           | 50            | 20     | 5     | _5000_ | 852              |

## Decision Outcome

The final weighting from the table above was adopted and tests re-run for all test sets.
