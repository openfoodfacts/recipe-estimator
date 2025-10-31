# Recipe Estimator 🍽️

[![Tests](https://github.com/openfoodfacts/recipe-estimator/workflows/Tests/badge.svg)](https://github.com/openfoodfacts/recipe-estimator/actions)

The Recipe Estimator analyzes food products to estimate ingredient proportions based on nutritional information. It's part of the [Open Food Facts](https://openfoodfacts.org) ecosystem, helping to understand what's really in our food.

<img src="https://github.com/openfoodfacts/recipe-estimator/blob/main/docs/2025-poster-recipe-estimator.png"/>


## 🚀 Try It Now

- **Production**: [recipe-estimator.openfoodfacts.org](https://recipe-estimator.openfoodfacts.org/static/#3017620422003)
- **Staging**: [recipe-estimator.openfoodfacts.net](https://recipe-estimator.openfoodfacts.net/static/#3017620422003)

## 🎯 What Does It Do?

Given a food product with:
- Ingredient list (e.g., "tomatoes, water, sugar, salt")  
- Nutritional information (e.g., "3.2g protein per 100g")

The Recipe Estimator calculates the likely proportion of each ingredient using optimization algorithms that match the nutritional profile.

## 📚 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Set up your development environment
- **[Development Guide](docs/DEVELOPMENT.md)** - Run locally, test, and contribute  
- **[How It Works](docs/HOW_IT_WORKS.md)** - Technical details and algorithms
- **[Community Resources](docs/COMMUNITY.md)** - Links, deployments, and support

## ⚡ Quick Start

1. **Install dependencies:**
   ```bash
   make install
   ```

2. **Run the application:**
   ```bash
   # Backend (API server)
   make watch
   
   # Frontend (in another terminal)
   make watch_frontend
   ```

3. **Test it:**
   - Backend: `http://localhost:5521/static/#0677294998025`
   - Frontend: `http://localhost:3000/#0677294998025`

## 🧪 Running Tests

```bash
pytest
# or
make tests
```

## 🐳 Docker

```bash
# Build and run with docker-compose
make up
```

Access at: `http://localhost:5520/static/#0677294998025`

## 🤝 Community & Support

- **💬 Slack Channel**: [#recipe-estimator](https://openfoodfacts.slack.com/archives/C08BDAWPJP7) ([Join here](https://slack.openfoodfacts.org))
- **📖 Wiki**: [Recipe Tool Documentation](https://wiki.openfoodfacts.org/Recipe/Tool)  
- **📋 Project Poster**: [Visual Overview](https://slack-files.com/T02KVRT1Q-F09EEEV7FU3-16a07789bb)
- **🎓 Getting Started**: [Presentation](https://docs.google.com/presentation/d/1QM7ATc-7eTzc-Tq3xf9Mi-0eOn_ZZeHTOaAmI7t1zds/edit?slide=id.g2a73fcafc65_0_17#slide=id.g2a73fcafc65_0_17)

## 🛠️ For Developers

### Available Commands

```bash
make install          # Install all dependencies
make watch            # Run backend with auto-reload  
make watch_frontend   # Run frontend with auto-reload
make tests            # Run tests
make build            # Build Docker image
make up               # Run with docker-compose
```

### Project Structure

- `frontend/` - React application  
- `recipe_estimator/` - Python FastAPI backend
- `docs/` - Additional documentation
- `ciqual/` - CIQUAL nutritional database files
- `scripts/` - Build and maintenance scripts

## 🔧 Contributing

1. **Join the community**: Connect with us on [Slack](https://slack.openfoodfacts.org)
2. **Read the docs**: Check the [Wiki](https://wiki.openfoodfacts.org/Recipe/Tool) and [project documents](docs/COMMUNITY.md)
3. **Set up locally**: Follow the [Installation Guide](docs/INSTALLATION.md)
4. **Start developing**: Use the [Development Guide](docs/DEVELOPMENT.md)

We welcome contributions of all kinds - code, documentation, testing, and feedback!

---

**Part of the [Open Food Facts](https://openfoodfacts.org) ecosystem** 🌍

