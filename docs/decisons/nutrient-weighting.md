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
| 5       | 5    | 0.5           | 50            | 20     | 5     | _5000_ | **852**          |

Tried again removing the down-weighting of nutrients based on percentage of unknown which gave an average variance of 849.

| Protein | Fat  | Carbohydrates | Saturated Fat | Sugars | Fiber | Sodium | Average Variance |
| ------- | ---- | ------------- | ------------- | ------ | ----- | ------ | ---------------- |
| 5       | 5    | 0.5           | 50            | 20     | 5     | _1000_ | 856              |
| 5       | 5    | 0.5           | 50            | 20     | 5     | _2000_ | 850              |
| 5       | 5    | 0.5           | 50            | 20     | 5     | _3000_ | 850              |
| 5       | 5    | 0.5           | 50            | 20     | _2_   | 5000   | 854              |
| 5       | 5    | 0.5           | 50            | _10_   | 5     | 5000   | 856              |
| 5       | 5    | 0.5           | _20_          | 20     | 5     | 5000   | 854              |
| 5       | 5    | _2_           | 50            | 20     | 5     | 5000   | 848              |
| 5       | 5    | _5_           | 50            | 20     | 5     | 5000   | 857              |
| 5       | _10_ | 2             | 50            | 20     | 5     | 5000   | **847**          |
| 5       | _20_ | 2             | 50            | 20     | 5     | 5000   | 867              |
| _10_    | 10   | 2             | 50            | 20     | 5     | 5000   | 845              |
| _20_    | 10   | 2             | 50            | 20     | 5     | 5000   | 848              |

Attempting with Netherlands as this variance went up with the new weightings. Was 888 originally and 903 before most recent changes

| Protein | Fat  | Carbohydrates | Saturated Fat | Sugars | Fiber | Sodium | Average Variance |
| ------- | ---- | ------------- | ------------- | ------ | ----- | ------ | ---------------- |
| 10      | 10   | 2             | 50            | 20     | 5     | 5000   | 972              |
| 10      | 10   | 2             | 50            | 20     | 5     | _1000_ | 958              |
| 10      | 10   | 2             | 50            | 20     | 5     | _100_  | 949              |
| 10      | 10   | 2             | 50            | 20     | 5     | _10_   | 944              |
| 10      | 10   | 2             | 50            | 20     | 5     | _1_    | 950              |
| 10      | 10   | 2             | _20_          | 20     | 5     | 10     | 964              |
| 10      | 10   | 2             | 50            | _10_   | 5     | 10     | 952              |
| _5_     | 10   | 2             | 50            | 20     | 5     | 10     | 943              |
| _7_     | 10   | 2             | 50            | 20     | 5     | 10     | 941              |
| _9_     | 10   | 2             | 50            | 20     | 5     | 10     | 943              |
| _8_     | 10   | 2             | 50            | 20     | 5     | 10     | 942              |
| 7       | _5_  | 2             | 50            | 20     | 5     | 10     | **928**          |
| 7       | _7_  | 2             | 50            | 20     | 5     | 10     | 932              |
| 7       | _6_  | 2             | 50            | 20     | 5     | 10     | 930              |

Those best weightings then gave 855 for UK.

## Decision Outcome

The final weighting from the table above was adopted and tests re-run for all test sets.
