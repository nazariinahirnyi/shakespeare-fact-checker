# Fact-Checking Pipeline for Shakespeare Articles

A rule-based pipeline that fact-checks articles about Shakespeare's plays against a corpus of text fragments ("chunks") from those plays. It was my solo entry in the **AI Agentic Club** mini-hackathon (about 20 participants, individual format), where it won first place.

The task, the corpus and the evaluation scripts belong to the organizers and are not included here. See the original task repository: `<link to the original task repo>`.

## What the pipeline does

For every article it produces:

1. **Facts.** Short claims from the article (up to 40 words each), each linked to the corpus chunk that supports it.
2. **Errors.** Sentences where a value is wrong, with the wrong value, the correct value, the source chunk and a short quote from it.

Output is one JSON file per article, in the format required by the task.

## How it works

**1. Indexing.** Every chunk is tokenized (lowercased, possessive `'s` removed, capitalization of names tracked). Stop words are dropped, and each remaining word gets an IDF weight computed over the corpus, so rare words (names, places) count more than common ones.

**2. Locating the source.**
- Chunk ids share a prefix per scene (for example `Ham.3.2`). For each paragraph, the pipeline picks the scene whose chunks best match all of the paragraph's sentences.
- For each sentence it then picks the best chunk inside that scene using an IDF-weighted word overlap score. If a chunk elsewhere in the corpus scores clearly higher (by more than 0.25), it takes that one instead.

**3. Extracting facts.** Each sentence of up to 40 words becomes a fact, linked to the chunk found in step 2.

**4. Detecting errors.** For sentences of up to 60 words, three checks run in order and the first that fires is used:
- **Scene number:** a mention like "Scene V" is compared with the scene range in the chunk's metadata.
- **Setting:** a phrase like "set in X" is compared with the place named in the scene heading (`SCENE I. Place.`).
- **Word substitution:** a number, a name or a role word (such as *father*, *king*, *servant*) in the sentence that does not appear in the best-matching chunk is treated as a suspect. The pipeline looks for the replacement in the chunk using neighbouring words as anchors. Two anchors give higher confidence than one, and numbers get a small bonus. Names that differ only by spelling are ignored.

**5. Output.** Errors are ranked by confidence and only the top 8 are kept, because the scoring penalizes false alarms. The source quote is a window of about 26 words around the correct value.

## Design notes

- **No external dependencies.** Standard library only (`re`, `difflib`, `json`, `math`, `collections`).
- **Offline and fast.** No network calls and no language models at runtime, as the task runs without internet and with a time limit.
- **Precision over recall.** Reporting few, well-supported errors was a deliberate choice to avoid false-alarm penalties.

## Usage

```
python -X utf8 solution.py --input <input_dir> --output <output_dir>
```

Expected input:

```
<input_dir>/
  corpus.jsonl            # one JSON object per line: id, text (and optional scene metadata)
  articles/
    article_1.json        # fields: article, title, text
    ...
```

The output directory gets one `article_<n>.json` per article with the fields `article`, `facts` and `errors`.

## Limitations

- English-only and tuned to a few error types: numbers, names, roles, scene numbers and places. It will miss other kinds of errors, such as altered events or motives.
- It relies on word overlap and heuristics, so paraphrased claims can be matched to the wrong chunk.
- Thresholds (0.25, 0.5, 0.85 and the confidence values) were chosen by hand on the public example articles, not tuned systematically.

## Author

Nazarii Nahirnyi, first-year Computer Science (AI Systems) student at Lviv Polytechnic.
