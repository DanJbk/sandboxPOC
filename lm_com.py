import requests
import json
import sys

# MODEL = "qwen3:14b"
# MODEL = "qwen2.5:14b"
# MODEL = "gemma3:12b"
# MODEL = "mistral"
# MODEL = "hf.co/LatitudeGames/Wayfarer-Large-70B-Llama-3.3-GGUF:IQ1_S"
MODEL = "phi4:14b-q8_0"

def generate_text_stream(prompt, model=MODEL, options={"temperature": 0}):
    """
    Send a request to the Ollama API to generate text using the specified model.
    Returns a generator that yields each token/chunk of the response.

    Args:
        prompt (str): The input prompt for text generation
        model (str): The model to use (default: "qwen2.5")

    Yields:
        str: Each token or chunk of the generated text response.
    Options guidelines:
        Repeat penalty prevents: "The cat sat on the mat. The cat sat on the mat."
        Presence penalty prevents: "Cats are mammals. Cats have fur. Cats make good pets."
        Frequency penalty prevents: "I really like this. I really enjoy that. I really appreciate those."
    """
    url = "http://localhost:11434/api/generate"

    # Prepare the request payload
    payload = {
        "model": model, 
        "prompt": prompt,
    }

    if options:
        payload["options"] = options

    try:
        # Send POST request with stream=True to get response chunks
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    json_response = json.loads(line)
                    if "response" in json_response:
                        chunk = json_response["response"]
                        yield chunk

                    # Stop yielding if this is the last message
                    if json_response.get("done", False):
                        break
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}", file=sys.stderr)
        return


def generate_text_non_streaming(prompt, model=MODEL, options={}):
    """
    Send a request to the Ollama API to generate text using the specified model.
    Collects the entire response and returns it as a single string.

    Args:
        prompt (str): The input prompt for text generation
        model (str): The model to use (default: "qwen2.5")

    Returns:
        str: The full generated text response.
    """
    url = "http://localhost:11434/api/generate"

    # Prepare the request payload
    payload = {"model": model, "prompt": prompt}

    if options:
        payload["options"] = options

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        # Collect the entire response as JSON
        full_response = ""
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line)
                if "response" in json_response:
                    full_response += json_response["response"]

                # Stop processing if this is the last message
                if json_response.get("done", False):
                    break

        return full_response.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    text_generator = generate_text_stream("why is the sky blue?")

    for i in range(1000):
        try:
            token = next(text_generator)
            print(token, end="", flush=True)
        except StopIteration:
            print("done")
            break

    print("done stream")