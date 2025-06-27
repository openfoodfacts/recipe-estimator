# some settings
import os

# by default we use preprod
OPENFOODFACTS_URL = os.environ.get(
    'OPENFOODFACTS_URL',
    'https://world.openfoodfacts.net'
).rstrip("/")
