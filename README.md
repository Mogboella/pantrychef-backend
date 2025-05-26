# PantryChef API Documentation

API for recommending recipes based on pantry ingredients

## Base URL
All endpoints are prefixed with `/api`

## Authentication
The API uses session-based authentication with headers:
- `X-Session-ID`: Session identifier
- `Session-Token`: Session authentication token

Both headers are optional but recommended for personalized experiences.

---

## Recipes Endpoints

### GET `/api/recipes/`
Search and filter recipes with optional query parameters.

**Parameters:**
- `query` (string, optional): Search query for recipe discovery
- `cuisine` (string, optional): Filter by cuisine type
- `max_time` (integer, optional): Maximum cooking time in minutes
- `max_missing` (integer, optional): Maximum number of missing ingredients allowed

**Response:** Array of `Recipe` objects

**Example:**
```bash
GET /api/recipes/?query=pasta&cuisine=italian&max_time=30&max_missing=2
```

### POST `/api/recipes/recommend`
Get personalized recipe recommendations based on your pantry items.

**Parameters:**
- `max_missing` (integer, optional): Maximum missing ingredients allowed
- `min_score` (number, optional, default: 0.4): Minimum match score threshold

**Response:** Array of recommended recipes with scores

**Example:**
```bash
POST /api/recipes/recommend?max_missing=3&min_score=0.5
```

### GET `/api/recipes/{recipe_id}`
Get detailed information about a specific recipe.

**Parameters:**
- `recipe_id` (string, required): Unique recipe identifier

**Response:** `RecipeDB` object with full recipe details

**Example:**
```bash
GET /api/recipes/abc123
```

---

## Session Management

### POST `/api/sessions/`
Create a new session with initial pantry items, can optionally include no pantry items `[]`.

**Request Body:**
```json
["tomatoes", "pasta", "cheese", "basil"]
```

**Response:** Session information object

**Example:**
```bash
curl -X POST /api/sessions/ \
  -H "Content-Type: application/json" \
  -d '["tomatoes", "pasta", "cheese"]'
```

---

## Pantry Management

### POST `/api/pantry/`
Add a new item to your pantry.

**Request Body:**
```json
{
  "ingredient": {
    "name": "tomatoes",
    "unit": "lbs",
    "quantity": "2"
  },
  "expiry_date": "2024-12-31T23:59:59"
}
```

**Response:** `PantryItemOut` object

### GET `/api/pantry/`
Retrieve all pantry items for your session.

**Parameters:**
- `expiring_soon` (boolean, optional, default: false): Filter for items expiring soon

**Response:** Array of `PantryItemOut` objects

**Example:**
```bash
GET /api/pantry/?expiring_soon=true
```

### DELETE `/api/pantry/{item_id}`
Remove an item from your pantry.

**Parameters:**
- `item_id` (integer, required): Pantry item ID

**Example:**
```bash
DELETE /api/pantry/123
```

---

## Grocery List Management

### POST `/api/pantry/grocery`
Add ingredients to your grocery list (typically missing ingredients from recipes).

**Request Body:**
```json
[
  {
    "name": "milk",
    "unit": "cups",
    "quantity": "2"
  },
  {
    "name": "eggs",
    "unit": "pieces",
    "quantity": "6"
  }
]
```

**Response:** Array of `GroceryItemOut` objects

### GET `/api/pantry/grocery`
Get your grocery list with optional filtering.

**Parameters:**
- `purchased` (boolean, optional): Filter by purchase status
  - `true`: Only purchased items
  - `false`: Only unpurchased items
  - `null`: All items

**Response:** Array of `GroceryItemOut` objects

### PATCH `/api/pantry/grocery/{item_id}/toggle`
Toggle the purchased status of a grocery item.

**Parameters:**
- `item_id` (integer, required): Grocery item ID

**Response:** Updated `GroceryItemOut` object

### DELETE `/api/pantry/grocery/{item_id}`
Remove an item from your grocery list.

**Parameters:**
- `item_id` (integer, required): Grocery item ID

---

## Data Models

### Recipe
```json
{
  "title": "Spaghetti Carbonara",
  "ingredients": [
    {
      "name": "spaghetti",
      "unit": "lbs",
      "quantity": "1"
    }
  ],
  "prep_time": "15 minutes",
  "cook_time": "20 minutes",
  "image_url": "https://example.com/image.jpg",
  "source_url": "https://example.com/recipe",
  "source": "allrecipes"
}
```

### PantryItemOut
```json
{
  "ingredient": {
    "name": "tomatoes",
    "unit": "lbs",
    "quantity": "2"
  },
  "expiry_date": "2024-12-31T23:59:59Z",
  "id": 123,
  "created_at": "2024-01-01T12:00:00Z",
  "normalized_name": "tomatoes"
}
```

### GroceryItemOut
```json
{
  "ingredient": {
    "name": "milk",
    "unit": "cups",
    "quantity": "2"
  },
  "id": 456,
  "session_id": "session-123",
  "normalized_name": "milk",
  "purchased": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

## Typical Workflow

1. **Create Session**: `POST /api/sessions/` with initial pantry items
2. **Manage Pantry**: Use `/api/pantry/` endpoints to add/remove ingredients
3. **Get Recommendations**: `POST /api/recipes/recommend` for personalized suggestions
4. **Search Recipes**: `GET /api/recipes/` with filters if you want something specific
5. **Add to Grocery List**: `POST /api/pantry/grocery` with missing ingredients
6. **Manage Shopping**: Use grocery endpoints to track purchases

---

## Error Responses

All endpoints return standard HTTP status codes:
- `200`: Success
- `422`: Validation Error - Check request format and required fields
- `500`: Server Error

Validation errors include details about which fields are invalid:
```json
{
  "detail": [
    {
      "loc": ["body", "ingredient", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```