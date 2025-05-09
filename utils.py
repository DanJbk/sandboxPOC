import re
import difflib

import re

def extract_property_info(text):
    """
    Extract information from set_property function calls.
    
    Args:
        text (str): String containing set_property function calls
        
    Returns:
        list: List of dictionaries, each containing entity_name, property_name, and value
    """
    # Regular expression pattern to match set_property calls
    pattern = r'set_property\("([^"]+)",\s*"([^"]+)",\s*(.+?)\)'
    
    # Find all matches
    matches = re.findall(pattern, text)
    
    # Convert matches to list of dictionaries
    results = []
    for match in matches:
        entity_name, property_name, value_str = match
        
        # Convert value_str to appropriate Python type
        if value_str.lower() == 'true':
            value = True
        elif value_str.lower() == 'false':
            value = False
        elif value_str.isdigit():
            value = int(value_str)
        elif value_str.replace('.', '', 1).isdigit():
            value = float(value_str)
        elif value_str.startswith('"') and value_str.endswith('"'):
            value = value_str[1:-1]
        else:
            value = value_str
            
        results.append({
            'entity_name': entity_name,
            'property_name': property_name,
            'value': value
        })
    
    return results

def get_entity_description(obj, include_inventory=True, exclude_properties=None, exclude_invisible_properties=True):

    if exclude_properties is None:
        exclude_properties = []
    
    obj_properties = [f"- {k}: {v}" for k, v in obj.properties.items() if (k not in exclude_properties) and not (exclude_invisible_properties and k.startswith("_"))]
    obj_description = "\n".join(obj_properties)
    
    if not include_inventory:
        return obj_description
    
    obj_inventory = "\n- inventory: " + ", ".join([obj.properties["name"] for obj in obj.inventory])
    if len(obj.inventory) == 0:
        "\n- inventory: empty"

    return obj_description + obj_inventory


def extract_called_function_args(text, function_name=None):
    """
    Extract arguments from a function/tool call in the provided text.
    Handles both quoted and unquoted arguments.
    
    Args:
        text (str): The text containing the function call
        function_name (str, optional): Specific function name to look for. 
                                       If None, extracts args from the first function call found.
        
    Returns:
        tuple: A tuple containing the extracted arguments, or empty tuple if no function call found
    """
    if function_name is None:
        # Find the first function call and its name
        first_func_pattern = r'(\w+)\('
        first_func_match = re.search(first_func_pattern, text)
        if first_func_match:
            function_name = first_func_match.group(1)
        else:
            return tuple()
    
    # Pattern to match the full function call
    full_pattern = rf'{function_name}\((.*?)\)'
    full_match = re.search(full_pattern, text)
    
    if not full_match:
        return tuple()
    
    # Get the arguments string inside the parentheses
    args_str = full_match.group(1).strip()
    
    if not args_str:
        return tuple()  # Empty arguments
    
    # First try to find quoted arguments
    quoted_args = re.findall(r'"([^"]*)"', args_str)
    if quoted_args:
        return tuple(quoted_args)
    
    # If no quoted arguments, try to split by comma for unquoted arguments
    unquoted_args = [arg.strip() for arg in args_str.split(',')]
    return tuple(unquoted_args)

def extract_tags(text, tag_name='description'):
    """
    Extract all content between <description> and </description> tags from a text.
    
    Args:
        text (str): The input text containing description tags
        
    Returns:
        list: A list of strings containing the content of each description tag
    """
    pattern = r'<description>(.*?)</description>'.replace('description', tag_name)
    # Using re.DOTALL to make the dot character match newlines as well
    matches = re.findall(pattern, text, re.DOTALL)
    
    # Strip whitespace from each match
    descriptions = [match.strip() for match in matches]
    return "\n".join(descriptions)

def remove_scratchpad(text):
    """
    Removes all content between <scratchpad> tags, including the tags themselves.
    
    Args:
        text (str): The input text containing scratchpad tags
        
    Returns:
        str: The text with all scratchpad content removed
        
    Example:
        >>> text = "Before <scratchpad>Some notes</scratchpad> After"
        >>> remove_scratchpad(text)
        'Before  After'
    """
    try:
        # Pattern to match <scratchpad> tags and their content
        pattern = r'<scratchpad>.*?</scratchpad>'
        
        # Use re.DOTALL flag to match across multiple lines
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        # Remove any double newlines that might have been created
        cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text).strip()
        
        return cleaned_text
    
    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return text
    

def fuzzy_match(query, choices, limit=5):
    """
    Performs fuzzy matching between a query string and a list of choices
    using Python's built-in difflib.
    
    Args:
        query (str): The string to match against.
        choices (list): List of strings to search within.
        limit (int, optional): Maximum number of results to return. Defaults to 5.
    
    Returns:
        list: List of tuples containing (matched_string, similarity_score) sorted by score in descending order.
    """
    # Get similarity scores for each choice
    scores = []
    for choice in choices:
        # Calculate similarity ratio (0 to 1)
        ratio = difflib.SequenceMatcher(None, query.lower(), choice.lower()).ratio()
        # Convert to percentage
        score = int(ratio * 100)
        scores.append((choice, score))
    
    # Sort by score in descending order
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches
    return scores[:limit]

def get_best_match(query, choices):
    """
    Returns only the best match from the choices.
    
    Args:
        query (str): The string to match against.
        choices (list): List of strings to search within.
    
    Returns:
        tuple: (matched_string, similarity_score)
    """
    matches = fuzzy_match(query, choices, limit=1)
    return matches[0] if matches else (None, 0)