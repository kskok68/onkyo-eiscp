#!/usr/bin/env python3
# coding: utf8
"""Script to extract the list of commands from the Onkyo protocol
documentation, which is an Excel file.

Since this Excel file is not designed to be read by machines, I don't
expect this to work for new versions of the file without adjustments.

Here's how the process is supposed to work:

    - This script takes the Excel document as a an input file, and
      converts it into a YAML.
    - This is checked into version control.
    - Adjustments to this file are required and made, via version control.
    - Subsequently, a new version of the Excel file can be parsed into YAML
      and merged with the manual changes.
    - The YAML file is used by the Python library for the final command list;
      potentially be further generating a Python file from it for speed.
"""
import copy
import sys
import re
import os
from datetime import datetime
import yaml
from collections import OrderedDict
import tablib

EXTRA_TRACE = False

# sys.stdout = open('output.yaml', 'w')

# Common patterns and constants
HEX_CHARS = '0123456789ABCDEF'
COMMON_WORDS_TO_REMOVE = ['level', 'setting', 'state', 'control']
STATE_WORDS = ['enabled', 'disabled', 'active', 'inactive', 'toggle', 'standby', 'auto', 'manual']
NEGATION_WORDS = ['not', 'no', 'non']

# Helper functions for string processing
def make_command(name):
    """Convert a string into a space-less command."""
    if not name:
        return ""
    name = re.sub(r'[^\w]', ' ', name)   # Replace special characters with spaces
    name = name.strip().lower()
    name = re.sub(r'\s+', ' ', name)     # Replace duplicate spaces
    return name.replace(' ', '-')         # In the end, we want no whitespace

def is_hex_value(val):
    """Check if a string contains only hexadecimal characters."""
    return all(c in HEX_CHARS for c in val)

def normalize_whitespace(text):
    """Normalize whitespace in a string."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def clean_description_text(text):
    """Clean up description text by removing parentheses content and normalizing whitespace."""
    if not text:
        return ""
    text = re.sub(r'\([^)]*\)', ' ', text)  # Remove text in parentheses
    return normalize_whitespace(text)

def extract_words(text):
    """Extract meaningful words from a text string."""
    words = []
    if text:
        for word in re.split(r'[ :,\n]+', text):
            if word and len(word) > 1:
                # Clean up the word
                word = re.sub(r'[^\w-]', '', word).lower()
                if word:
                    words.append(word)
    return words

# Tained tuple that can have a non-standard YAML representation
class FlowStyleTuple(tuple):
    pass

def is_known_footer(string):
    """Sometimes the excel has a footer for a command section and
    we cannot very reliably differentiate it from a command value
    (actually, it might be possible, but this approach is easier).
    """
    if not string:
        return False
    string = string.strip()

    known_prefixes = [ "*", "Ex:" ]
    if string.startswith(tuple(known_prefixes)):
        return True

    known_footers = [
        'If Jacket Art is disable from one',
        'Please refer to sheets of popup xml,',
        'receiver will return',
        '://',
        'Line Separator : " ・ "（0x20, 0xC2, 0xB7, 0x20'
    ]

    return any(footer in string for footer in known_footers)

def process_unicode_text(text):
    """Process values to handle Unicode characters consistently."""
    if not text:
        return ""

    # Replace Unicode special characters with ASCII equivalents
    replacements = {
        '\u2026': '...',  # ellipsis
        '\u2013': '-',    # en dash
        '\u2014': '-',    # em dash
        '\uff54': 't',    # random odd T
        '\u3000': ' '     # full-width space
    }

    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)

    return text

def safe_extract_quoted_content(text):
    """Extract content between quotes, handling various quote types."""
    # Strip whitespace first
    text = text.strip()

    # Process Unicode characters first
    text = process_unicode_text(text)

    # Define all possible quote characters
    quotes = {'"': '"', "'": "'", "\u201c": "\u201d", "\u201d": "\u201c"}

    # First check for exact pairs
    for open_q, close_q in quotes.items():
        if text.startswith(open_q) and text.endswith(close_q):
            return text[len(open_q):-len(close_q)]

    # Then check more liberally for any quote combination
    for open_q in quotes.keys():
        if text.startswith(open_q):
            for close_q in quotes.values():
                if text.endswith(close_q):
                    return text[len(open_q):-len(close_q)]

    # If no quotes found, return stripped version
    stripped = text.strip('"\'"\u201c\u201d')
    if text != stripped:
        print(f"Warning: Failed to match quotes in value: '{text}', using stripped: '{stripped}'", file=sys.stderr)
    return stripped

def is_command_header(row):
    """Determine if a row represents a command header."""
    if not row[0] or ' -' not in row[0]:
        return False

    rowStr = row[0].strip()
    # Check for specific patterns that indicate headers
    if ( rowStr[0] == "'" or rowStr[0] == '"'):
        return True

    # Check if subsequent columns are empty (another header indicator)
    if not any(row[1:]):
        return True

    return False

def parse_command_header(header_text):
    """Parse a command header to extract the prefix and description."""
    if not header_text:
        return None, None

    # Fix where it is a dual header like "ZPA"/"ZPB - Zone 2"
    header_text = header_text.replace('"/"', '').strip()
    header_text = header_text.replace("When Jacket Art","") #net usb
    # Skip known non-header patterns
    if header_text.startswith('*'):
        return None, None
    if 'when' in header_text.lower() or 'ex:' in header_text.lower() or 'is shared' in header_text.lower():
        return None, None
    # Try matching with quotes
    cmd_pattern = r'["\'"\u201c\u201d]([A-Z0-9]{2,})["\'"\u201c\u201d]\s*-\s*(.*)'
    match = re.match(cmd_pattern, header_text)

    if match is None:
        # Try alternative without quotes
        alt_pattern = r'([A-Z0-9]{2,})\s*-\s*(.*)'
        match = re.match(alt_pattern, header_text)

    if match is None:
        return None, None

    return match.groups()

def process_range_value(value):
    """Process a command value that might be a range."""
    if not re.search(r'["""]', value):
        return value

    # Parse the value - sometimes ranges are given, split those first
    range_value = re.split(r'(?<=[\u201c\u201d"""])-(?=[\u201c\u201d"""])', value)
    range_value = [safe_extract_quoted_content(r) for r in range_value]

    # If it's actually a single value, store as such
    # e.g. "UP" as opposed to "0 - 28".
    if len(range_value) == 1:
        range_value = range_value[0]
        # Replace `xx` to make it clearer it's a placeholder
        return range_value.replace('xx', '{xx}')

    # For any multi-value range, try to convert to integers first
    try:
        # Handle special cases for subwoofer levels with plus/minus prefix
        processed_range = []
        for item in range_value:
            if item.startswith('+'):
                # For +18, convert to integer directly
                processed_range.append(int(item[1:], 16))
            elif item.startswith('-'):
                # For -1E, convert to negative integer
                processed_range.append(-int(item[1:], 16))
            else:
                # Try to convert normal values (like "000") to integer
                processed_range.append(int(item, 16))

        # Convert to tuple for hashability
        range_value = tuple(processed_range)

        # Handle cases where range_value is given as -10...0...+10 format
        # Convert to a simple pair by removing the middle 0
        if len(range_value) == 3 and range_value[1] == 0:
            range_value = (range_value[0], range_value[2])

    except ValueError:
        # If conversion fails, handle special cases for track numbers
        if len(range_value) == 2 and all(r.isdigit() for r in range_value) and (
            range_value[0].startswith('0') or range_value[1].startswith('0') or
            len(range_value[0]) >= 3 or len(range_value[1]) >= 3
        ):
            # Keep as string tuple to preserve leading zeros for track numbers
            range_value = tuple(range_value)
        else:
            # For any other multi-value range_value that failed integer conversion,
            # just keep as string tuple
            range_value = tuple(range_value)
            print(f"Warning: Could not convert range_value to integers: {range_value}", file=sys.stderr)

    # Warn about ranges that have more than 2 items
    if len(range_value) > 2:
        print(f'Warning: Range {range_value} is not as expected at 2 items.', file=sys.stderr)

    return range_value

def parse_support(s,debug=False):
    """Parse a cell to determine model support (Yes/No)."""
    if not s:
        return False

    if s.startswith('Yes'):
        return True
    elif s.startswith('No'):
        return False
    # String values like RS232C imply YES
    return True

def determine_name_from_description(desc, command_parts=None, groupname=None):
    """Extract a command name from the description."""
    if not desc:
        return None

    name = desc.replace('sets', '')
    name = re.sub(r'\(.*\)$', '', name)  # Remove trailing brackets

    if ',' in name or '/' in name:
        # Commas here (inserted above) indicate multiple values, so does /
        names = re.split(r'[,/]', name)
        processed_names = [remove_dups(make_command(n), command_parts, groupname) for n in names]
        # Filter out empty strings
        processed_names = [s for s in processed_names if bool(s)]

        # If we have only one name after processing, don't wrap it in FlowStyleTuple
        if len(processed_names) == 1:
            return processed_names[0]
        elif processed_names:
            return FlowStyleTuple(processed_names)
        else:
            return None
    else:
        name = make_command(name)
        return remove_dups(name, command_parts, groupname)

def remove_dups(name, command_parts=None, groupname=None):
    """Remove duplicate parts from command names."""
    if not name:
        return name

    if command_parts is None:
        command_parts = []

    # Convert name to list of parts
    name_parts = name.split('-')

    # Filter parts
    filtered_parts = []
    for part in name_parts:
        if (part not in command_parts and
            part not in COMMON_WORDS_TO_REMOVE and
            (not groupname or part != groupname.lower())):
            filtered_parts.append(part)

    return '-'.join(filtered_parts)

def determine_value_name(range_value, desc, command_parts=None, groupname=None):
    """Determine a readable name for a command value."""
    if range_value == 'QSTN':
        return 'query'

    if isinstance(range_value, str) and ('nnn' in range_value or 'bbb' in range_value):
        # With these sorts of values, we already know we can't get anything useful
        return None

    # When description tells us it sets something, use that as the value name
    if desc and desc.startswith('sets') and 'Wrap-Around' not in desc:
        return determine_name_from_description(desc, command_parts, groupname)

    if isinstance(range_value, str):
        if range_value == 'TG':
            return 'toggle'
        else:
            # Use the internal command itself, if it's not a range
            name = re.sub(r'\s*Key$', '', range_value)  # sometimes ends in key, remove
            return make_command(name)

    return None

def import_sheet(groupname, sheet, model_sets):
    """Import a sheet from the Excel file and convert to YAML structure."""
    if EXTRA_TRACE:
        print(f"Importing {groupname} sheet", file=sys.stderr)
    data = OrderedDict()

    # First line has a list of models, ignore empty cols, and first two.
    modelcols = list(filter(lambda s: bool(s), sheet[0]))[2:]
    # One model headers can continue multiple models. Split.
    modelcols = [m
                .replace('\n(Ether)', '(Ether)')
                .replace('\n(Ver2.0)', '(Ver2.0)')
                .replace('TX-NR5000ETX-NA1000', 'TX-NR5000\nETX-NA1000')
                .split('\n')
              for m in modelcols]

    # Max column to consider (to avoid floating tables)
    max_model_column = len([s for s in modelcols if bool(s)]) + 2

    def loop_rows(data):
        it = iter(data)

        while True:
            try:
                row = next(it)

                # Special case with many many rows we have to skip (the NRI query command)
                if row[0] and ('ex.)XML data' in row[0] or 'ex.) XML data' in row[0]):
                    while True:
                        try:
                            row = next(it)
                            if row[0] and isinstance(row[0], str) and row[0].startswith('"'):
                                break
                        except StopIteration:
                            return  # End of data during special case
                yield row
            except StopIteration:
                return  # End of data

    prefix = prefix_desc = None
    for row in loop_rows(sheet[1:]):
        # Remove right-most columns that no longer belong to the main table
        row = row[:max_model_column]

        # Remove whitespace from all fields
        row = [str(s).strip().replace("NET/USB Device Name"," - NET/USB Device Name") if s else s for s in row]

        # Debug: Print the first field and check if subsequent columns are empty
        if EXTRA_TRACE:
            print(f"ROW START: '{row[0]}', empty cols: {not any(row[1:])}", file=sys.stderr)

        # Ignore empty lines
        if not any(row):
            continue

        # Try to recognize command footers. Footnotes often start with *.
        if row[0] is None:
            continue
        if is_known_footer(row[0]):
            continue

        # Detect if this is a command header
        if is_command_header(row):
            # Parse the command header
            prefix_match = parse_command_header(row[0])
            if not prefix_match:
                print(f"Warning: Failed to parse command header row: '{row[0]}'", file=sys.stderr)
                continue

            prefix, prefix_desc = prefix_match

            if not prefix or not prefix_desc:
                print(f"Warning: Incomplete command header: prefix={prefix}, desc={prefix_desc} header={row[0]}", file=sys.stderr)
                continue

            if EXTRA_TRACE:
                print(f"Matched prefix: '{prefix}', description: '{prefix_desc}'", file=sys.stderr)

            # Auto-determine a possible command name
            name = re.sub(r'\(.*\)$', '', prefix_desc)  # Remove trailing brackets
            name = re.sub(r'(Operation\s*)?Command\s*$', '', name)  # Remove "Operation Command"
            name = re.sub(r'(?i)^%s' % re.escape(groupname), '', name)  # e.g. for zone2, remove any zone2 prefix.
            name = make_command(name)

            data.setdefault(prefix, OrderedDict())
            data[prefix]['name'] = name
            data[prefix]['description'] = prefix_desc
            data[prefix]['values'] = OrderedDict()

        # Process command value rows
        else:
            if not prefix:
                # Skip rows that don't have a valid prefix set
                continue

            value, desc = row[0], row[1]

            # Process the value
            range_value = process_range_value(value)

            # Process model support
            support = [ parse_support(c) for c in row[2:]]
            # Validate we don't miss anything
            assert len(support) == len(modelcols) == len(row[2:])


            # Get a final list of model names
            supported_modelcols = [
                model for model, yesno in zip(modelcols, support)
                if yesno]
            supported_models = sum(supported_modelcols, [])  # flatten
            # Remove duplicates and sort
            supported_models = sorted(set(supported_models))
            supported_models = tuple(supported_models)  # make hashable

            # Add to model sets
            if supported_models not in model_sets:
                setname = f'set{len(model_sets)+1}'
                model_sets[supported_models] = setname
            else:
                setname = model_sets[supported_models]

            # Process description
            if not desc:
                continue
            else:
                desc = process_unicode_text(desc)

            # Fix up the description
            desc = re.sub(r'\*\d*$', '', desc)   # remove footnote refs
            if desc.startswith('sets'):
                # Multiple whitespace here is often used to indicate multiple possible values
                desc = re.sub(r'\s\s\s+', ', ', desc)

            # Determine a readable name
            name = None
            if isinstance(range_value, tuple):
                # For track numbers
                if len(range_value) == 2 and all(isinstance(r, str) and r.isdigit() for r in range_value):
                    name = 'track-number'
            else:
                # Determine name based on the value and description
                command_parts = data[prefix]['name'].split('-') if prefix in data else []
                name = determine_value_name(range_value, desc, command_parts, groupname)

            # Create the value entry
            this = data[prefix]['values'][range_value] = OrderedDict()
            if name:
                this['name'] = name
            this['description'] = desc
            this['models'] = setname

    improve_names_for_values(data)

    # Handle zone a/b items
    for combined_prefix, split_prefixes in [("ZPAZPB", ("ZPA", "ZPB")), ("SPASPB", ("SPA", "SPB"))]:
        if combined_prefix in data:
            prefix_a, prefix_b = split_prefixes
            data[prefix_a] = copy.deepcopy(data[combined_prefix])
            data[prefix_b] = copy.deepcopy(data[prefix_a])

            # Set appropriate names
            if combined_prefix == "ZPAZPB":
                data[prefix_a]["name"] = "zone-2-a"
                data[prefix_b]["name"] = "zone-2-b"
            else:  # SPASPB
                data[prefix_a]["name"] = "speaker-a"
                data[prefix_b]["name"] = "speaker-b"

            del data[combined_prefix]

    # old manual established aliases we maintain for back compat
    if groupname == "main":
        data["PWR"]["aliases"] = ["power"]
        data["PWR"]["values"]["00"]["name"] = ["standby", "off"]
        data["MVL"]["aliases"] = ["volume"]
        data["SLI"]["aliases"] = ["source"]

    return data

def improve_names_for_values(data):
    """Improve names for hex values by analyzing descriptions."""
    for prefix in data:
        if 'values' not in data[prefix]:
            continue

        # Collect existing names and values that need naming
        existing_names = set()
        all_values = []

        for val_key, val_details in data[prefix]['values'].items():
            if 'name' in val_details:
                existing_names.add(val_details['name'])

            # Collect two-digit hex values that need better names
            if (isinstance(val_key, str) and len(val_key) == 2 and is_hex_value(val_key) and
                ('name' not in val_details or val_details['name'] == val_key)):
                if 'description' in val_details and val_details['description']:
                    all_values.append((val_key, val_details['description']))

        # Analyze descriptions to find common patterns and potential collisions
        potential_collisions = []
        processed_descriptions = []

        # Process and normalize descriptions
        for val_key, desc in all_values:
            clean_desc = clean_description_text(desc).lower()
            processed_descriptions.append((val_key, clean_desc))

        # Look for descriptions that would result in the same name (collision detection)
        for i in range(len(processed_descriptions)):
            val_key1, desc1 = processed_descriptions[i]
            words1 = desc1.split()
            if not words1:
                continue

            last_word = words1[-1]
            for j in range(len(processed_descriptions)):
                if i == j:
                    continue

                val_key2, desc2 = processed_descriptions[j]
                words2 = desc2.split()
                if not words2:
                    continue

                # If they share the same last word, note the potential collision
                if words2[-1] == last_word:
                    potential_collisions.append((val_key1, val_key2, last_word))

        # Process each value that needs naming
        for val_key, val_details in list(data[prefix]['values'].items()):
            # Check if value is a 2-digit hex number and needs naming
            if (isinstance(val_key, str) and len(val_key) == 2 and is_hex_value(val_key) and
                ('name' not in val_details or val_details['name'] == val_key)):

                # Skip values without descriptions
                if not val_details.get('description'):
                    continue

                desc = val_details['description']
                clean_desc = clean_description_text(desc)
                words = extract_words(clean_desc)

                # Only proceed if we have words to work with
                if not words:
                    continue

                try:
                    # Check for negation words that must be preserved
                    has_negation = False
                    negation_word = None
                    for neg in NEGATION_WORDS:
                        if neg in words:
                            has_negation = True
                            negation_word = neg
                            break

                    # Generate candidate names in order of preference
                    candidate_names = []

                    # Check if this word is involved in collision
                    needs_more_context = False
                    if words:
                        for key1, key2, collision_word in potential_collisions:
                            if val_key == key1 or val_key == key2:
                                if collision_word == words[-1]:
                                    needs_more_context = True
                                    break

                    # 1. First priority: If no collision, use just the last meaningful word
                    if not needs_more_context and words:
                        last_word = words[-1]
                        if has_negation and negation_word != last_word:
                            candidate_names.append(f"{negation_word}-{last_word}")
                        else:
                            candidate_names.append(last_word)

                    # 2. Second priority: Common state words anywhere in description
                    for state in STATE_WORDS:
                        if state in words and state not in [n.split('-')[-1] for n in candidate_names]:
                            if has_negation and negation_word not in [state]:
                                candidate_names.append(f"{negation_word}-{state}")
                            else:
                                candidate_names.append(state)

                    # 3. If collision or need context, use two last words
                    if needs_more_context and len(words) >= 2:
                        context_name = '-'.join(words[-2:])
                        if context_name not in candidate_names:
                            candidate_names.append(context_name)

                    # 4. Add progressively longer combinations
                    for word_count in range(2, min(4, len(words) + 1)):
                        name_words = words[-word_count:]
                        if has_negation and negation_word not in name_words:
                            name_words = [negation_word] + name_words[-1:]
                        candidate_name = '-'.join(name_words)
                        if candidate_name not in candidate_names:
                            candidate_names.append(candidate_name)

                    # Try each candidate name, starting with shortest
                    for new_name in sorted(candidate_names, key=len):
                        if new_name and new_name not in existing_names:
                            val_details['name'] = new_name
                            existing_names.add(new_name)
                            if EXTRA_TRACE:
                                print(f"Renamed value from desc '{val_key}' to '{new_name}'", file=sys.stderr)
                            break

                except Exception as e:
                    print(f"Error processing value '{val_key}': {e}", file=sys.stderr)

    return data

def main():
    """Main entry point for the script."""
    # Verify arguments
    if len(sys.argv) < 2:
        print("Usage: %s <excel-file>" % os.path.basename(sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    # Load the Excel file
    with open(sys.argv[1], 'rb') as f:
        try:
            book = tablib.import_book(f)
        except Exception as e:
            print(f"Error loading Excel file: {e}", file=sys.stderr)
            sys.exit(1)

    # Model sets collect unique combinations of supported models
    model_sets = OrderedDict()

    # Print names and indices of all sheets in the workbook
    sheet_name_to_index = dict()
    if EXTRA_TRACE:
        print("Sheet names and indices:", file=sys.stderr)
    for i, sheet in enumerate(book.sheets()):
        sheet_name_to_index[sheet.title] = i
        if EXTRA_TRACE:
            print(f"  {i}: {sheet.title}", file=sys.stderr)

    # Process the sheets
    tabs_todo = OrderedDict([
        ("main", "MAIN"),
        ("zone2", "ZONE2"),
        ("zone3", "ZONE3"),
        ("zone4", "ZONE4"),
        ("net", "NET USB"),
        ("dock", "via RI"),
        ("port", "PORT"),
        ("blueray", "BD via RIHD"),
        ("tv", "TV via RIHD")
    ])
    data = OrderedDict()
    for key, value in tabs_todo.items():
        if EXTRA_TRACE:
            print(f"Processing {key} sheet", file=sys.stderr)

        data[key] = import_sheet(key, book.sheets()[sheet_name_to_index[f'CMND({value})']], model_sets)

    data['modelsets'] = OrderedDict(list(zip(list(model_sets.values()), list(model_sets.keys()))))

    # Configure YAML output
    # Configure yaml.SafeDumper for proper Unicode handling
    yaml.SafeDumper.add_representer(OrderedDict,
        lambda dumper, value: represent_odict(dumper, 'tag:yaml.org,2002:map', value))
    # Use flow style for FlowStyleTuple to make small multi-value sequences cleaner
    yaml.SafeDumper.add_representer(FlowStyleTuple,
        lambda dumper, value: yaml.SafeDumper.represent_sequence(dumper, 'tag:yaml.org,2002:seq', value, flow_style=True))
    # Configure for Unicode
    yaml.SafeDumper.unicode_supplementary = True
    yaml.SafeDumper.allow_unicode = True

    # Print header
    print("""# Last generated
#   by %s
#   from %s
#   at %s
#
# This file can and should be manually changed to fix things the
# automatic import didn't and often can't do right. These changes
# should be tracked in source control, so they can be merged with
# new generated versions of the file.
""" % (os.path.basename(sys.argv[0]), os.path.basename(sys.argv[1]), datetime.now()))

    # Output the data
    print(yaml.safe_dump(data, default_flow_style=False, allow_unicode=True))


def represent_odict(dump, tag, mapping, flow_style=None):
    """Like BaseRepresenter.represent_mapping, but does not issue the sort()."""
    value = []
    node = yaml.MappingNode(tag, value, flow_style=flow_style)
    if dump.alias_key is not None:
        dump.represented_objects[dump.alias_key] = node
    best_style = True
    if hasattr(mapping, 'items'):
        mapping = list(mapping.items())
    for item_key, item_value in mapping:
        node_key = dump.represent_data(item_key)
        node_value = dump.represent_data(item_value)
        if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
            best_style = False
        if not (isinstance(node_value, yaml.ScalarNode) and not node_value.style):
            best_style = False
        value.append((node_key, node_value))
    if flow_style is None:
        if dump.default_flow_style is not None:
            node.flow_style = dump.default_flow_style
        else:
            node.flow_style = best_style
    return node


if __name__ == "__main__":
    main()
