# Python Code Snippet Detection

## 1. Constants and Definitions

### CONSTANTS:

```python
STRONG_PY_KEYWORDS = {
    "def", "class", "import", "from", "if", "elif", "else", "try", "except",
    "with", "for", "while", "return", "print", "lambda", "yield", "assert",
    "nonlocal", "global", "raise", "async", "await", "pass", "continue", "break"
}

WEAK_PY_KEYWORDS = { "in", "is", "and", "or", "not" }

DANGEROUS_REGEX = regular expression detecting:
    - os.system(...)
    - subprocess.run / call / Popen
    - eval(...)
    - exec(...)
    - shutil.rmtree(...)
    - 'rm -rf'
    - urllib.request / urlopen
    - requests?
    - socket.
    - pickle.load(s)
    - marshal.load(s)

MAX_INPUT_SIZE = 5 MB  # Maximum input size limit

STAT_THRESHOLD = 70.0  # Default confidence score threshold below which we do not wrap
```

## 2. Utility Functions

### 2.1 Determine if a line looks like Python code

```python
FUNCTION is_line_code_like(line_text):
    1. Strip spaces -> stripped_line
    2. If len(stripped_line) < 3 THEN
         RETURN FALSE
    3. If line contains '#', cut before '#' to ignore comment
       - If remaining part < 3 characters, RETURN FALSE
    4. Convert to lowercase -> lower_line
    5. Check if line contains foreign language words (e.g., "function ", "console.")
       OR symbols like {, }, ; (not typical of Python)
       -> If YES, RETURN FALSE
    6. Match against typical Python block pattern
       (e.g., `^\s*(def|class|if|elif|else|try|except|with|for|while)\b.*:\s*$`)
       -> If YES, RETURN TRUE
    7. Extract tokens `[A-Za-z_]+` -> token_list
    8. For each token in token_list:
         IF token in STRONG_PY_KEYWORDS THEN
             RETURN TRUE
    9. Otherwise, RETURN FALSE
```

### 2.2 Check for dangerous patterns

```python
FUNCTION _contains_dangerous_pattern(text):
    1. Apply DANGEROUS_REGEX to text
    2. If match found, RETURN TRUE
    3. Else, RETURN FALSE
```

### 2.3 Strip comments from a block

```python
FUNCTION strip_comments_from_block(multiline_block):
    1. Split block into lines
    2. For each line:
       - Remove everything after first '#' (comment)
       - Add cleaned line to a new list
    3. Join the cleaned list with line breaks
    4. RETURN final string
```

### 2.4 Quickly check if text might contain Python code

```python
FUNCTION might_contain_python_code(text):
    1. Lowercase text -> text_min
    2. Search for explicit JavaScript forms (e.g., "function ", "console.")
       - If found, check if at least one token in STRONG_PY_KEYWORDS
         Otherwise, RETURN FALSE
    3. Extract tokens `[A-Za-z_]+` -> token_list
    4. If any token in STRONG_PY_KEYWORDS, RETURN TRUE
    5. Else, RETURN FALSE
```

## 3. Confidence Calculation via AST

```python
FUNCTION _calculate_confidence_for_block(multiline_block):
    1. block_no_comment = strip_comments_from_block(multiline_block)
    2. code_lines = non-empty lines from block_no_comment
    3. IF code_lines is empty:
         RETURN 0.0
    4. Dedent block (via textwrap.dedent or equivalent) -> dedented_code
    5. TRY:
         - Parse dedented_code with ast.parse
         - If parse successful:
             IF block has >1 line THEN RETURN 100.0
             ELSE RETURN 80.0
      EXCEPT (SyntaxError, IndentationError):
         - Extract tokens from block_no_comment
         - If any token in STRONG_PY_KEYWORDS:
             IF >1 line THEN RETURN 100.0
             ELSE RETURN 80.0
         - Else RETURN 0.0
```

## 4. Extraction and Grouping of Code Blocks

```python
FUNCTION _form_code_blocks(text):
    1. Split text into lines (keeping end separators) -> line_list
    2. Initialize in_code_block = FALSE
    3. Initialize empty list blocks
    4. For i from 0 to nb_lines - 1:
         - current_line = line_list[i]
         - IF in_code_block == TRUE:
             * Stay in block if:
               (is_line_code_like(current_line) OR
                empty line OR
                line starts with space/tab)
             * ELSE close block: blocks.add((block_start, i - 1))
               and in_code_block = FALSE
           ELSE:
             * If current_line looks like code:
               THEN in_code_block = TRUE
                     block_start = i
               ELSE do nothing
    5. If in_code_block at EOF, close block (block_start, last_line)
    6. RETURN blocks (list of (start, end) pairs)
```

## 5. Wrapping Logic (<PythonCode>…</PythonCode>)

```python
FUNCTION _wrap_code_blocks_in_text(text, start_tag, end_tag):
    1. blocks = _form_code_blocks(text)
    2. IF blocks is empty:
         - Check if text contains dangerous pattern via _contains_dangerous_pattern
           - If yes, mark dangerous_code_detected = TRUE
         - RETURN (text, 0.0, FALSE)
    3. Split text into lines
    4. Initialize out = [] (result)
    5. Initialize confs = [] (confidence scores)
    6. Initialize did_wrap = FALSE
    7. last = 0  # current line index
    8. For each (start_i, end_i) in blocks:
         - Add lines [last … start_i-1] unchanged to out
           * Check dangerous pattern in prefix
         - block_str = concat lines [start_i … end_i]
         - conf = _calculate_confidence_for_block(block_str)
         - Add conf to confs
         - Check dangerous pattern in block_str
         - IF conf >= STAT_THRESHOLD:
             out.add(start_tag + block_str + end_tag)
             did_wrap = TRUE
           ELSE:
             out.add(block_str)
         - last = end_i + 1
    9. Add trailing lines [last … end] to out
       - Check dangerous pattern in tail
    10. avg_conf = average(confs) (or 0 if confs empty)
    11. IF did_wrap == TRUE AND avg_conf < STAT_THRESHOLD:
         - RETURN (text, avg_conf, FALSE)
       ELSE:
         - RETURN (concatenation of out, avg_conf, did_wrap)
```

## 6. Processing String Fields in JSON

```python
FUNCTION _process_string_field(original_string, start_tag, end_tag):
    1. Strip spaces -> s = original_string.strip()
    2. IF len(s) < 5:
         RETURN (original_string, [], FALSE, FALSE)
    3. unescaped = replace "\\n" by \n and "\\r" by \r in original_string
    4. IF NOT might_contain_python_code(unescaped) AND NOT _contains_dangerous_pattern(unescaped):
         RETURN (original_string, [], FALSE, FALSE)
    5. (wrapped, confidence, did_wrap) = _wrap_code_blocks_in_text(unescaped, start_tag, end_tag)
    6. IF did_wrap == TRUE:
         reescaped = retransform \n and \r to "\\n" and "\\r"
         changed = (reescaped != original_string)
         RETURN (reescaped, [confidence], did_wrap, changed)
       ELSE:
         RETURN (original_string, [confidence], FALSE, FALSE)
```

## 7. Recursive Processing of JSON Objects

```python
FUNCTION _wrap_code_in_json(obj, start_tag, end_tag, parallel):
    1. IF obj is a dict:
         new_dict = {}
         FOR each (key, value) in obj:
             (nv, c, dw, ch) = _wrap_code_in_json(value, start_tag, end_tag, parallel)
             new_dict[key] = nv
         RETURN (new_dict, confs, did_wrap_any, changed_any)

    2. ELSE IF obj is a list:
         IF parallel == TRUE AND len(list) > 1:
             # process items in threads
             FOR each item in parallel:
                _wrap_code_in_json(item, start_tag, end_tag, parallel)
         ELSE:
             FOR each it in obj:
                _wrap_code_in_json(it, start_tag, end_tag, parallel)
         RETURN (new_list, confs, did_wrap_any, changed_any)

    3. ELSE IF obj is a string:
         (new_str, conf_list, did_wrap, changed) = _process_string_field(obj, start_tag, end_tag)
         RETURN (new_str, conf_list, did_wrap, changed)

    4. ELSE:
         RETURN (obj, [], FALSE, FALSE)
```

## 8. Final Key Points

- **Size limit (5MB):** check input size before any processing.
- **Confidence analysis (avg_conf):** if wrapping confidence is below threshold, revert to original text or JSON.
- **Dangerous code detection:** any detected dangerous pattern is flagged immediately.
- **Final output:**
  - In plain text, result is concatenation of lines, potentially wrapped.
  - In JSON, re-serialize the modified structure (with `json.dumps`).
