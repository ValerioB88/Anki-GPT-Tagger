# Anki-GPT-Tagger

This script automatically enriches your Anki cards with tags suggested by GPT, streamlining the tagging process by analyzing each card's content.

## How to Use

### Step 1: Export Your Deck
1. In Anki Desktop, navigate to `File -> Export`.
2. Set `Export Format` to `Notes in Plain Text (.txt)`.
3. Ensure **all checkboxes** are selected. This includes `Include HTML and media`, `Include tags`, `Include deck name`, `Include notetype name`, and `Include unique identifier`.

### Step 2: Run the Script
- **Set your OpenAI API key**: The script looks for the API key in the `openAI_API_key` environment variable. Alternatively, specify it via the command line with `--openAI_API_key`.
- **Specify tags instructions**: Use the `--tags_instruction` argument. For details, refer to [Default Tag Instructions](#default-tag-instructions). You may also directly modify the instruction string within the script for convenience.
The run with:
```bash
python anki_tagger.py -i %path_to_your_deck.txt% -o output.txt
```

**Example Usages**
```bash
python anki_tagger.py -i alldecks.txt -o output.txt
```
or 
```bash
python anki_tagger.py -i alldecks.txt -o output_any_tags.txt --only_untagged --tags_instructions "Use any tag that you deem appropriate"
``` 


Note that by default the script will *append* new content to the output file, if it already exists. 

**Re-import the deck**
*It is strongly recommended to back up your original deck before importing the updated one. In your Anki desktop: `Fil->Import`. In the `Import Options` select `Existing notes: Updated.`.*
- In Anki Desktop, go to `File -> Import`.
- In `Import Options`, select `Existing notes: Update`.

### Default Tag Instructions 
Tags will need to come from this predefined set: ``, `ML` (machine learning), `CV` (computer vision), `psycho` (psychology), `hist` (history), `rats` (rationality), `coding`, `physics`, `gen` (general knowledge), `music`, `evo` (evolution). Leave the corresponding line empty if a card does not match any tags. Use the tag unsure along with potentially appropriate tags if you're uncertain about the context; this indicates the card requires a double-check.

### Known Problems
Sometime GPT will make up tags that are not in the tag instructions. Sometime GPT will produce the incorrect amount of tags for a batch of cards, in which case we'll skip the whole batch. 