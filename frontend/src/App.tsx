import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { API_PATH } from "./api";

import "./App.css";
import Recipe from "./Recipe";
import { Card, CardContent, Typography } from "@mui/material";

function App() {
  const [product, setProduct] = useState<any>({});

  let location = useLocation();
  useEffect(() => {
    function getProduct(id: string) {
      fetch(`${API_PATH}product/${id}`)
        .then((res) => res.json())
        .then(
          (result) => {
            document.title = id + " - " + result.name;
            setProduct(result);
          },
          () => {
            setProduct({});
          }
        );
    }
    getProduct(location.hash.substring(1));
  }, [location]);

  return (
    <>
      <Card>
        <CardContent>
          <Typography>
            {product.product_name} (
            <a
              href={`https://world.openfoodfacts.org/product/${product.code}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {product.code}
            </a>
            )
          </Typography>
          <Typography>{product.ingredients_text}</Typography>
        </CardContent>
      </Card>
      <Recipe product={product} />
    </>
  );
}

export default App;
