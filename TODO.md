# TODO

## Outstanding Tasks

### Error Handling
- Need to return a more formal error object

### CIQUAL Database Integration  
- Use min and max for ingredient nutrient when stated as "< ..." in CIQUAL
- Use min and max from CIQUAL for unmatched ingredients
- Cope with min and max on product nutrients (e.g. if we had to get from a category)

### Testing
- Add frontend unit tests
- Improve test coverage for edge cases

### Performance
- Optimize algorithm performance for large ingredient lists
- Add caching for frequently accessed nutritional data

### Features
- Support for additional nutritional databases beyond CIQUAL
- Regional preference settings for database selection
- Better handling of ingredient synonyms and translations

## Development Notes

### Getting Nutrient Types

The query used to generate nutrient types for `nutrient_map.csv`:

```js
db.products.aggregate([
  {
    $project: {
      keys: {
        $map: {
          input: {
            $objectToArray: "$nutriments"
          },
          in: "$$this.k"
        }
      }
    }
  },
  {
    $unwind: "$keys"
  },
  {
    $match: {
      $and: [
        {
          keys: {
            $regex: "_100g$"
          }
        },
        {
          keys: {
            $ne: {
              $regex: "_prepared_100g$"
            }
          }
        }
      ]
    }
  },
  {
    $project: {
      keys: {
        $replaceOne: {
          input: "$keys",
          find: "_100g",
          replacement: ""
        }
      }
    }
  },
  {
    $group: {
      _id: "$keys",
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  }
])
```