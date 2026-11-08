---
name: read-pdf
description: Use whenever a PDF in a flow-life folder is about to be read or asked about (a certificate, a letter, a decision, a statement). Reads its Markdown summary when one exists and is current; otherwise reads the PDF once and writes the summary beside it, so the PDF is not read again.
---

# read-pdf: read a PDF once

Read `${CLAUDE_PLUGIN_ROOT}/references/rules.md` (Documents, Sensitive data) first.

1. **Ask the script, before opening the PDF:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_summary.py" status <pdf>
   ```
   - Exit 0 and a path: read that summary only, answer from it, and say the answer came
     from the summary. Open the PDF only when the question needs something the summary
     lacks, and then add what was missing to the summary.
   - Exit 1 (`none`) or 3 (`stale`): go on. `stale` means the PDF changed since it was
     summarised, so the old summary is not to be trusted.
2. **Read the PDF.** If it cannot be read (a scan with no text), say so and write no summary.
3. **Write the summary beside it**, same folder and name with `.md`
   (`documents/tax/return-2026.pdf` gets `documents/tax/return-2026.md`; an existing stale
   one is rewritten). Its first line is exactly the output of
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_summary.py" stamp <pdf>`. Then, in plain
   Markdown: what the document is, who issued it and when, the facts a later question is
   likely to need (amounts, dates, deadlines, what it asks of the owner), and anything
   odd. Never from memory.
4. **Identifiers.** Under the documents folder or a process folder the summary may carry
   identifiers, as the evidence it sits beside does. Anywhere else, leave them out and
   write "the number is in the PDF".
5. **Register it** when it sits under the documents folder: a row for the summary
   (`/flow-life:register-document`), or the check reports it as not listed.
6. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_repo.py"` → `0 problem(s)`.

Never send the PDF or its summary anywhere. The script reads and prints; the agent writes.
