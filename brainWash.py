from google import genai
import os
from google.genai import types
import base64

#find key
from dotenv import load_dotenv
load_dotenv()
api_key = AIzaSyAWMJfbmk333lVpwrPjj5rd82_jWz8_Ac8
#alterntively from terminal export GEMINI_API_KEY=....


prompt = """{
  "system_logic": {
    "input_method": "natural_language_vibe_check",
    "scoring_model": {
      "range": "1-20",
      "criteria": {
        "1-5": "Micro-tasks (< 5 mins, low effort)",
        "6-10": "Standard Chores (15-30 mins, medium effort)",
        "11-15": "Heavy Lifting (30-60 mins, sweat involved)",
        "16-20": "Boss Raids (> 1 hour or disgusting tasks)"
      }
    }
  },
  "simulation_example": {
    "user_raw_input": "We live in a chaotic student loft with 3 roommates. It's got a huge kitchen we use for parties, 2 bathrooms that get gross fast, and a gaming corner. We need help remembering to buy toilet paper and taking out the recycling. Oh, and watering the plants on the balcony.",
    "ai_parsing_result": {
      "detected_attributes": {
        "housing_type": "Loft / Apartment",
        "vibe_tags": ["chaotic", "social", "student"],
        "occupants": 3,
        "explicit_requests": ["buy toilet paper", "recycling", "water plants"],
        "detected_rooms": ["Huge Kitchen", "2 Bathrooms", "Gaming Corner", "Balcony"]
      }
    },
    "generated_task_list": [
      {
        "id": "task_01",
        "title": "The Morning Aftermath",
        "type": "Kitchen Cleanup",
        "description": "Deep clean the huge kitchen after a party usage.",
        "score": 18,
        "origin": "inferred_from_text: 'huge kitchen we use for parties'",
        "edit_options": {
          "editable": true,
          "suggested_modifiers": ["Add 'Mop Floor' (+2 pts)"]
        }
      },
      {
        "id": "task_02",
        "title": "Biohazard Containment",
        "type": "Bathroom Deep Clean",
        "description": "Scrub both bathrooms before they reach critical mass.",
        "score": 20,
        "origin": "inferred_from_text: 'get gross fast'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_03",
        "title": "Tech Support",
        "type": "Tidy Up",
        "description": "Declutter the gaming corner, remove empty cans/wrappers.",
        "score": 8,
        "origin": "inferred_from_text: 'gaming corner'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_04",
        "title": "Supply Drop",
        "type": "Shopping",
        "description": "Restock critical inventory: Toilet Paper.",
        "score": 5,
        "origin": "explicit_request: 'buy toilet paper'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_05",
        "title": "Ecological Sortie",
        "type": "Trash/Recycling",
        "description": "Sort and take out the recycling.",
        "score": 6,
        "origin": "explicit_request: 'taking out recycling'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_06",
        "title": "Druid Ritual",
        "type": "Plant Care",
        "description": "Water the plants on the balcony.",
        "score": 4,
        "origin": "explicit_request: 'watering plants'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_07",
        "title": "Chaos Control",
        "type": "General Tidy",
        "description": "15-minute speed clean of the common 'student loft' area.",
        "score": 10,
        "origin": "inferred_from_text: 'chaotic'",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_08",
        "title": "Trash Eviction",
        "type": "Trash",
        "description": "Take out general refuse (non-recycling).",
        "score": 5,
        "origin": "system_default_necessary_task",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_09",
        "title": "Floor Is Lava",
        "type": "Vacuum/Sweep",
        "description": "Sweep the main loft area.",
        "score": 12,
        "origin": "system_default_necessary_task",
        "edit_options": {
          "editable": true
        }
      },
      {
        "id": "task_10",
        "title": "The Dish Pit",
        "type": "Dishes",
        "description": "Daily load/unload or handwash of dishes.",
        "score": 9,
        "origin": "system_default_necessary_task",
        "edit_options": {
          "editable": true
        }
      }
    ]
  },
  "api_structure": {
    "request_endpoint": "/api/generate_tasks_from_vibe",
    "request_body": {
      "user_id": "12345",
      "vibe_text": "string"
    },
    "response_body": {
      "status": "success",
      "suggested_tasks": "array_of_task_objects"
    }
  }
}"""

def generate():
    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    tools = [
        types.Tool(),
    ]
    generate_content_config = types.GenerateContentConfig(
        tools=tools,
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    generate()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

