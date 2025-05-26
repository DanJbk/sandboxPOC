from lm_com import generate_text_stream, generate_text_non_streaming
import descriptive_prompts as dp
from utils import extract_called_function_args, extract_tags, get_entity_description


class llm_logic:


    def parse_player_input(
        turn, text, player_entity, obj_entities, 
    ):  # todo replace with target entity (singular)
        if text.lower().startswith("look at"):
            prompt = llm_logic.look_at_command(text, obj_entities)
            text_output  = generate_text_stream(prompt)
            return {"output": text_output, "type": "print", "generated": True, "target": None} 
        
        elif text.lower().startswith("look"):
            prompt = llm_logic.look_command(text, player_entity, 
                                            [obj for obj in obj_entities if 
                                             obj.properties.get("name", "") != player_entity.properties["name"]
            ])
            text_output  = generate_text_non_streaming(prompt)
            text_output = extract_tags(text_output, tag_name='description')
            return {"output": string_gen(text_output), "type": "print", "generated": True, "target": None} 

        elif text.lower().startswith("pickup") or text.lower().startswith("pick up"):

            prompt, obj_index = llm_logic.pick_up_command(turn, text, player_entity, obj_entities)
            
            if obj_index == -1:
                return {
                    "output": string_gen(prompt),
                    "text": prompt,
                    "type": "pickup", 
                    "generated": False, 
                    "target": None
                }
            
            text_output = generate_text_non_streaming(prompt)

            return {
                "output": string_gen(text_output),
                "text": text_output,
                "type": "pickup", 
                "generated": False, 
                "target": {
                    "entity_index": obj_index,
                    "property": "success()" in text_output and "failure()" not in text_output,
                }
            }
        
        elif turn.lower().startswith("interact"):

            prompt, obj_index = llm_logic.do_command(turn, text, player_entity, obj_entities)
            text_output = generate_text_non_streaming(prompt)
            print(prompt)
            print("# ---")
            print(text_output)
            return {
                "output": string_gen(text_output),
                "text": text_output,
                "type": "do", 
                "generated": False, 
                "target": {
                    "entity_index": obj_index,
                    "property": None,
                }
            }
        elif turn.lower().startswith("trade"):
            prompt, trade_target, obj_index = llm_logic.inventory_trade_command(turn, text, player_entity, obj_entities)
            print(prompt)
            text_output = generate_text_non_streaming(prompt)
            trade_result = extract_called_function_args(text_output, "trade")

            return {
                "output": string_gen(text_output),
                "text": text_output,
                "type": "trade", 
                "generated": False, 
                "target": {
                    "entity_index": obj_index,
                    "property": trade_result,
                }
            }
        else:
            prompt = text

        text_generator = generate_text_stream(prompt=prompt)
        return {"output": text_generator, "type": "print", "generated": True, "target": None} 


    def look_command(text, player_entity, obj_entities):
        fitting_objs = [
            obj
            for obj in obj_entities
            if (player_entity.position).distance_to(obj.position) < 4
        ]

        fitting_objs = sorted(fitting_objs, key=lambda x: x.position.distance_to(player_entity.position))

        obj_properties = "\n".join([f"{obj.properties["name"]}:\n * {'\n * '.join([f"{k}: {v}" 
                            for k, v in obj.properties.items() 
                            if k not in ["name", "npc"]])}".strip()
                            for obj in fitting_objs])
        
        obj_properties = "\n".join([
                            f"{obj.properties["name"]}:\n" + get_entity_description(obj, include_inventory=False, exclude_properties=["name", "npc"], exclude_invisible_properties=True)
                            for obj in fitting_objs])
                
        prompt = dp.look.replace("$OBJECT_PROPERTIES", obj_properties)

        return prompt


    def look_at_command(text, obj_entities):
        
        obj_named = text[len("look at "):].strip()

        fitting_objs = [
            obj
            for obj in obj_entities
            if obj_named in obj.properties.get("name", "")
        ]

        if len(fitting_objs) > 0:
            obj = fitting_objs[0]
            obj_name = obj.properties["name"]
            obj_properties = get_entity_description(obj, include_inventory=False, exclude_properties=["name", "npc"], exclude_invisible_properties=True)
            prompt = dp.lookat.replace("$OBJECT_NAME", obj_name).replace(
                "$PROPERTIES", obj_properties
            )
        else:
            prompt = dp.lookat_fail.replace("$COMMAND", text)

        return prompt


    def pick_up_command(turn, text, player_entity, obj_entities):

        actor_desc = get_entity_description(player_entity, include_inventory=False, exclude_properties=None, exclude_invisible_properties=False)

        if text.startswith("pick up"):
            text = text.replace("pick up", "pickup")

        entity_name = text[text.find(" ") + 1 :].strip()
        action = "pickup"
        item_name = text[len("pickup"):].strip().lower()

        fitting_objs = [
            obj
            for obj in obj_entities
            if (player_entity.position).distance_to(obj.position) < 4
        ]

        fitting_objs = [
            obj
            for obj in fitting_objs
            if (obj.properties.get("name", "") in entity_name.strip().lower()) and (item_name == obj.properties.get("name", "") and obj.render_image)
        ]

        if len(fitting_objs) == 0:
            return f"There is no {entity_name} here.", -1

        obj = fitting_objs[0]

        obj_properties = get_entity_description(obj, include_inventory=False, exclude_properties=None, exclude_invisible_properties=False)
        obj_index = obj_entities.index(obj)
        
        prompt = (
            dp.deterministic_action.replace("$ACTOR_DESCRIPTION", actor_desc)
            .replace("$ENTITY_DESCRIPTION", obj_properties)
            .replace("$ACTION_DESCRIPTION", action)
        )

        print(f"pickup")
        print(prompt)
        return prompt, obj_index

    def do_command(turn, text, player_entity, obj_entities):

        actor_desc = get_entity_description(player_entity, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)

        _, entity_name = tuple(turn.split("->"))
        action = text

        entity_name = entity_name.strip()

        fitting_objs = [
            obj
            for obj in obj_entities
            if (player_entity.position).distance_to(obj.position) < 4
        ]

        fitting_objs = [
            obj
            for obj in fitting_objs
            if obj.properties.get("name", "") in entity_name.strip()
        ]
        obj = fitting_objs[0]
        obj_index = obj_entities.index(obj)
        obj_properties = get_entity_description(obj, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)
        
        prompt = (
            dp.deterministic_action.replace("$ACTOR_DESCRIPTION", actor_desc)
            .replace("$ENTITY_DESCRIPTION", obj_properties)
            .replace("$ACTION_DESCRIPTION", action)
        )

        return prompt, obj_index


    def do_interact_all_command(turn, text, player_entity, obj_entities, object_index=-1):

        actor_desc = get_entity_description(player_entity, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)

        _, entity_name = tuple(turn.split("->"))
        action = text

        if object_index < 0:
            entity_name = entity_name.strip()
            fitting_objs = [
                obj
                for obj in obj_entities
                if (player_entity.position).distance_to(obj.position) < 4
            ]
            fitting_objs = [
                obj
                for obj in fitting_objs
                if obj.properties.get("name", "") in entity_name.strip().lower()
            ]
            obj = fitting_objs[0]
            obj_index = obj_entities.index(obj)

        else:
            obj = obj_entities[object_index]
            obj_index = object_index

        obj_properties = get_entity_description(obj, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)

        prompt = (
            dp.interaction_update_all_properties_prompt.replace("$ACTOR", actor_desc)
            .replace("$ENTITY", obj_properties)
            .replace("$ACTION", action)
        )

        return prompt, obj_index

    def inventory_trade_command(turn, text, player_entity, obj_entities):
        # _, obj_named, _ = turn.split("->")
        _, obj_named = turn.split("->")
        
        actor_desc = get_entity_description(player_entity, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)

        action = text
        obj_index = -1
        fitting_objs = [
            obj
            for obj in obj_entities
            if obj_named.strip().lower() in obj.properties.get("name", "")
        ]

        obj = None
        obj_properties = ""
        if len(fitting_objs) > 0:
            obj = fitting_objs[0]
            obj_index = obj_entities.index(obj)
            
            obj_properties = get_entity_description(obj, include_inventory=True, exclude_properties=None, exclude_invisible_properties=False)

        prompt = dp.trade_validation.replace("$ENTITY_DESCRIPTION", obj_properties).replace("$ACTION_DESCRIPTION", action).replace("$ACTOR_DESCRIPTION", actor_desc)
        
        return prompt, obj, obj_index

def string_gen(asting):
    yield asting