"""Deterministic transcript filtering for the coordinator memory sidecar.

The filter decides, without a model, which transcript records carry
conversational text and what that text is. It is driven by a declarative
*profile*: a description of one harness's transcript shape. Hand-written
profiles ship for Claude Code and Term2; a profile for an unseen harness is
produced by schema induction (a separate LLM onboarding step) and then frozen,
reviewed, and interpreted here deterministically.

A profile names the path to the record's type token and maps each conversational
record type to a *channel*: the path, relative to the record, that reaches the
text container, plus the block specs that identify human text inside that
container. The container is either a bare string or a list of typed blocks, so
one profile shape covers both harnesses.

Profiles are data, never code.
"""
from __future__ import annotations

# Claude Code transcript profile. Records are JSONL objects with a top-level
# ``type``; conversational text lives in ``message.content``, either a bare
# string or a list of typed blocks.
CLAUDE_CODE = {
    'name': 'claude-code',
    'type_path': ('type',),
    'records': {
        'user': {'text_path': ('message', 'content'),
                 'text_blocks': ({'type': 'text', 'field': 'text'},)},
        'assistant': {'text_path': ('message', 'content'),
                      'text_blocks': ({'type': 'text', 'field': 'text'},)},
    },
}

# Term2 conversation-log profile. Records are ``{v, seq, ts, event}`` envelopes
# whose ``event.type`` is the record type; the user text is a bare string on
# ``event.message.text``, assistant text is ``assistant_text`` items inside
# ``event.turn.items``.
TERM2 = {
    'name': 'term2',
    'type_path': ('event', 'type'),
    'records': {
        'user_message': {'text_path': ('event', 'message', 'text'), 'text_blocks': ()},
        'assistant_turn': {'text_path': ('event', 'turn', 'items'),
                           'text_blocks': ({'type': 'assistant_text', 'field': 'text'},)},
    },
}

# Harness handle (as recorded in a session binding) -> profile.
PROFILES = {'claude': CLAUDE_CODE, 'term2': TERM2}


def profile_for(harness, default=CLAUDE_CODE):
    """Return the profile for a harness handle, or ``default`` when unknown."""
    return PROFILES.get(harness, default)


def _walk(node, path):
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _channel_text(record, spec):
    node = _walk(record, spec['text_path'])
    dropped_blocks = []
    if isinstance(node, str):
        text = node
    elif isinstance(node, list):
        parts = []
        for block in node:
            matched = None
            if isinstance(block, dict):
                for block_spec in spec.get('text_blocks', ()):
                    if block.get('type') == block_spec['type'] and block_spec['field'] in block:
                        matched = block[block_spec['field']]
                        break
                if matched is None:
                    dropped_blocks.append(block.get('type') or 'unknown')
            else:
                dropped_blocks.append('scalar')
            if matched is not None:
                parts.append(str(matched))
        text = ' '.join(parts)
    else:
        return None, []
    return text, dropped_blocks


def filter_record(record, profile=CLAUDE_CODE):
    """Return ``(text, info)`` for one transcript record.

    ``text`` is the record's conversational text, or ``None`` when the record
    carries none and must be dropped. ``info`` records what happened so callers
    can surface schema drift:

    - ``{'kept': True, ...}`` - text extracted; ``dropped_blocks`` lists the
      block types seen but not kept (for example ``tool_result``).
    - ``{'dropped': 'record-type', 'record_type': <type>}`` - the record type is
      not in the profile, i.e. not conversational for this harness.
    - ``{'dropped': 'no-text'}`` - a conversational record type with no text.
    """
    if not isinstance(record, dict):
        return None, {'dropped': 'record-type', 'record_type': None}
    record_type = _walk(record, profile['type_path'])
    spec = profile['records'].get(record_type) if isinstance(record_type, str) else None
    if spec is None:
        return None, {'dropped': 'record-type', 'record_type': record_type}
    text, dropped_blocks = _channel_text(record, spec)
    if text is not None:
        text = text.strip()
    if not text:
        return None, {'dropped': 'no-text'}
    info = {'kept': True}
    if dropped_blocks:
        info['dropped_blocks'] = dropped_blocks
    return text, info


def filter_records(records, profile=CLAUDE_CODE):
    """Split ``records`` into kept ``(record, text)`` pairs and drop counts.

    ``dropped`` maps a dropped record type (or ``'no-text'``) to its count, so a
    caller can log the types it did not recognize. An unrecognized type appears
    under its own name; this is the schema-drift signal.
    """
    kept = []
    dropped = {}
    for record in records:
        text, info = filter_record(record, profile)
        if text is None:
            key = info.get('record_type') if info.get('dropped') == 'record-type' else 'no-text'
            dropped[key] = dropped.get(key, 0) + 1
            continue
        kept.append((record, text))
    return kept, dropped
