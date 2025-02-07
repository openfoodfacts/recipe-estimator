import { Table, TableHead, TableRow, TextField, TableBody, TableCell, Typography, Autocomplete, Button} from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { API_PATH } from './api';

interface RecipeProps {
  product: any
}

function ingredientDisplayName(ingredient: any): string {
  return ingredient?.alim_nom_eng ? `${ingredient.alim_nom_eng} (${ingredient.ciqual_food_code ?? (ingredient.ciqual_proxy_food_code ? 'P-' + ingredient.ciqual_proxy_food_code : '?')})` : ''
}
function addFirstOption(ingredient: any) {
  ingredient.options ??= [];
  if (ingredient && !(ingredient.options.find((i:any) => i.id === ingredient.id))) {
    ingredient.options.push({
      ciqual_food_code: ingredient.ciqual_food_code,
      ciqual_proxy_food_code: ingredient.ciqual_proxy_food_code,
      alim_nom_eng: ingredient.alim_nom_eng,
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
    ingredient.quantity_estimate = round(ingredient.quantity_estimate);
    flatIngredients.push(ingredient);
    if (ingredient.ingredients) {
      flatIngredients.push(...flattenIngredients(ingredient.ingredients, depth + 1));
    } else {
      addFirstOption(ingredient);
      if (ingredient.searchTerm == null)
        ingredient.searchTerm =  ingredientDisplayName(ingredient);
    }
  }
  return flatIngredients;
}

function round(num: any){
  return num == null || isNaN(num) ? 'unknown' : parseFloat(num).toPrecision(4);
}

const PERCENT = new Intl.NumberFormat(undefined, {maximumFractionDigits:1,minimumFractionDigits:0,style:"percent"});
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
      const results = await (await fetch(`${API_PATH}api/v3/estimate_recipe`, {method: 'POST', body: JSON.stringify(product)})).json();
      setIngredients(results.ingredients);
      setNutrients(Object.fromEntries(
        Object.entries(results.recipe_estimator.nutrients).filter(
           ([key, val])=>(val as any).product_total
        )));
    }
    fetchData();
  }, []);

  useEffect(()=>{
    getRecipe(product);
  }, [product, getRecipe]);

  function getTotal(nutrient_key: string, bound = 'nom') {
    return getTotalForParent(nutrient_key, ingredients, bound);
  }

  function recalculateRecipe() {
    product.ingredients = ingredients;
    getRecipe(product);
  }

  function getTotalForParent(nutrient_key: string, parent: any[], bound: string) {
    let total = 0;
    for(const ingredient of parent) {
      if (!ingredient.ingredients) {
        if (nutrient_key === '_total')
          total += 1.0 * ingredient.quantity_estimate;
        else if (nutrient_key === '_evaporation')
          total += ingredient.lost_water;
        else if (nutrient_key === '_percent')
          total += 0.01 * ingredient.percent_estimate;
        else if (ingredient.nutrients?.[nutrient_key])
          total += ingredient.quantity_estimate * ingredient.nutrients?.[nutrient_key]['percent_' + bound] / 100;
      }
      else
        total += getTotalForParent(nutrient_key, ingredient.ingredients, bound);
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
    if (['input','clear'].includes(reason)) {
      addFirstOption(ingredient);
      ingredient.searchTerm = value;
      setIngredients([...ingredients]);
      if (value) {
        getData(value, ingredient);
      }
    }
  };
  
  function ingredientChange(ingredient: any, value: any) {
    if (value) {
      // print ingredient to console
      console.log(value);
      ingredient.id = value.id;
      ingredient.ciqual_food_code_used = value.ciqual_food_code;
      ingredient.ciqual_food_code = value.ciqual_food_code;
      ingredient.ciqual_proxy_food_code = null;
      ingredient.alim_nom_eng = value.alim_nom_eng;
      ingredient.nutrients = value.nutrients;
      ingredient.searchTerm = ingredientDisplayName(value);
      setIngredients([...ingredients]);
    }
  }

  return (
    <div>
      {nutrients && ingredients &&
        <div>
            <Table size='small' stickyHeader sx={{'& .MuiTableCell-sizeSmall': {padding: '1px 4px'}}}>
              <TableHead>
                <TableRow className='total'>
                  <TableCell><Typography>Ingredient</Typography></TableCell>
                  <TableCell><Typography>CIQUAL Code</Typography></TableCell>
                  <TableCell><Typography>g/100g</Typography></TableCell>
                  <TableCell><Typography align='center'>Evaporation</Typography></TableCell>
                  <TableCell><Typography align='center'>Percent</Typography></TableCell>
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
                          <TextField {...params} variant='standard' size='small'/>
                        )}
                        filterOptions={(options) => options}
                      />
                    }
                    </TableCell>
                    <TableCell>{!ingredient.ingredients &&
                      <TextField variant="standard" type="number" size='small' value={parseFloat(ingredient.quantity_estimate) || ''} onChange={(e) => {ingredient.quantity_estimate = parseFloat(e.target.value);setIngredients([...ingredients]);}}/>
                    }
                    </TableCell>
                    <TableCell align='center'>{!ingredient.ingredients &&
                      <Typography>{format(parseFloat(ingredient.lost_water), QUANTITY)}</Typography>}
                    </TableCell>
                    <TableCell align='center'>{!ingredient.ingredients &&
                      <Typography>{format(0.01 * parseFloat(ingredient.percent_estimate), PERCENT)}</Typography>}
                    </TableCell>
                    {Object.keys(nutrients).map((nutrient: string) => (
                      <TableCell key={nutrient}>{!ingredient.ingredients && ingredient.nutrients?.[nutrient] &&
                        <>
                          <Typography variant="caption">
                            {ingredient.nutrients?.[nutrient].percent_min < ingredient.nutrients?.[nutrient].percent_nom ? format(ingredient.nutrients?.[nutrient].percent_min, QUANTITY) + '<' : ''}
                            {format(ingredient.nutrients?.[nutrient].percent_nom, QUANTITY)}[{ingredient.nutrients?.[nutrient].confidence}]
                            {ingredient.nutrients?.[nutrient].percent_max > ingredient.nutrients?.[nutrient].percent_nom ? '<' + format(ingredient.nutrients?.[nutrient].percent_max, QUANTITY) : ''}
                          </Typography>
                          <Typography variant="body1">{format(ingredient.quantity_estimate * ingredient.nutrients?.[nutrient].percent_nom / 100, QUANTITY)}</Typography>
                        </>
                      }
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                  <TableRow className='total'>
                    <TableCell colSpan={2}><Typography>Ingredients totals</Typography></TableCell>
                    <TableCell><Typography>{format(getTotal('_total'), QUANTITY)}</Typography></TableCell>
                    <TableCell><Typography align='center'>{format(getTotal('_evaporation'), QUANTITY)}</Typography></TableCell>
                    <TableCell><Typography align='center'>{format(getTotal('_percent'), PERCENT)}</Typography></TableCell>
                    {Object.keys(nutrients).map((nutrient_key: string) => (
                      <TableCell key={nutrient_key}>
                          <Typography variant="caption">{format(getTotal(nutrient_key, 'min'), QUANTITY)}</Typography>
                          <Typography variant="body1">{format(getTotal(nutrient_key), QUANTITY)}</Typography>
                          <Typography variant="caption">{format(getTotal(nutrient_key, 'max'), QUANTITY)}</Typography>
                      </TableCell>
                    ))}
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={5}><Typography>Quoted product nutrients</Typography></TableCell>
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
                    <TableCell padding='normal'>
                      <Button variant='contained' onClick={recalculateRecipe}>recalculate</Button>
                    </TableCell>
                    <TableCell colSpan={3}>
                      <Typography variant="caption">Weighted</Typography>
                      <Typography>{format(Object.keys(nutrients).reduce((total: number,nutrient_key: any) => 
                      total + (!nutrients[nutrient_key].notes 
                        ? nutrients[nutrient_key].weighting * (getTotal(nutrient_key)- nutrients[nutrient_key].product_total) ** 2
                        : 0), 0), VARIANCE)}
                      </Typography>
                    </TableCell>
                    {Object.keys(nutrients).map((nutrient_key: string) => (
                      <TableCell key={nutrient_key}>
                          <Typography variant="caption">{format(getTotal(nutrient_key) - nutrients[nutrient_key].product_total, VARIANCE)}</Typography>
                          <br/>
                          {!nutrients[nutrient_key].notes && nutrients[nutrient_key].weighting > 0
                            ? <Typography>{format(nutrients[nutrient_key].weighting * (getTotal(nutrient_key)- nutrients[nutrient_key].product_total), VARIANCE)}</Typography>
                            : <Typography variant="caption">{nutrients[nutrient_key].notes ?? 'Not used'}</Typography>
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

