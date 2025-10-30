# Daggerheart Codex API Documentation

This document provides details on the external APIs available for the Daggerheart Codex application. These APIs allow other programs to interact with the adversary and environment data.

## Base URL

The application runs on `http://127.0.0.1:8282` by default. All API endpoints are relative to this base URL.

---

## List Adversaries

Retrieves a list of all adversaries with their basic information.

*   **Endpoint:** `GET /api/adversaries`
*   **Method:** `GET`
*   **Success Response:**
    *   **Code:** 200 OK
    *   **Content:** A JSON array of adversary objects.
*   **Example Response:**
    ```json
    [
      {
        "name": "Acid Burrower",
        "tier": 1,
        "type": "Solo",
        "description": "A horse-sized insect with digging claws and acidic blood."
      },
      {
        "name": "Adult Flickerfly",
        "tier": 3,
        "type": "Solo",
        "description": "A winged insect the size of a large house with iridescent scales and wings that move too fast to track."
      }
    ]
    ```

---

## List Environments

Retrieves a list of all environments with their basic information.

*   **Endpoint:** `GET /api/environments`
_   **Method:** `GET`
*   **Success Response:**
    *   **Code:** 200 OK
    *   **Content:** A JSON array of environment objects.
*   **Example Response:**
    ```json
    [
      {
        "name": "Abandoned Grove",
        "tier": "1",
        "type": "Exploration",
        "description": "A former druidic grove lying fallow and fully reclaimed by nature."
      },
      {
        "name": "Ambushed",
        "tier": "1",
        "type": "Event",
        "description": "An ambush is set to catch an unsuspecting party off-guard."
      }
    ]
    ```

---

## Get Statblock by Name

Retrieves the full statblock for a single adversary or environment by its name.

*   **Endpoint:** `GET /api/stat/<name>`
*   **Method:** `GET`
*   **URL Parameters:**
    *   `name` (required): The name of the adversary or environment. The name is case-insensitive. URL encoding is required for names with spaces or special characters (e.g., `Acid%20Burrower`).
*   **Success Response:**
    *   **Code:** 200 OK
    *   **Content:** The full JSON object for the requested statblock.
*   **Error Response:**
    *   **Code:** 404 Not Found
    *   **Content:** `{"error": "Not found"}`
*   **Example Request:**
    `GET /api/stat/Bear`
*   **Example Response:**
    ```json
    {
      "atk": "+1",
      "category": "Adversaries",
      "damage_dice": "1d8+3",
      "damage_type": "phy",
      "description": "A large bear with thick fur and powerful claws.",
      "difficulty": 14,
      "experience": [
        "Ambusher +3",
        "Keen Senses +2"
      ],
      "features": [
        {
          "description": "Targets who mark HP from the Bear’s standard attack are knocked back to Very Close range.",
          "name": "Overwhelming Force",
          "type": "Passive"
        },
        {
          "description": "Mark a Stress to make an attack against a target within Melee range. On a success, deal 3d4+10 physical damage and the target is Restrained until they break free with a successful Strength Roll.",
          "name": "Bite",
          "type": "Action"
        },
        {
          "description": "When the Bear makes a successful attack against a PC, you gain a Fear.",
          "name": "Momentum",
          "type": "Reaction"
        }
      ],
      "hp": 7,
      "motives_tactics": [
        "Climb",
        "defend territory",
        "pummel",
        "track"
      ],
      "name": "Bear",
      "range": "Melee",
      "stress": 2,
      "thresholds": "9/17",
      "tier": 1,
      "type": "Bruiser",
      "weapon": "Claws"
    }
    ```

---

## Create or Update Statblock

Creates a new statblock or updates an existing one if the name matches.

*   **Endpoint:** `POST /api/save`
*   **Method:** `POST`
*   **Request Body:** A JSON object representing the full statblock. The `name` and `category` fields are required. The structure should match the one used internally (see `data/statblocks_default.json` for examples).
*   **Success Response:**
    *   **Code:** 200 OK
    *   **Content:** `{"saved": true}`
*   **Error Response:**
    *   **Code:** 400 Bad Request
    *   **Content:** `{"error": "Name is required"}`
*   **Example Request Body (for a new Adversary):**
    ```json
    {
        "name": "Cave Spider",
        "category": "Adversaries",
        "tier": 1,
        "type": "Skulk",
        "description": "A large, venomous spider that lurks in the dark.",
        "motives_tactics": "Ambush, web, bite",
        "difficulty": "12",
        "thresholds": "5/10",
        "hp": "4",
        "stress": "2",
        "atk": "+2",
        "weapon": "Bite",
        "range": "Melee",
        "damage_dice": "1d6+2",
        "damage_type": "phy",
        "experience": "Stealth +3",
        "features": [
            {
                "name": "Poisonous Bite",
                "type": "Passive",
                "description": "A creature that takes damage from the spider's bite must succeed on a Strength roll or be poisoned."
            }
        ]
    }
    ```

