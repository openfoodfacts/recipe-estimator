import { writeFileSync } from 'fs';
import stringify from 'json-stable-stringify';

fetch('https://static.openfoodfacts.org/data/taxonomies/ingredients.json').then(async (response) => {
    writeFileSync('ciqual/ingredients.json', stringify(await response.json(), {space: 2}));
});

