# Proof of concept for an LLM-Powered RPG Adventure Game

A Proof of concept for a text-based top-down adventure game with an LLM acting as the Game Master to determine action outcomes.
![python3 13_Ny2Knm6VyP](https://github.com/user-attachments/assets/09f78b6b-fa4b-4d06-a74c-2ce317eeec6e)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the LLM:
   - Install Ollama from [https://ollama.ai](https://ollama.ai)
   - Start your chosen model in a separate terminal:
     ```bash
     ollama run <model-name>
     ```
   - Update the `MODEL` variable in `lm_com.py` to match your chosen model

## How to Play

### Controls

| Key/Action | Description |
|------------|-------------|
| `TAB` | Opens the command window for entering text commands |
| `W`, `A`, `S`, `D` | Movement controls (up, left, down, right) |
| `Arrow Keys` | Scroll through the command window history |
| `Left Mouse Click` | Enter "interact mode" - the next command you type will have the LLM determine the outcome of an action on the selected entity (click elsewhere to cancel) |
| `Right Mouse Click` | Open debug information and add the entity's name to the command window |

### Basic Commands

| Command | Description |
|---------|-------------|
| `look` | Get information about your surroundings |
| `look at <entity_name>` | Examine a specific entity in detail |
| `pickup <entity_name>` | Add an item to your inventory |
| `inventory` | View the items you're carrying |
| `<interact mode>` | entered when left clicking an entity with the mouse, currently effects only the target of the interaction |

### Advanced Interaction

The game uses an LLM to interpret your actions and determine outcomes. When in "interact mode" (after left-clicking an entity), you can type natural language commands like:
- `write name on ledger`
- `open the rusty door with a dagger`
- `clean dust from table`

Your character might need to be at a close proximity to an object to interact with it.

## Future features

* support trade.
* two-way interaction updates.
* dialog system.
* ...
