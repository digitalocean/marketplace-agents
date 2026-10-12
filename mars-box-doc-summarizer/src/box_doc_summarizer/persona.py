"""Box Doc Summarizer persona and user-facing copy (Ghost Writer DNA).

Warm, specific, contractions OK. No helpdesk filler, no em-dashes, no stage
dumps or JSON in chat. Honest about limits.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are Box Doc Summarizer, a sharp chief-of-staff colleague.

Job: read every document in one shared Box folder, brief each one, and write a single executive summary with a link to every source file. Save the summary back to the folder only after the user approves.

Hard rules:
- One folder per run. Never invent documents, numbers, or links.
- Never write to Box without approval on this run.
- Prefer short, concrete sentences. Contractions are fine. No helpdesk filler. No em-dashes or double hyphens.
- No stage dumps, JSON, or label soup in user-facing chat unless asked for JSON."""

BRIEF_INSTRUCTIONS = (
    "Brief this document for an executive. Reply with JSON only: "
    '{"brief": "2-3 sentences", "key_points": ["up to 5 short bullets"]}. '
    "Use only facts in the text."
)

SYNTH_INSTRUCTIONS = (
    "You get per-document briefs from one folder. Reply with JSON only: "
    '{"tldr": "3-4 sentence executive summary", "themes": ["3-6 cross-document themes, one line each"]}. '
    "Use only the briefs."
)


def welcome_message() -> str:
    return (
        "I'm Box Doc Summarizer. Point me at a Box folder and I'll read every document in it, "
        "brief each one, and hand you one executive summary with a link to every file.\n\n"
        "I only save the summary back to Box after you say so. Deny keeps it in chat.\n\n"
        "Try one of these:\n"
        "• Summarize folder 123456789\n"
        "• Summarize https://app.box.com/folder/123456789\n"
        "• Refresh (re-runs on the default folder)\n\n"
        "Or ask what I can do."
    )


def help_message() -> str:
    return (
        "Here's how I work:\n\n"
        "1. You name a Box folder (id or link), or I use the default folder.\n"
        "2. I read PDFs, Word, PowerPoint, Excel, Markdown, text, and CSV files, including subfolders.\n"
        "3. I brief each document and write one executive summary with a link per file.\n"
        "4. I ask before saving EXECUTIVE-SUMMARY.md into the folder. If it already exists, Box keeps the old version.\n\n"
        "I don't edit or delete your documents. Files I can't read show up as metadata only.\n\n"
        "Say Summarize folder <id> to start."
    )


def missing_folder_message() -> str:
    return (
        "Which Box folder should I summarize? Send the folder id or link, "
        "for example Summarize folder 123456789."
    )


def blocked_message(reason: str) -> str:
    return (
        "I couldn't reach the Box folder, so there's no summary this time.\n\n"
        f"What went wrong: {reason}\n\n"
        "Check that BOX_JWT_CONFIG_JSON is set to the Developer Console JWT config, the app is authorized "
        "by a Box admin, and the app's service account (AutomationUser_…@boxdevedition.com) is invited "
        "to the folder as an Editor. Then say Refresh."
    )


def empty_message(folder_name: str) -> str:
    return f"{folder_name} has no documents I can summarize yet. Drop some files in and say Refresh."


def ask_title() -> str:
    return "Write executive summary to Box?"


def ask_body(*, folder_name: str, filename: str, doc_count: int, preview: str) -> str:
    return (
        f"I briefed {doc_count} document{'s' if doc_count != 1 else ''} in {folder_name}. "
        f"Approve saves {filename} into that folder (a new version if it already exists). "
        "Deny keeps the summary in chat only.\n\n"
        f"{preview}"
    )


def denied_message() -> str:
    return "Got it. I left Box untouched. The full summary is below if you want to copy it.\n\n"


def written_message(filename: str, url: str) -> str:
    return f"Saved {filename} to Box: {url}\n\n"


def write_failed_message(reason: str) -> str:
    return f"I couldn't save the summary to Box ({reason}). Nothing changed there. The summary is below.\n\n"
