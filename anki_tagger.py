import csv
import io
from tqdm import tqdm
import os
from openai import OpenAI
import re
import argparse


def read_ankitxt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        comments = [line for line in file if line.startswith("#")]
    with open(file_path, "r", encoding="utf-8") as file:
        content = "".join(line for line in file if not line.startswith("#"))
        filtered_content = io.StringIO(content)
        reader = csv.reader(filtered_content, delimiter="\t")
    return reader, comments


def create_assistant(openAI_APIkey, tags_instructions):
    client = OpenAI(api_key=openAI_APIkey)

    assistant = client.beta.assistants.create(
        name="Anki Tagger",
        instructions=f"The following messages will contain one or more ankidroid card, front and back. Each different card will be on each line. Your role is to provide tags for each card. When answering, write the FRONT of the card first and then the tags within <tags></tags>. The tags will be space separated. Each tag can be a single word. {tags_instructions}.  \nExample Message: \nFRONT: Cross entropy and NLL in pytorch BACK: CL always expects inputs to be logits. It will do the softmax transformation itself.<br><br>NLL expects them to be probabilities\nFRONT: Terminal lucidity BACK: Unexpected mental clarity and memory shortly before deaths in patients suffering from neurological disorders such as alzhaimer\n\nExample Response:\n FRONT: Cross entropy and NLL in pytorch <tags> ml</tags>\nFRONT: Terminal lucidity <tags>gen</tags>\nNote that the BACK can sometime be empty. This is totally normal. Always answer with the FRONT and the <tags></tags>",
        model="gpt-3.5-turbo-0125",
    )
    return assistant, client


def get_tagged_cards(assistant, client, batch_cards):
    message_txt = "\n".join(
        [f"FRONT: {c[map['front']]} BACK: {c[map['back']]}" for c in batch_cards]
    )
    only_front = [f"FRONT: {c[map['front']]}" for c in batch_cards]

    thread = client.beta.threads.create()

    msg = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=message_txt
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    if run.status == "completed":
        gpt_output = client.beta.threads.messages.list(thread_id=thread.id)
    tags_pattern = r"<tags>(.*?)<\/tags>"
    batch_output_tags = []

    gpt_output_split = gpt_output.data[0].content[0].text.value.split("\n")
    gpt_output_only_front = [g.split("<tags")[0] for g in gpt_output_split]

    for idx, msg_card in enumerate(only_front):
        gpt_found_output = [
            gpt_output_split[i]
            for i, _ in enumerate(gpt_output_only_front)
            if msg_card.strip() == gpt_output_only_front[i].strip()
        ]
        if len(gpt_found_output) > 0:
            try:
                batch_output_tags.append(
                    re.search(
                        tags_pattern, gpt_found_output[0], re.IGNORECASE | re.DOTALL
                    ).group(1)
                )
            except AttributeError:
                batch_output_tags.append("")
        else:
            batch_output_tags.append("")
    return batch_output_tags


def merge_tags(batch_cards, batch_tags):
    for idx, card in enumerate(batch_cards):
        pre_tags = card[map["tags"]].split(" ")
        tags = " ".join(
            [i for i in set(batch_tags[idx].split(" ")).union(set(pre_tags)) if i != ""]
        )
        card[map["tags"]] = tags
    return batch_cards


def process(
    input_file,
    output_file,
    only_untagged,
    start_from_card,
    openAI_APIkey,
    tags_instructions,
):
    assistant, client = create_assistant(openAI_APIkey, tags_instructions)
    # starting_batch = 209 + 33 + 12 + 78
    if not os.path.exists(output_file):
        with open(output_file, "w", encoding="utf-8") as file:
            pass
    batch_size = 20
    all_cards, comments = read_ankitxt(input_file)

    all_cards = list(all_cards)
    all_cards = all_cards[start_from_card:]
    if only_untagged:
        all_cards = [r for r in all_cards if r[map["tags"]] in ["", "leech"]]

    with open(output_file, "r", encoding="utf-8") as file:
        content = "".join(line for line in file if not line.startswith("#"))

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        file.writelines(comments)
        file.writelines(content)
        writer = csv.writer(file, delimiter="\t")
        pbar = tqdm(total=len(all_cards), unit="item")
        for i in range(0, len(all_cards), batch_size):
            batch_cards = all_cards[i : i + batch_size]
            batch_output_tags = get_tagged_cards(assistant, client, batch_cards)
            if len(batch_output_tags) != len(batch_cards):
                print(
                    f"Error in batch {i}, len tags output ({len(batch_output_tags)} doesn't match number of cards ({len(batch_cards)}). If the error persist, reduce the batch size"
                )
                batch_output_tags = ["unsure"] * len(batch_cards)
            merge_tags(batch_cards, batch_output_tags)
            writer.writerows(batch_cards)

            pbar.update(min(batch_size, len(all_cards) - i))


map = {"guid": 0, "notetype": 1, "deck": 2, "front": 3, "back": 4, "tags": 11}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        By default, the new cards are APPENDED to the output file, is it already exists. Once this is finished, you  can import your collection in Anki. IT IS STRONGLY RECCOMENDED TO BACKUP YOUR COLLECTION BEFORE IMPORTING THIS UPDATED ONE. In the Import Options select Existing notes: Updated. 
        Example Usage
        python anki -i example_deck.txt -o output.txt
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--input_file",
        "-i",
        default="output3.txt",
    )
    parser.add_argument(
        "--output_file",
        "-o",
        default="output.txt",
    )
    parser.add_argument(
        "--only_untagged",
        help="We will ignore any card that already contain a tag (excluding the default tag `leech`)",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--start_from_card",
        "-sc",
        type=int,
        default=0,
        help="Start from card at index n",
    )
    parser.add_argument(
        "--openAI_APIkey",
        "-k",
        default=os.environ["openAI_API_key"],
        help="Start from card at index n",
    )
    parser.add_argument(
        "--tags_instructions",
        default="Tags will need to come from this set: `math`, `ML` (machine learning), `CV` (computer vision), `psycho` (psychology), `hist` (history), `rats` (rationality), `coding`, `physics`, `gen` (general knowledge), `music`, `evo` (evolution). If a card doesn't match any of this tag, just leave the corresponding line empty or make up your own tag. ",
    )
    args = parser.parse_known_args()[0]
    process(**args.__dict__)
