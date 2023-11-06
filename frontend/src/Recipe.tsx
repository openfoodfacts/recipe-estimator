import { Table, TableHead, TableRow, TextField, TableBody, TableCell, Typography, Autocomplete, Button} from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { API_PATH } from './api';

interface RecipeProps {
  product: any
}

function ingredientDisplayName(ingredient: any): string {
  return ingredient?.text ? `${ingredient.text} (${ingredient.ciqual_food_code})` : ''
}
function addFirstOption(ingredient: any) {
  ingredient.options ??= [];
  if (ingredient && !(ingredient.options.find((i:any) => i.id === ingredient.id))) {
    ingredient.options.push({
      ciqual_food_code: ingredient.ciqual_food_code,
      text: ingredient.text,
      id: ingredient.id,
      searchTerm: ingredientDisplayName(ingredient),
      nutrients: ingredient.nutrients,
    });
  }
}

function flattenIngredients(ingredients: any[], depth = 0): any[] {
  const flatIngredients = [];
  for (const ingredient of ingredients) {
    ingredient.depth = depth;
    ingredient.proportion = round(ingredient.proportion);
    flatIngredients.push(ingredient);
    if (ingredient.ingredients) {
      flatIngredients.push(...flattenIngredients(ingredient.ingredients, depth + 1));
    } else {
      addFirstOption(ingredient);
      if (!ingredient.searchTerm)
        ingredient.searchTerm =  ingredientDisplayName(ingredient);
    }
  }
  return flatIngredients;
}

function round(num: any){
  return num == null || isNaN(num) ? 'unknown' : parseFloat(num).toPrecision(4);
}

const PERCENT = new Intl.NumberFormat(undefined, {maximumFractionDigits:2,minimumFractionDigits:2,style:"percent"});
const VARIANCE = new Intl.NumberFormat(undefined, {maximumFractionDigits:2,minimumFractionDigits:2,signDisplay:"always"});
const QUANTITY = new Intl.NumberFormat(undefined, {maximumFractionDigits:2,minimumFractionDigits:2});

function format(num: number, formatter: Intl.NumberFormat){
  return num == null || isNaN(num) ? 'unknown' : formatter.format(num);
}


export default function Recipe({product}: RecipeProps) {
  const [ingredients, setIngredients] = useState<any>();
  const [nutrients, setNutrients] = useState<any>();

  const getRecipe = useCallback((product: any) => {
    if (!product || !product.ingredients)
      return;
    async function fetchData() {
      const results = await (await fetch(`${API_PATH}recipe`, {method: 'POST', body: JSON.stringify(product)})).json();
      setIngredients(results.ingredients);
      setNutrients(results.recipe_estimator.nutrients);
    }
    fetchData();
  }, []);

  useEffect(()=>{
    getRecipe(product);
  }, [product, getRecipe]);

  function getTotal(nutrient_key: string) {
    return getTotalForParent(nutrient_key, ingredients);
  }

  function getTotalForParent(nutrient_key: string, parent: any[]) {
    let total = 0;
    for(const ingredient of parent) {
      if (!ingredient.ingredients) 
        total += ingredient.proportion * (nutrient_key ? ingredient.nutrients?.[nutrient_key] : 1) / 100;
      else
        total += getTotalForParent(nutrient_key, ingredient.ingredients);
    }
    return total;
  }

  const previousController = useRef<AbortController>();
  
  function getData(searchTerm: string, ingredient: any) {
    if (previousController.current) {
      previousController.current.abort();
    }
    const controller = new AbortController();
    const signal = controller.signal;
    previousController.current = controller;
    fetch(`${API_PATH}ciqual/${searchTerm}`, {signal})
      .then(function (response) {
        return response.json();
      })
      .then(function (myJson) {
        ingredient.options = myJson;
        addFirstOption(ingredient)
        setIngredients([...ingredients]);
      })
      .catch(() => {});
  };
  
  function onInputChange(ingredient:any, value: string, reason: string) {
    if (value) {
      addFirstOption(ingredient);
      setIngredients([...ingredients]);
      if (reason === 'input' && value) {
        getData(value, ingredient);
      }
    }
  };
  
  function ingredientChange(ingredient: any, value: any) {
    if (value) {
      ingredient.id = value.id;
      ingredient.ciqual_food_code = value.ciqual_food_code;
      ingredient.text = value.text;
      ingredient.nutrients = value.nutrients;
      ingredient.searchTerm = ingredientDisplayName(value);
      setIngredients([...ingredients]);
    }
  }

  return (
    <div>
      {nutrients && ingredients &&
        <div>
            <Table size='small'>
              <TableHead>
                <TableRow className='total'>
                  <TableCell><Typography>Ingredient</Typography></TableCell>
                  <TableCell><Typography>CIQUAL Code</Typography></TableCell>
                  <TableCell><Typography>Proportion</Typography></TableCell>
                  {Object.keys(nutrients).map((nutrient: string) => (
                    <TableCell key={nutrient}>
                      <Typography>{nutrient}</Typography>
                      <Typography variant="caption">{format(nutrients[nutrient].weighting, QUANTITY)}</Typography>
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {flattenIngredients(ingredients).map((ingredient: any, index: number)=>(
                  <TableRow key={index}>
                    <TableCell><Typography sx={{paddingLeft: (ingredient.depth)}}>{ingredient.text}</Typography></TableCell>
                    <TableCell>{!ingredient.ingredients &&
                      <Autocomplete
                        id="combo-box-demo"
                        options={ingredient.options}
                        onInputChange={(_event,value,reason) => onInputChange(ingredient,value,reason)}
                        onChange={(_event,value) => ingredientChange(ingredient,value)}
                        value={ingredient.id || null}
                        inputValue={ingredient.searchTerm || ''}
                        getOptionLabel={(option:any) => ingredientDisplayName(option)}
                        isOptionEqualToValue={(option:any, value:any) => option.id === value.id}
                        style={{ width: 300 }}
                        renderInput={(params) => (
                          <TextField {...params} size='small'/>
                        )}
                        filterOptions={(options) => options}
                      />
                    }
                    </TableCell>
                    <TableCell>{!ingredient.ingredients &&
                      <TextField type="number" size='small' value={parseFloat(ingredient.proportion) || ''} onChange={(e) => {ingredient.proportion = parseFloat(e.target.value);setIngredients([...ingredients]);}}/>
                    }
                    </TableCell>
                    {Object.keys(product.recipe_estimator.nutrients).map((nutrient: string) => (
                      <TableCell key={nutrient}>{!ingredient.ingredients &&
                        <>
                          <Typography variant="caption">{format(ingredient.nutrients?.[nutrient], QUANTITY)}</Typography>
                          <Typography variant="body1">{format(ingredient.proportion * ingredient.nutrients?.[nutrient] / 100, QUANTITY)}</Typography>
                        </>
                      }
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                  <TableRow className='total'>
                    <TableCell colSpan={2}><Typography>Ingredients totals</Typography></TableCell>
                    <TableCell><Typography>{format(getTotal(''), PERCENT)}</Typography></TableCell>
                    {Object.keys(nutrients).map((nutrient_key: string) => (
                      <TableCell key={nutrient_key}>
                        <Typography variant="body1">{format(getTotal(nutrient_key), QUANTITY)}</Typography>
                      </TableCell>
                    ))}
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={3}><Typography>Quoted product nutrients</Typography></TableCell>
                    {Object.keys(nutrients).map((nutrient_key: string) => (
                      <TableCell key={nutrient_key}>
                        <Typography variant="body1">{format(nutrients[nutrient_key].product_total, QUANTITY)}</Typography>
                      </TableCell>
                    ))}
                  </TableRow>
                  <TableRow className='total'>
                    <TableCell>
                      <Typography>Variance</Typography>
                    </TableCell>
                    <TableCell>
                      <Button variant='contained' onClick={()=>getRecipe(product)}>recalculate</Button>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">Weighted</Typography>
                      <Typography>{format(Object.keys(nutrients).reduce((total: number,nutrient_key: any) => 
                      total + (!nutrients[nutrient_key].notes 
                        ? nutrients[nutrient_key].weighting * Math.abs(getTotal(nutrient_key)- nutrients[nutrient_key].product_total) 
                        : 0), 0), VARIANCE)}
                      </Typography>
                    </TableCell>
                    {Object.keys(nutrients).map((nutrient_key: string) => (
                      <TableCell key={nutrient_key}>
                        {!nutrients[nutrient_key].notes 
                          ? <>
                            <Typography variant="caption">{format(getTotal(nutrient_key) - nutrients[nutrient_key].product_total, VARIANCE)}</Typography>
                            <Typography>{format(nutrients[nutrient_key].weighting * (getTotal(nutrient_key)- nutrients[nutrient_key].product_total), VARIANCE)}</Typography>
                            </>
                          : <Typography variant="caption">{nutrients[nutrient_key].notes}</Typography>
                        }
                      </TableCell>
                    ))}
                  </TableRow>
              </TableBody>
            </Table>
        </div>
      }
    </div>
  );
}

