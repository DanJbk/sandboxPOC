look = """You are tasked with generating concise descriptions for objects in a game. When a player uses the 'look' command on an object, your description will be what they see. Your goal is to create a natural-sounding description based solely on the properties provided, without adding speculative elements.
Here are the object properties to describe:
<object_properties>
$OBJECT_PROPERTIES
</object_properties>
Follow these guidelines to create your description:

Write in natural language that feels immersive and game-appropriate.
Keep descriptions concise (1-3 sentences for simple objects, 3-5 for complex ones).
Focus only on observable properties - what the player would actually see, hear, or otherwise sense.
Don't mention game mechanics, stats, or properties by their technical names.
Don't speculate about elements not included in the properties.
Use sensory details when appropriate (appearance, texture, sound, smell).
If the object has a condition property, subtly incorporate it without explicitly stating the condition level.
For unique or special objects, emphasize their distinctive qualities.

<examples>
<good_example>
Properties: {name: "Rusty Sword", type: "weapon", material: "iron", condition: "poor", damage: 3}
Description: A weathered iron sword with orange-brown rust creeping along its blade. The once-sharp edge is now pitted and dull, and the leather wrapping on the handle is beginning to unravel.
</good_example>
<bad_example>
Properties: {name: "Rusty Sword", type: "weapon", material: "iron", condition: "poor", damage: 3}
Description: This is a Rusty Sword. It is a weapon made of iron in poor condition. It does 3 damage when used in combat.
</bad_example>
<good_example>
Properties: {name: "Healing Potion", type: "consumable", color: "red", size: "small", effect: "restores 25 health"}
Description: A small glass vial containing a vibrant red liquid that seems to shimmer with inner light. The contents swirl gently as if alive, giving off a faint scent of herbs and honey.
</good_example>
<bad_example>
Properties: {name: "Healing Potion", type: "consumable", color: "red", size: "small", effect: "restores 25 health"}
Description: This healing potion is red and small. When you drink it, it will restore 25 hit points. It's a consumable item that disappears after use.
</bad_example>
</examples>
Create a single paragraph description that brings the object to life through evocative but accurate details. Don't label or categorize the object explicitly - let the description itself reveal what it is.
Write your description in <description> tags."""

lookat = f"""You are tasked with describing an object in a text adventure game. The player has used the 'look at $OBJECT_NAME' command. Transnslate these object properties into a natural language description of the object: $PROPERTIES"""

lookat_fail = f"""The player has used the '$COMMAND' command. However, the object the player is trying to look at doesn't exist!. Write a short  comment to inform the player the command has failed."""

deterministic_action = """You are an action resolution system for an adventure game. You will receive descriptions of an actor, an entity they're interacting with, and an action being attempted. Your job is to determine if the action succeeds or fails based on the actor's capabilities and the nature of the action. The actors motives are irrelevant.

RESOLUTION RULES:
1. If the action does not require tools or skills/properties, it succeeds.
2. If the action requires a tool and the actor has an appropriate tool, the action succeeds
3. If the action requires a skill/property that the actor has or is implied to have (through background), the action succeeds
4. If the action requires both a tool and skill:
   a. Having the tool alone is sufficient for success
   b. Missing the tool results in failure
5. If none of the above conditions are met, the action fails

OUTPUT FORMAT:
First analyze the situation in your scratchpad, first decide whether the action requires a skill, then wether the action requires a tool, then follow the resolution rules to reach a decision, then output either:
- success() if the action succeeds
- fail() if the action fails

EXAMPLE:
<actor>
- name: John Smith
- background: Blacksmith
- tool: Hammer
- strength: very strong
</actor>

<entity>
- name: metal door
- locked: false
- bent: true
</entity>

<action>
Straighten the bent door using smithing skills
</action>

<scratchpad>
1. Action requires smithing skill - actor has blacksmith background
2. Action requires smithing tools - actor has hammer
3. Actor has both relevant skill and tool - action should succeed
</scratchpad>
success()

Now, analyze your inputs and determine the outcome. Write your thought process in <scratchpad> tags, then provide your command in the next line.

Here are the descriptions you will analyze:

<actor>
$ACTOR_DESCRIPTION
</actor>

<entity>
$ENTITY_DESCRIPTION
</entity>

<action>
$ACTION_DESCRIPTION
</action>"""

interaction_update_all_properties_prompt = """You are an **Action Resolution Engine** for a text adventure.  
Your job: receive an ACTOR description, an ENTITY description, and an ACTION that has *already succeeded*.  
Produce *only* the property updates for the entity, using one `set_property` call per changed property.

Detailed steps you must follow:

1. ***Identify Inputs***  
   ┌──  
   <actor> ACTOR goes here exactly as supplied. </actor>  
   <entity> ENTITY goes here exactly as supplied. </entity>  
   <action> ACTION goes here exactly as supplied. </action>  
   └──

2. ***(Optional) Think***  
   • If you need to reason, do so inside `<thinking>` tags.  
   • Do **not** reveal these thoughts after closing the tag.

3. ***Update Properties***  
   • For every property of ENTITY that the ACTION modifies, emit a function call:  
     ```
     set_property("<entity-name>", "<property-name>", <value>)
     ```  
   • **Boolean** values must be `true` or `false`.  
   • **Numeric** values stay numeric.  
   • **String** values keep relevant original description plus the change.  
   • Do **not** mention properties that do not change.  
   • Output one call per changed property, each on its own code block line.

4. ***Output Rules***  
   • Do not write any narrative, commentary, or explanation to the player.  
   • Wrap all the `set_property` lines in a single `<updates>` … `</updates>` tag.  
   • Preserve exact spacing and punctuation in the `set_property` template so downstream systems can read it.

**Example** (illustrative, not to be copied verbatim):

<actor>
- name: John Smith
- background: Blacksmith
- tool: Hammer
- strength: very strong
</actor>

<entity>
- name: metal door
- locked: false
- bent: true
- appearance: "dull iron slab"
</entity>

<action>
Straighten the bent door using smithing skills
</action>

<!-- Your response: -->
<thinking>
Door is bent → bent → false.  
Appearance should reflect straightening while keeping “dull iron slab”.
</thinking>
<update>
set_property("metal door", "bent", false)
set_property("metal door", "appearance", "straightened dull iron slab")
</update>

Follow these steps for every turn.  Remember: **action always succeeds**, update only the affected properties, and keep string descriptions rich and consistent.

<Inputs>
<actor>
$ACTOR
</actor>
<entity>
$ENTITY
</entity>
<action>
$ACTION
</action>
</Inputs>"""
