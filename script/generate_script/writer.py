import openai
import configparser
import os
import json

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

openai.api_key = config['openai']['api_key']
MODEL = config['openai'].get('model', 'gpt-4-turbo-preview')
TEMPERATURE = float(config['openai'].get('temperature', 0.7))

PROMPT_DIR = 'prompts'
OUTPUT_DIR = 'outputs'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# class OutlineSection(BaseModel):
#     number: str
#     title: str
#     content: str

def load_prompt(step_filename, **kwargs):
    path = os.path.join(PROMPT_DIR, step_filename)
    with open(path, 'r', encoding='utf-8', errors='replace') as file:
        prompt = file.read().format(**kwargs)
    return prompt

def call_openai(prompt, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content.strip()

def call_openai_json(prompt, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()

def save_output(filename, content):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)

def get_attempt_dir(topic):
    # Sanitize topic for folder name
    import re
    safe_topic = re.sub(r'[^\w\-_]+', '_', topic)[:50]
    attempt_dir = os.path.join(OUTPUT_DIR, safe_topic)
    os.makedirs(attempt_dir, exist_ok=True)
    return attempt_dir

def get_last_completed_step(attempt_dir):
    steps = [
        '01_purpose.txt',
        '02_brain_dump.txt',
        '03_outline.txt',
        '04_full_draft.txt',
        '05_revised_draft.txt',
        '06_final_output.txt',
    ]
    for i, step in enumerate(steps):
        if not os.path.exists(os.path.join(attempt_dir, step)):
            return i  # 0 = nothing done, 1 = step 1 done, etc.
    return len(steps)

def required_setup_fields():
    return [
        "topic",
        "point_of_view",
        "tone",
        "target_audience",
        "lore_and_context",
        "length_guidance",
        "special_instructions",
    ]

def check_setup_json(setup_path):
    if not os.path.exists(setup_path):
        return False, f"setup.json not found at {setup_path}"
    with open(setup_path, 'r', encoding='utf-8', errors='replace') as f:
        try:
            data = json.load(f)
        except Exception as e:
            return False, f"setup.json is not valid JSON: {e}"
    missing = [k for k in required_setup_fields() if not data.get(k)]
    if missing:
        return False, f"setup.json is missing or has empty fields: {', '.join(missing)}"
    return True, data

SAMPLE_SETUP = {
    "topic": "Hypnosis script to condition a puppy mindset.",
    "point_of_view": "Third person, addressing the listener directly as 'you.'",
    "tone": "Warm, soothing, authoritative yet gentle. Use repetitive, rhythmic language that reinforces obedience, trust, and playfulness.",
    "target_audience": "Adults interested in consensual hypnosis, pet play, power exchange.",
    "lore_and_context": "The listener is being gently guided into a puppy mindset to foster submissive feelings toward their Master. Emphasis on psychological safety, consensual submission, and joyful obedience.",
    "length_guidance": "Each section should be approximately 300-500 words.",
    "special_instructions": "Avoid infantilization, emphasize playful and animal-like innocence. Use sensory-rich descriptions."
}

def main(folder_name):
    attempt_dir = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(attempt_dir, exist_ok=True)
    setup_path = os.path.join(attempt_dir, 'setup.json')
    valid, setup_result = check_setup_json(setup_path)
    if not valid:
        print(f"{setup_result}\nPlease fill in all required fields in {setup_path} and rerun.")
        return
    setup_config = setup_result
    topic = setup_config["topic"]
    last_step = get_last_completed_step(attempt_dir)
    save_output = lambda fn, c: open(os.path.join(attempt_dir, fn), 'w', encoding='utf-8').write(c)

    # Step 1: Discover Purpose
    if last_step <= 0:
        prompt1 = load_prompt('01_discover_purpose.txt', topic=topic, **setup_config)
        purpose_output = call_openai(prompt1)
        save_output('01_purpose.txt', purpose_output)
        print("✅ Step 1 completed.")
    else:
        with open(os.path.join(attempt_dir, '01_purpose.txt'), encoding='utf-8', errors='replace') as f:
            purpose_output = f.read()

    # Step 2: Brain Dump
    if last_step <= 1:
        prompt2 = load_prompt('02_brain_dump.txt', purpose=purpose_output, **setup_config)
        brain_dump = call_openai(prompt2)
        save_output('02_brain_dump.txt', brain_dump)
        print("✅ Step 2 completed.")
    else:
        with open(os.path.join(attempt_dir, '02_brain_dump.txt'), encoding='utf-8', errors='replace') as f:
            brain_dump = f.read()

    # Step 3: Outline Structure (JSON mode)
    if last_step <= 2:
        system_prompt = (
            "You are an expert script outliner. Always reply with a JSON array of sections, "
            "each with 'number', 'title', and 'content'. JSON ONLY."
        )
        prompt3 = load_prompt('03_outline_structure.txt', brain_dump=brain_dump, **setup_config)
        outline_json_str = call_openai_json(prompt3, system_prompt=system_prompt)
        try:
            outline_sections = json.loads(outline_json_str)
        except Exception as e:
            print("Outline JSON parsing failed:", e)
            return
        save_output('03_outline.txt', json.dumps(outline_sections, indent=2))
        print("✅ Step 3 completed.")
    else:
        with open(os.path.join(attempt_dir, '03_outline.txt'), encoding='utf-8', errors='replace') as f:
            outline_sections = json.load(f)
        with open(os.path.join(attempt_dir, '03_outline.txt'), encoding='utf-8', errors='replace') as f:
            pretty_outline = f.read()

    # Step 4: Draft each section (with previous section ending)
    if last_step <= 4:
        section_contents = []
        prev_section_end = ""
        sections = outline_sections["sections"] if "sections" in outline_sections else outline_sections
        for idx, section in enumerate(sections):
            print(f"Writing section: {section['number']} - {section['title']}")
            # Get previous section ending (last 2 sentences)
            if idx > 0:
                prev_text = section_contents[-1]
                prev_end = '.'.join(prev_text.strip().split('.')[-3:]).strip()
            else:
                prev_end = ""
            prompt4 = load_prompt(
                '04_section_drafting.txt',
                section=f"{section['number']}. {section['title']}\n{section['content']}",
                outline=pretty_outline if 'pretty_outline' in locals() else '',
                previous_section_end=prev_end,
                **setup_config
            )
            section_text = call_openai(prompt4)
            filename = f"04_section_{section['number']}.txt"
            save_output(filename, section_text)
            section_contents.append(section_text)
            print(f"✅ Section {section['number']} drafted.")
        full_draft = '\n\n'.join(section_contents)
        save_output('04_full_draft.txt', full_draft)
    else:
        with open(os.path.join(attempt_dir, '04_full_draft.txt'), encoding='utf-8', errors='replace') as f:
            full_draft = f.read()

    # Step 5: Revision Pass
    if last_step <= 5:
        prompt5 = load_prompt('05_revision_pass.txt', draft=full_draft, **setup_config)
        revised_draft = call_openai(prompt5)
        save_output('05_revised_draft.txt', revised_draft)
        print("✅ Step 5 completed.")
    else:
        with open(os.path.join(attempt_dir, '05_revised_draft.txt'), encoding='utf-8', errors='replace') as f:
            revised_draft = f.read()

    # Step 6: Final Polish
    if last_step <= 6:
        prompt6 = load_prompt('06_final_polish.txt', draft=revised_draft, **setup_config)
        final_output = call_openai(prompt6)
        save_output('06_final_output.txt', final_output)
        print("🎉 Final polished script generated!")
    else:
        with open(os.path.join(attempt_dir, '06_final_output.txt'), encoding='utf-8', errors='replace') as f:
            final_output = f.read()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a script in a given folder (under outputs/). If no folder is given, creates 'default' and a sample setup.json.")
    parser.add_argument("folder", type=str, nargs="?", default="default", help="The folder name under outputs/ to use")
    args = parser.parse_args()

    if not args.folder:
        default_dir = os.path.join(OUTPUT_DIR, "default")
        os.makedirs(default_dir, exist_ok=True)
        setup_path = os.path.join(default_dir, "setup.json")
        if not os.path.exists(setup_path):
            with open(setup_path, 'w', encoding='utf-8') as f:
                json.dump(SAMPLE_SETUP, f, indent=2)
            print(f"Created {setup_path} with a sample template. Please fill it in and rerun with: python writer.py default")
        else:
            print(f"Please fill in all required fields in {setup_path} and rerun with: python writer.py default")
    else:
        main(args.folder)
